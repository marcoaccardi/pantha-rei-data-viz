"""
Data extraction engine for Ocean Data Management API.

Handles reading NetCDF files and extracting point data with high performance.
Supports all datasets: SST, currents, and acidity.
"""

import xarray as xr
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import time
import logging
from datetime import datetime, date
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict

from api.models.responses import (
    DatasetInfo, PointDataResponse, MultiDatasetResponse, 
    Coordinates, DataValue
)
from api.cache_manager import cache_manager, CachedPoint
from api.middleware.resilience import with_retry, managed_resource, default_retry_policy
from utils.parameter_interpreter import parameter_interpreter

logger = logging.getLogger(__name__)

class DataExtractor:
    """High-performance data extraction engine."""
    
    def __init__(self):
        """Initialize the data extractor."""
        self.data_path = Path(__file__).parent.parent.parent.parent / "ocean-data" / "processed" / "unified_coords"
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ocean_data")
        
        # Register cleanup for graceful shutdown
        import atexit
        atexit.register(self._cleanup)
        
        # Dataset configuration with ALL available variables
        self.dataset_config = {
            "sst": {
                "name": "Sea Surface Temperature",
                "description": "NOAA OISST v2.1 daily sea surface temperature",
                "variables": ["sst", "anom", "err", "ice"],
                "file_pattern": "sst_harmonized_*.nc",
                "spatial_resolution": "1.0° (downsampled from 0.25°)"
            },
            "currents": {
                "name": "Ocean Currents",
                "description": "Global Ocean Currents from OSCAR (2003-2022) and CMEMS (2023-present)",
                "variables": ["uo", "vo", "u", "v", "ug", "vg", "current_speed", "current_direction", "speed", "direction", "thetao", "so"],
                "file_pattern": "currents_harmonized_*.nc",
                "spatial_resolution": "Variable: OSCAR 1°, CMEMS 0.083°"
            },
            "acidity_historical": {
                "name": "Ocean Biogeochemistry - Historical Nutrients",
                "description": "CMEMS historical biogeochemistry data (1993-2022) with nutrients and biological variables",
                "variables": ["no3", "po4", "si", "o2", "chl", "nppv"],
                "file_pattern": "acidity_historical_harmonized_*.nc",
                "spatial_resolution": "0.25° degree",
                "temporal_coverage": "1993-2022",
                "data_source": "GLOBAL_MULTIYEAR_BGC_001_029"
            },
            "acidity_current": {
                "name": "Ocean Biogeochemistry - Current pH/Carbon", 
                "description": "CMEMS current biogeochemistry data (2021-present) with pH and carbon variables",
                "variables": ["ph", "dissic", "talk"],
                "file_pattern": "acidity_current_harmonized_*.nc",
                "spatial_resolution": "0.25° degree", 
                "temporal_coverage": "2021-present",
                "data_source": "GLOBAL_ANALYSISFORECAST_BGC_001_028"
            },
            "microplastics": {
                "name": "Marine Microplastics",
                "description": "NOAA microplastics data (1993-2019) combined with GAN-generated synthetic data (2019-2025)",
                "variables": ["microplastics_concentration", "confidence", "data_source", "ocean_region", "sampling_method", "mesh_size", "water_depth", "organization"],
                "file_pattern": "microplastics_complete_1993_2025.nc",
                "spatial_resolution": "Point data (harmonized coordinates)",
                "temporal_coverage": "1993-2025",
                "data_reliability": {
                    "real_data": "1993-2019 (confidence=1.0)",
                    "synthetic_data": "2019-2025 (confidence=0.7)"
                }
            }
        }
        
        logger.info("🔧 Data extractor initialized")
    
    def _cleanup(self):
        """Clean up resources on shutdown."""
        try:
            if hasattr(self, 'executor') and self.executor:
                logger.info("🧹 Shutting down ThreadPoolExecutor...")
                self.executor.shutdown(wait=True)
                logger.info("✅ ThreadPoolExecutor shutdown complete")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def _create_enhanced_data_value(
        self, 
        value: Any, 
        units: str, 
        long_name: str, 
        valid: bool,
        parameter_name: str,
        location: Optional[Tuple[float, float]] = None,
        date: Optional[str] = None
    ) -> DataValue:
        """Create a DataValue with enhanced educational context and dynamic descriptions."""
        # Get classification and educational context
        classification = parameter_interpreter.get_parameter_classification(
            parameter_name, value, location, date
        )
        educational_context = parameter_interpreter.get_educational_context(parameter_name)
        
        return DataValue(
            value=value if not (isinstance(value, float) and np.isnan(value)) else None,
            units=units,
            long_name=long_name,
            valid=valid,
            classification=classification,
            educational_context=educational_context
        )
    
    def _add_ecosystem_insights(self, datasets: Dict[str, Any], location: Tuple[float, float]) -> Dict[str, Any]:
        """Add ecosystem-level insights based on multi-parameter analysis."""
        # Extract numeric measurements from all datasets
        measurements = {}
        
        for dataset_name, dataset_data in datasets.items():
            if isinstance(dataset_data, dict) and 'error' not in dataset_data:
                if hasattr(dataset_data, 'data'):
                    for param_name, param_data in dataset_data.data.items():
                        if param_data.valid and isinstance(param_data.value, (int, float)):
                            measurements[param_name] = param_data.value
        
        # Get ecosystem insights
        if measurements:
            insights = parameter_interpreter.interpret_multi_parameter_context(measurements)
            if insights:
                datasets['_ecosystem_insights'] = {
                    'insights': insights,
                    'measurement_count': len(measurements),
                    'location': f"{location[0]:.2f}°N, {location[1]:.2f}°E"
                }
        
        return datasets

    async def get_available_datasets(self) -> Dict[str, DatasetInfo]:
        """Get information about all available datasets."""
        datasets = {}
        
        for dataset_id, config in self.dataset_config.items():
            try:
                # Special handling for microplastics
                if dataset_id == "microplastics":
                    microplastics_path = self.data_path / "microplastics" / "unified" / "microplastics_complete_1993_2025.nc"
                    files = [microplastics_path] if microplastics_path.exists() else []
                    
                    # Fixed temporal coverage for microplastics
                    temporal_coverage = {
                        "start": "1993-01-01",
                        "end": "2025-12-31"
                    }
                    latest_date = "2025-12-31"
                else:
                    # Standard file handling for other datasets
                    dataset_path = self.data_path / dataset_id
                    files = list(dataset_path.rglob(config["file_pattern"])) if dataset_path.exists() else []
                    
                    # Get date range
                    dates = []
                    for file_path in files:
                        try:
                            date_str = self._extract_date_from_filename(file_path.name)
                            if date_str:
                                dates.append(date_str)
                        except:
                            continue
                    
                    dates.sort()
                    
                    temporal_coverage = {
                        "start": dates[0] if dates else "No data",
                        "end": dates[-1] if dates else "No data"
                    }
                    latest_date = dates[-1] if dates else None
                
                datasets[dataset_id] = DatasetInfo(
                    name=config["name"],
                    description=config["description"],
                    variables=config["variables"],
                    temporal_coverage=temporal_coverage,
                    spatial_resolution=config["spatial_resolution"],
                    file_count=len(files),
                    latest_date=latest_date
                )
                
            except Exception as e:
                logger.error(f"Error getting info for dataset {dataset_id}: {e}")
                # Create empty dataset info
                datasets[dataset_id] = DatasetInfo(
                    name=config["name"],
                    description=f"{config['description']} (Error: {str(e)})",
                    variables=config["variables"],
                    temporal_coverage={"start": "Error", "end": "Error"},
                    spatial_resolution=config["spatial_resolution"],
                    file_count=0,
                    latest_date=None
                )
        
        return datasets
    
    async def get_available_dates(self) -> Dict[str, List[str]]:
        """Get all available dates for each dataset."""
        available_dates = {}
        
        for dataset_id, config in self.dataset_config.items():
            if dataset_id == "microplastics":
                # Microplastics has all dates in single file
                available_dates[dataset_id] = ["1993-01-01 to 2025-12-31"]
                continue
                
            dataset_path = self.data_path / dataset_id
            if not dataset_path.exists():
                available_dates[dataset_id] = []
                continue
                
            pattern = config["file_pattern"]
            files = list(dataset_path.rglob(pattern))
            
            dates = []
            for file_path in files:
                date_str = self._extract_date_from_filename(file_path.name)
                if date_str:
                    dates.append(date_str)
            
            dates.sort()
            available_dates[dataset_id] = dates
            
        return available_dates

    def _open_dataset_optimized(self, file_path: Path, chunks: Optional[Dict] = None) -> xr.Dataset:
        """
        Open dataset with optimizations for large files.
        Uses dask for chunked loading and memory efficiency.
        """
        try:
            # For large files, use dask chunks for memory efficiency
            if chunks:
                logger.info(f"🚀 Opening large dataset with chunks: {chunks}")
                ds = xr.open_dataset(file_path, chunks=chunks, engine='netcdf4')
            else:
                ds = xr.open_dataset(file_path, engine='netcdf4')
            
            # Check file size and log performance info
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            if file_size_mb > 50:
                logger.info(f"📊 Large file detected: {file_size_mb:.1f}MB, using optimized loading")
            
            return ds
            
        except Exception as e:
            logger.error(f"Failed to open dataset {file_path}: {e}")
            # Fallback to standard opening
            return xr.open_dataset(file_path)

    def _find_nearest_point_optimized(self, ds: xr.Dataset, lat: float, lon: float) -> Tuple[float, float]:
        """
        Optimized spatial lookup for large datasets using numpy operations.
        Faster than xarray sel for chunked/large files.
        """
        try:
            # Determine coordinate names (different datasets use different naming)
            lat_coord = 'latitude' if 'latitude' in ds.coords else 'lat'
            lon_coord = 'longitude' if 'longitude' in ds.coords else 'lon'
            
            # Use numpy operations for faster spatial lookup on large files
            lat_values = ds[lat_coord].values
            lon_values = ds[lon_coord].values
            
            # Find nearest indices using numpy
            lat_idx = np.argmin(np.abs(lat_values - lat))
            lon_idx = np.argmin(np.abs(lon_values - lon))
            
            nearest_lat = float(lat_values[lat_idx])
            nearest_lon = float(lon_values[lon_idx])
            
            logger.debug(f"🎯 Fast spatial lookup: ({lat:.3f}, {lon:.3f}) → ({nearest_lat:.3f}, {nearest_lon:.3f})")
            return nearest_lat, nearest_lon
            
        except Exception as e:
            logger.warning(f"Optimized spatial lookup failed, falling back to standard method: {e}")
            # Fallback to standard xarray method with coordinate detection
            lat_coord = 'latitude' if 'latitude' in ds.coords else 'lat'
            lon_coord = 'longitude' if 'longitude' in ds.coords else 'lon'
            nearest_lat = ds[lat_coord].sel({lat_coord: lat}, method='nearest').values
            nearest_lon = ds[lon_coord].sel({lon_coord: lon}, method='nearest').values
            return float(nearest_lat), float(nearest_lon)

    def _extract_date_from_filename(self, filename: str) -> Optional[str]:
        """Extract date from filename in YYYY-MM-DD format."""
        # Handle different filename patterns
        if "harmonized_" in filename:
            # Format: sst_harmonized_20240115.nc -> 2024-01-15
            date_part = filename.split("_")[-1].split(".")[0]
        elif "processed_" in filename:
            # Format: processed files -> YYYY-MM-DD
            date_part = filename.split("_")[-1].split(".")[0]
        else:
            return None
            
        if len(date_part) == 8 and date_part.isdigit():
            return f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
        return None

    def _resolve_acidity_dataset(self, dataset: str, date_str: Optional[str] = None) -> str:
        """Resolve 'acidity' requests to the appropriate historical/current dataset."""
        # If not an acidity request, return as-is
        if dataset != "acidity":
            return dataset
        
        # If no date provided, default to current data
        if not date_str:
            logger.info("🔄 No date provided for acidity request, defaulting to acidity_current")
            return "acidity_current"
        
        # Parse the date to determine which dataset to use
        try:
            from datetime import datetime
            target_date = datetime.strptime(date_str, "%Y-%m-%d")
            year = target_date.year
            
            # Route based on temporal coverage
            if year <= 2022:
                # Historical period (2003-2022): use historical data
                resolved = "acidity_historical"
                logger.info(f"📅 Date {date_str} (year {year}) → using acidity_historical")
            else:
                # Current period (2023-present): use current data
                resolved = "acidity_current"
                logger.info(f"📅 Date {date_str} (year {year}) → using acidity_current")
            
            return resolved
            
        except Exception as e:
            logger.warning(f"❌ Could not parse date {date_str}: {e}, defaulting to acidity_current")
            return "acidity_current"

    def extract_point_data(self, dataset: str, lat: float, lon: float, date_str: Optional[str] = None) -> PointDataResponse:
        """Smart data extraction with automatic acidity dataset routing."""
        start_time = time.time()
        
        # Smart dataset resolution for acidity data
        resolved_dataset = self._resolve_acidity_dataset(dataset, date_str)
        logger.info(f"📊 Dataset resolution: {dataset} → {resolved_dataset} for date {date_str}")
        
        # Find the data file directly
        file_path = self._find_dataset_file(resolved_dataset, date_str)
        if not file_path:
            logger.warning(f"No data file found for dataset {resolved_dataset} (original: {dataset}) on {date_str}")
            return PointDataResponse(
                dataset=dataset,  # Keep original dataset name in response
                location=Coordinates(lat=lat, lon=lon),
                actual_location=Coordinates(lat=lat, lon=lon),
                date=date_str or "no-data",
                data={},
                extraction_time_ms=0,
                file_source="no-file"
            )
        
        # Optimized data extraction with chunked loading for large files
        try:
            # Use chunked loading for large currents files
            if resolved_dataset == "currents":
                ds = self._open_dataset_optimized(file_path, chunks={'lat': 100, 'lon': 100})
            else:
                ds = xr.open_dataset(file_path)
                
            with ds:
                # Find nearest point with optimized spatial lookup
                if resolved_dataset == "currents":
                    nearest_lat, nearest_lon = self._find_nearest_point_optimized(ds, lat, lon)
                else:
                    # Standard coordinate detection for other datasets
                    lat_coord = 'latitude' if 'latitude' in ds.coords else 'lat'
                    lon_coord = 'longitude' if 'longitude' in ds.coords else 'lon'
                    nearest_lat = ds[lat_coord].sel({lat_coord: lat}, method='nearest').values
                    nearest_lon = ds[lon_coord].sel({lon_coord: lon}, method='nearest').values
                
                # Extract data at the point using variables from resolved dataset
                point_data = {}
                dataset_vars = self.dataset_config.get(resolved_dataset, {}).get("variables", list(ds.data_vars))
                logger.info(f"🔍 Extracting variables for {resolved_dataset}: {dataset_vars}")
                
                for var_name in dataset_vars:
                    if var_name in ds.data_vars and len(ds[var_name].dims) >= 2:  # Skip scalar variables
                        try:
                            # Select by lat/lon first with proper coordinate names
                            lat_coord = 'latitude' if 'latitude' in ds.coords else 'lat'
                            lon_coord = 'longitude' if 'longitude' in ds.coords else 'lon'
                            var_data = ds[var_name].sel({lat_coord: nearest_lat, lon_coord: nearest_lon}, method='nearest')
                            
                            # Handle time dimension - take the first/only time if present
                            if 'time' in var_data.dims:
                                var_data = var_data.isel(time=0)
                            
                            # Handle depth/zlev dimension - take surface (first level) if present
                            if 'zlev' in var_data.dims:
                                var_data = var_data.isel(zlev=0)
                            elif 'depth' in var_data.dims:
                                var_data = var_data.isel(depth=0)
                            
                            value = var_data.values
                            
                            # Handle numpy types
                            if hasattr(value, 'item'):
                                value = value.item()
                            
                            # Get units and long_name if available
                            units = ds[var_name].attrs.get('units', '')
                            long_name = ds[var_name].attrs.get('long_name', var_name)
                            
                            point_data[var_name] = {
                                'value': float(value) if not np.isnan(value) else None,
                                'units': units,
                                'long_name': long_name,
                                'valid': not np.isnan(value)
                            }
                        except Exception as e:
                            logger.warning(f"Failed to extract {var_name}: {e}")
                
                extraction_time = (time.time() - start_time) * 1000
                logger.info(f"✅ Extracted {dataset} data in {extraction_time:.1f}ms")
                
                return PointDataResponse(
                    dataset=dataset,
                    location=Coordinates(lat=lat, lon=lon),
                    actual_location=Coordinates(lat=float(nearest_lat), lon=float(nearest_lon)),
                    date=date_str or "latest",
                    data=point_data,
                    extraction_time_ms=extraction_time,
                    file_source=str(file_path.name)
                )
                
        except Exception as e:
            logger.error(f"Failed to extract data from {file_path}: {e}")
            return PointDataResponse(
                dataset=dataset,
                location=Coordinates(lat=lat, lon=lon),
                actual_location=Coordinates(lat=lat, lon=lon),
                date=date_str or "error",
                data={},
                extraction_time_ms=(time.time() - start_time) * 1000,
                file_source="error"
            )

    async def _extract_point_data_optimized(self, dataset: str, file_path: Path, lat: float, lon: float, cache_date: str) -> PointDataResponse:
        """Ultra-fast point data extraction using smart caching and coordinate grids."""
        start_time = time.time()
        
        try:
            # Special handling for microplastics and discrete data
            if dataset == "microplastics":
                try:
                    return await self._extract_microplastics_optimized(file_path, lat, lon, cache_date)
                except Exception as e:
                    if "NetCDF: HDF error" in str(e) or "Failed to decode" in str(e):
                        logger.warning(f"⚠️ Microplastics data file corrupted, returning no data: {e}")
                        # Return empty response instead of failing
                        return PointDataResponse(
                            dataset="microplastics",
                            location=Coordinates(lat=lat, lon=lon),
                            actual_location=Coordinates(lat=lat, lon=lon),
                            date=cache_date,
                            data={},
                            extraction_time_ms=0.0,
                            file_source="corrupted"
                        )
                    else:
                        raise
            
            
            # OPTIMIZATION: Use smart file manager with coordinate grids
            try:
                ds, coord_grid = await cache_manager.get_dataset_with_grid(file_path, dataset)
                # FAST SPATIAL LOOKUP: Use pre-loaded coordinate grid
                lat_idx, lon_idx, actual_lat, actual_lon = coord_grid.find_nearest_indices(lat, lon)
            except RuntimeError as e:
                if "Coordinate grid not available" in str(e):
                    # Fallback for ultra-large files: open dataset directly and do direct coordinate lookup
                    logger.info(f"⚡ Using direct coordinate lookup for large file: {dataset}")
                    ds = await cache_manager.file_manager.get_dataset(file_path, dataset)
                    
                    # Direct coordinate lookup without grid
                    lat_coord = 'latitude' if 'latitude' in ds.coords else 'lat'
                    lon_coord = 'longitude' if 'longitude' in ds.coords else 'lon'
                    
                    # Use sel method with nearest for chunked datasets (works with dask arrays)
                    ds_sel = ds.sel({lat_coord: lat, lon_coord: lon}, method='nearest')
                    actual_lat = float(ds_sel[lat_coord].values)
                    actual_lon = float(ds_sel[lon_coord].values)
                    lat_idx, lon_idx = None, None  # Not needed for direct selection
                else:
                    raise
            
            # Determine coordinate names
            lat_coord = 'latitude' if 'latitude' in ds.coords else 'lat'
            lon_coord = 'longitude' if 'longitude' in ds.coords else 'lon'
            
            # Extract data variables efficiently
            data = {}
            variables = self.dataset_config[dataset]["variables"]
            
            for var_name in variables:
                if var_name in ds.data_vars:
                    # Choose extraction method based on whether we have indices or direct selection
                    if lat_idx is not None and lon_idx is not None:
                        # Direct indexing - much faster than searching
                        var_data = ds[var_name].isel({lat_coord: lat_idx, lon_coord: lon_idx})
                    else:
                        # Direct coordinate selection for chunked datasets
                        var_data = ds[var_name].sel({lat_coord: actual_lat, lon_coord: actual_lon}, method='nearest')
                    
                    # Handle time dimension if present
                    if 'time' in var_data.dims:
                        var_data = var_data.isel(time=0)
                    
                    # Handle depth dimension if present (take surface)
                    if 'depth' in var_data.dims:
                        var_data = var_data.isel(depth=0)
                    
                    # Extract scalar value - handle dask arrays properly
                    if hasattr(var_data.values, 'compute'):  # Dask array
                        value = float(var_data.values.compute().item())
                    else:
                        value = float(var_data.values.item() if var_data.values.ndim == 0 else var_data.values.flatten()[0])
                    
                    # Create enhanced DataValue with educational context
                    data[var_name] = self._create_enhanced_data_value(
                        value=value,
                        units=var_data.attrs.get("units", "unknown"),
                        long_name=var_data.attrs.get("long_name", var_name),
                        valid=not np.isnan(value),
                        parameter_name=var_name,
                        location=(lat, lon),
                        date=cache_date
                    )
            
            # Get date from dataset or filename
            data_date = self._get_data_date(ds, file_path)
            
            extraction_time = (time.time() - start_time) * 1000
            
            # CACHE THE RESULT for future requests
            await cache_manager.cache_point(
                dataset, lat, lon, cache_date, 
                {k: {
                    'value': v.value,
                    'units': v.units,
                    'long_name': v.long_name,
                    'valid': v.valid
                } for k, v in data.items()},  # Convert DataValue to dict for caching
                extraction_time, 
                (actual_lat, actual_lon)
            )
            
            logger.info(f"⚡ OPTIMIZED EXTRACTION: {dataset} at ({lat}, {lon}) in {extraction_time:.1f}ms")
            
            return PointDataResponse(
                dataset=dataset,
                location=Coordinates(lat=lat, lon=lon),
                actual_location=Coordinates(lat=actual_lat, lon=actual_lon),
                date=data_date,
                data=data,
                extraction_time_ms=round(extraction_time, 2),
                file_source=str(file_path)
            )
            
        except Exception as e:
            logger.error(f"Error in optimized extraction: {e}")
            raise

    async def _extract_microplastics_optimized(self, file_path: Path, lat: float, lon: float, cache_date: str) -> PointDataResponse:
        """Optimized microplastics extraction with caching."""
        # Use legacy method for now but add caching
        loop = asyncio.get_event_loop()
        start_time = time.time()
        
        result = await loop.run_in_executor(
            self.executor,
            self._extract_microplastics_point_data,
            file_path, lat, lon, start_time
        )
        
        # Cache the result
        if result.data:
            await cache_manager.cache_point(
                "microplastics", lat, lon, cache_date,
                {k: {
                    'value': v.value,
                    'units': v.units,
                    'long_name': v.long_name,
                    'valid': v.valid
                } for k, v in result.data.items()},
                result.extraction_time_ms,
                (result.actual_location.lat, result.actual_location.lon)
            )
        
        return result

    async def _extract_discrete_optimized(self, dataset: str, file_path: Path, lat: float, lon: float, cache_date: str) -> PointDataResponse:
        """Optimized discrete sample extraction with caching."""
        # Use legacy method for now but add caching
        loop = asyncio.get_event_loop()
        start_time = time.time()
        
        result = await loop.run_in_executor(
            self.executor,
            self._extract_discrete_sample_data,
            dataset, file_path, lat, lon, start_time
        )
        
        # Cache the result
        if result.data:
            await cache_manager.cache_point(
                dataset, lat, lon, cache_date,
                {k: {
                    'value': v.value,
                    'units': v.units,
                    'long_name': v.long_name,
                    'valid': v.valid
                } for k, v in result.data.items()},
                result.extraction_time_ms,
                (result.actual_location.lat, result.actual_location.lon)
            )
        
        return result

    def _extract_point_data_sync(self, dataset: str, file_path: Path, lat: float, lon: float) -> PointDataResponse:
        """Synchronous point data extraction with proper resource cleanup."""
        start_time = time.time()
        ds = None
        
        try:
            # Special handling for microplastics point data
            if dataset == "microplastics":
                return self._extract_microplastics_point_data(file_path, lat, lon, start_time)
            
            # Standard gridded data extraction with explicit resource management
            try:
                ds = xr.open_dataset(file_path)
            except Exception as e:
                logger.error(f"Failed to open NetCDF file {file_path}: {e}")
                raise
                
            try:
                # Determine coordinate names (different datasets use different names)
                lat_coord = 'latitude' if 'latitude' in ds.coords else 'lat'
                lon_coord = 'longitude' if 'longitude' in ds.coords else 'lon'
                
                # Find nearest grid point
                lat_idx = np.argmin(np.abs(ds[lat_coord].values - lat))
                lon_idx = np.argmin(np.abs(ds[lon_coord].values - lon))
                
                actual_lat = float(ds[lat_coord].values[lat_idx])
                actual_lon = float(ds[lon_coord].values[lon_idx])
                
                # Extract data variables
                data = {}
                variables = self.dataset_config[dataset]["variables"]
                
                for var_name in variables:
                    if var_name in ds.data_vars:
                        var_data = ds[var_name].isel({lat_coord: lat_idx, lon_coord: lon_idx})
                        
                        # Handle time dimension if present
                        if 'time' in var_data.dims:
                            var_data = var_data.isel(time=0)
                        
                        # Handle depth dimension if present (take surface)
                        if 'depth' in var_data.dims:
                            var_data = var_data.isel(depth=0)
                        
                        # Extract scalar value
                        value = float(var_data.values.item() if var_data.values.ndim == 0 else var_data.values.flatten()[0])
                        
                        # Create enhanced DataValue with educational context
                        data[var_name] = self._create_enhanced_data_value(
                            value=value,
                            units=var_data.attrs.get("units", "unknown"),
                            long_name=var_data.attrs.get("long_name", var_name),
                            valid=not np.isnan(value),
                            parameter_name=var_name,
                            location=(lat, lon),
                            date=self._get_data_date(ds, file_path)
                        )
                
                # Get date from dataset or filename
                data_date = self._get_data_date(ds, file_path)
                
                extraction_time = (time.time() - start_time) * 1000
                
                return PointDataResponse(
                    dataset=dataset,
                    location=Coordinates(lat=lat, lon=lon),
                    actual_location=Coordinates(lat=actual_lat, lon=actual_lon),
                    date=data_date,
                    data=data,
                    extraction_time_ms=round(extraction_time, 2),
                    file_source=str(file_path)
                )
            finally:
                # Always close the dataset
                if ds is not None:
                    ds.close()
                
        except Exception as e:
            logger.error(f"Error extracting data from {file_path}: {e}")
            # Ensure cleanup even on error
            if ds is not None:
                try:
                    ds.close()
                except:
                    pass
            raise

    def _extract_microplastics_point_data(self, file_path: Path, lat: float, lon: float, start_time: float) -> PointDataResponse:
        """Extract microplastics point data with nearest neighbor matching."""
        try:
            # Use decode_cf=False to handle corrupted data_source variable
            with xr.open_dataset(file_path, decode_cf=False) as ds:
                # Get coordinate arrays
                lats = ds['latitude'].values
                lons = ds['longitude'].values
                
                # Calculate distances to all points
                lat_diff = lats - lat
                lon_diff = lons - lon
                distances = np.sqrt(lat_diff**2 + lon_diff**2)
                
                # Find nearest point
                nearest_idx = np.argmin(distances)
                
                # Check if nearest point is within reasonable distance (5 degrees)
                min_distance = distances[nearest_idx]
                if min_distance > 5.0:
                    # No nearby data point found
                    extraction_time = (time.time() - start_time) * 1000
                    return PointDataResponse(
                        dataset="microplastics",
                        location=Coordinates(lat=lat, lon=lon),
                        actual_location=Coordinates(lat=lat, lon=lon),
                        date="no-data",
                        data={},
                        extraction_time_ms=round(extraction_time, 2),
                        file_source=str(file_path)
                    )
                
                # Extract data at nearest point
                actual_lat = float(lats[nearest_idx])
                actual_lon = float(lons[nearest_idx])
                
                # Get data values
                concentration = float(ds['microplastics_concentration'].values[nearest_idx])
                confidence = float(ds['confidence'].values[nearest_idx])
                data_source = str(ds['data_source'].values[nearest_idx])
                
                # Get date from time coordinate - handle raw numeric values due to decode_cf=False
                time_val = ds['time'].values[nearest_idx]  
                try:
                    if hasattr(time_val, 'strftime'):
                        data_date = time_val.strftime('%Y-%m-%d')
                    elif isinstance(time_val, (int, float, np.integer, np.floating)):
                        # Raw numeric time value - try to convert to date
                        # Assume it's days since epoch or similar
                        try:
                            dt = pd.to_datetime(time_val, unit='D', origin='1990-01-01')
                            data_date = dt.strftime('%Y-%m-%d')
                        except:
                            # Fallback to generic date
                            data_date = "2020-01-01"  # Generic date for microplastics
                    else:
                        # Handle numpy datetime64 or other formats
                        dt = np.datetime64(time_val, 'D')
                        data_date = str(dt)
                except Exception as time_error:
                    logger.warning(f"Could not parse time value {time_val}, using fallback date: {time_error}")
                    data_date = "2020-01-01"
                
                # Build response data with environmental metadata and enhanced context
                data = {
                    "microplastics_concentration": self._create_enhanced_data_value(
                        value=concentration,
                        units="pieces/m³",
                        long_name="Microplastics Concentration",
                        valid=not np.isnan(concentration),
                        parameter_name="microplastics_concentration",
                        location=(lat, lon),
                        date=data_date
                    ),
                    "confidence": self._create_enhanced_data_value(
                        value=confidence,
                        units="ratio",
                        long_name="Data Confidence Level",
                        valid=not np.isnan(confidence),
                        parameter_name="confidence",
                        location=(lat, lon),
                        date=data_date
                    ),
                    "data_source": self._create_enhanced_data_value(
                        value=data_source,
                        units="category",
                        long_name="Data Source Type (real/synthetic)",
                        valid=True,
                        parameter_name="data_source",
                        location=(lat, lon),
                        date=data_date
                    )
                }
                
                # Add environmental metadata if available
                metadata_vars = ["ocean_region", "sampling_method", "mesh_size", "water_depth", "organization"]
                for var_name in metadata_vars:
                    if var_name in ds.variables:
                        try:
                            var_value = ds[var_name].values[nearest_idx]
                            if isinstance(var_value, (bytes, np.bytes_)):
                                var_value = var_value.decode('utf-8')
                            elif isinstance(var_value, np.ndarray):
                                var_value = str(var_value.item())
                            else:
                                var_value = str(var_value)
                            
                            # Add to data if valid
                            if var_value and var_value != 'nan' and var_value != 'None':
                                data[var_name] = DataValue(
                                    value=var_value,
                                    units="metadata" if var_name in ["ocean_region", "sampling_method", "organization"] else 
                                          "mm" if var_name == "mesh_size" else
                                          "m" if var_name == "water_depth" else "unknown",
                                    long_name={
                                        "ocean_region": "Ocean Region",
                                        "sampling_method": "Sampling Method",
                                        "mesh_size": "Mesh Size",
                                        "water_depth": "Water Sampling Depth",
                                        "organization": "Data Collection Organization"
                                    }.get(var_name, var_name.replace('_', ' ').title()),
                                    valid=True
                                )
                        except Exception as e:
                            logger.warning(f"Error extracting {var_name}: {e}")
                            continue
                
                # Add concentration classification
                if not np.isnan(concentration):
                    if concentration <= 0.0005:
                        class_text = "Very Low"
                    elif concentration <= 0.005:
                        class_text = "Low"
                    elif concentration <= 1.0:
                        class_text = "Medium"
                    elif concentration <= 100.0:
                        class_text = "High"
                    else:
                        class_text = "Very High"
                    
                    data["concentration_class"] = self._create_enhanced_data_value(
                        value=class_text,
                        units="category",
                        long_name="Concentration Classification",
                        valid=True,
                        parameter_name="concentration_class",
                        location=(lat, lon),
                        date=data_date
                    )
                
                extraction_time = (time.time() - start_time) * 1000
                
                return PointDataResponse(
                    dataset="microplastics", 
                    location=Coordinates(lat=lat, lon=lon),
                    actual_location=Coordinates(lat=actual_lat, lon=actual_lon),
                    date=data_date,
                    data=data,
                    extraction_time_ms=round(extraction_time, 2),
                    file_source=str(file_path)
                )
                
        except Exception as e:
            logger.error(f"Error extracting microplastics data from {file_path}: {e}")
            raise

    def _extract_discrete_sample_data(self, dataset: str, file_path: Path, lat: float, lon: float, start_time: float) -> PointDataResponse:
        """Extract discrete sample data (e.g., GLODAP pH data) with nearest neighbor matching."""
        try:
            with xr.open_dataset(file_path) as ds:
                # GLODAP data uses 'obs' dimension for individual observations
                if 'obs' not in ds.dims:
                    raise ValueError(f"Expected 'obs' dimension in discrete sample dataset {dataset}")
                
                # Get coordinate arrays
                lats = ds['latitude'].values
                lons = ds['longitude'].values
                
                # Calculate distances to all observation points
                lat_diff = lats - lat
                lon_diff = lons - lon
                distances = np.sqrt(lat_diff**2 + lon_diff**2)
                
                # Find nearest sample point
                nearest_idx = np.argmin(distances)
                
                # Check if nearest point is within reasonable distance (2 degrees for discrete samples)
                min_distance = distances[nearest_idx]
                if min_distance > 2.0:
                    # No nearby sample found
                    extraction_time = (time.time() - start_time) * 1000
                    return PointDataResponse(
                        dataset=dataset,
                        location=Coordinates(lat=lat, lon=lon),
                        actual_location=Coordinates(lat=lat, lon=lon),
                        date="no-data",
                        data={},
                        extraction_time_ms=round(extraction_time, 2),
                        file_source=str(file_path)
                    )
                
                # Extract data at nearest sample point
                actual_lat = float(lats[nearest_idx])
                actual_lon = float(lons[nearest_idx])
                
                # Get data values for all variables
                data = {}
                variables = self.dataset_config[dataset]["variables"]
                
                for var_name in variables:
                    if var_name in ds.data_vars:
                        var_data = ds[var_name].isel(obs=nearest_idx)
                        value = float(var_data.values.item())
                        
                        data[var_name] = self._create_enhanced_data_value(
                            value=value,
                            units=var_data.attrs.get("units", "unknown"),
                            long_name=var_data.attrs.get("long_name", var_name),
                            valid=not np.isnan(value),
                            parameter_name=var_name,
                            location=(lat, lon),
                            date=data_date
                        )
                
                # Get observation date from time coordinate
                if 'time' in ds.coords:
                    time_val = ds['time'].isel(obs=nearest_idx).values
                    if hasattr(time_val, 'strftime'):
                        data_date = time_val.strftime('%Y-%m-%d')
                    else:
                        # Handle numpy datetime64
                        dt = np.datetime64(time_val, 'D')
                        data_date = str(dt)
                else:
                    data_date = "unknown"
                
                # Add metadata about sample type and interpolation
                data["_sample_distance"] = DataValue(
                    value=round(min_distance * 111, 1),  # Convert degrees to km
                    units="km",
                    long_name="Distance to Nearest Sample",
                    valid=True
                )
                
                data["_data_type"] = DataValue(
                    value="discrete_sample",
                    units="category",
                    long_name="Data Type",
                    valid=True
                )
                
                extraction_time = (time.time() - start_time) * 1000
                
                return PointDataResponse(
                    dataset=dataset,
                    location=Coordinates(lat=lat, lon=lon),
                    actual_location=Coordinates(lat=actual_lat, lon=actual_lon),
                    date=data_date,
                    data=data,
                    extraction_time_ms=round(extraction_time, 2),
                    file_source=str(file_path)
                )
                
        except Exception as e:
            logger.error(f"Error extracting discrete sample data from {file_path}: {e}")
            raise

    async def get_all_microplastics_points(self, 
                                         min_concentration: Optional[float] = None,
                                         data_source: Optional[str] = None,
                                         year_min: Optional[int] = None,
                                         year_max: Optional[int] = None,
                                         spatial_bounds: Optional[Dict] = None) -> Dict[str, Any]:
        """Get all microplastics measurement points for visualization."""
        logger.info("Fetching all microplastics points for visualization overlay")
        
        # Find microplastics file
        file_path = self._find_dataset_file("microplastics")
        if not file_path:
            raise ValueError("Microplastics dataset not found")
        
        # Load data in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._get_microplastics_points_sync,
            file_path, min_concentration, data_source, year_min, year_max, spatial_bounds
        )
    
    def _get_microplastics_points_sync(self, 
                                      file_path: Path,
                                      min_concentration: Optional[float],
                                      data_source: Optional[str],
                                      year_min: Optional[int],
                                      year_max: Optional[int],
                                      spatial_bounds: Optional[Dict]) -> Dict[str, Any]:
        """Synchronously extract all microplastics points."""
        try:
            with xr.open_dataset(file_path) as ds:
                # Extract arrays
                lats = ds['latitude'].values
                lons = ds['longitude'].values
                concentrations = ds['microplastics_concentration'].values
                confidences = ds['confidence'].values
                data_sources = ds['data_source'].values
                times = ds['time'].values
                
                # Convert times to years
                years = np.array([pd.Timestamp(t).year for t in times])
                
                # Apply filters
                mask = np.ones(len(lats), dtype=bool)
                
                if min_concentration is not None:
                    mask &= concentrations >= min_concentration
                
                if data_source is not None:
                    mask &= np.array([ds == data_source for ds in data_sources])
                
                if year_min is not None:
                    mask &= years >= year_min
                
                if year_max is not None:
                    mask &= years <= year_max
                
                if spatial_bounds is not None:
                    mask &= (lons >= spatial_bounds['min_lon']) & (lons <= spatial_bounds['max_lon'])
                    mask &= (lats >= spatial_bounds['min_lat']) & (lats <= spatial_bounds['max_lat'])
                
                # Apply mask
                filtered_lats = lats[mask]
                filtered_lons = lons[mask]
                filtered_concentrations = concentrations[mask]
                filtered_confidences = confidences[mask]
                filtered_sources = data_sources[mask]
                filtered_times = times[mask]
                
                # Create GeoJSON features
                features = []
                for i in range(len(filtered_lats)):
                    # Determine concentration class
                    conc = filtered_concentrations[i]
                    if conc <= 0.0005:
                        conc_class = "Very Low"
                    elif conc <= 0.005:
                        conc_class = "Low"
                    elif conc <= 1.0:
                        conc_class = "Medium"
                    elif conc <= 100.0:
                        conc_class = "High"
                    else:
                        conc_class = "Very High"
                    
                    # Format date
                    date_str = str(pd.Timestamp(filtered_times[i]).date())
                    
                    feature = {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [float(filtered_lons[i]), float(filtered_lats[i])]
                        },
                        "properties": {
                            "concentration": float(filtered_concentrations[i]),
                            "confidence": float(filtered_confidences[i]),
                            "data_source": str(filtered_sources[i]),
                            "date": date_str,
                            "concentration_class": conc_class
                        }
                    }
                    features.append(feature)
                
                # Create summary statistics
                summary = {
                    "total_points": len(features),
                    "filtered_from": len(lats),
                    "real_points": sum(1 for f in features if f['properties']['data_source'] == 'real'),
                    "synthetic_points": sum(1 for f in features if f['properties']['data_source'] == 'synthetic'),
                    "concentration_range": {
                        "min": float(np.min(filtered_concentrations)) if len(filtered_concentrations) > 0 else 0,
                        "max": float(np.max(filtered_concentrations)) if len(filtered_concentrations) > 0 else 0,
                        "mean": float(np.mean(filtered_concentrations)) if len(filtered_concentrations) > 0 else 0
                    },
                    "temporal_range": {
                        "start": str(pd.Timestamp(filtered_times.min()).date()) if len(filtered_times) > 0 else None,
                        "end": str(pd.Timestamp(filtered_times.max()).date()) if len(filtered_times) > 0 else None
                    }
                }
                
                return {
                    "type": "FeatureCollection",
                    "features": features,
                    "summary": summary
                }
                
        except Exception as e:
            logger.error(f"Error extracting microplastics points from {file_path}: {e}")
            raise

    def _get_data_date(self, ds: xr.Dataset, file_path: Path) -> str:
        """Get the date from dataset or filename."""
        # Try to get from dataset time coordinate
        if 'time' in ds.coords:
            try:
                time_val = ds.time.values[0] if ds.time.size > 0 else ds.time.values
                if hasattr(time_val, 'strftime'):
                    return time_val.strftime('%Y-%m-%d')
                else:
                    # Handle numpy datetime64
                    dt = np.datetime64(time_val, 'D')
                    return str(dt)
            except:
                pass
        
        # Fallback to filename
        return self._extract_date_from_filename(file_path.name) or "unknown"

    def _find_dataset_file(self, dataset: str, date_str: Optional[str] = None) -> Optional[Path]:
        """
        Simple, direct file path construction - no scanning, no fallbacks.
        Since all data is available, we use predictable file paths.
        """
        base_path = Path(__file__).parent.parent.parent.parent / "ocean-data" / "processed" / "unified_coords"
        
        # Handle latest date requests by using today's date
        if not date_str or date_str == "latest":
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        # Convert date format and extract year/month
        try:
            date_formatted = date_str.replace('-', '')
            year = date_str[:4]
            month = date_str[5:7]
        except:
            logger.error(f"Invalid date format: {date_str}")
            return None
        
        # Direct path construction with proper directory structure
        file_patterns = {
            "sst": f"sst/{year}/{month}/sst_harmonized_{date_formatted}.nc",
            "currents": f"currents/{year}/{month}/currents_harmonized_{date_formatted}.nc", 
            "acidity": f"acidity_current/{year}/{month}/acidity_current_harmonized_{date_formatted}.nc",
            "acidity_current": f"acidity_current/{year}/{month}/acidity_current_harmonized_{date_formatted}.nc",
            "acidity_historical": f"acidity_historical/{year}/{month}/acidity_historical_harmonized_{date_formatted}.nc",
            "microplastics": "microplastics/unified/microplastics_complete_1993_2025.nc"
        }
        
# All currents files now use uniform naming - no special handling needed
        
        if dataset not in file_patterns:
            logger.error(f"Unknown dataset: {dataset}")
            return None
        
        file_path = base_path / file_patterns[dataset]
        
        if file_path.exists():
            logger.info(f"✅ Found file: {file_path}")
            return file_path
        else:
            logger.warning(f"❌ File not found: {file_path}")
            return None
    
    def _validate_dataset_file(self, file_path: Path) -> bool:
        """Validate that a dataset file has proper coordinates and variables."""
        try:
            with xr.open_dataset(file_path) as ds:
                # Check that file has coordinates and variables
                if len(ds.coords) == 0 or len(ds.data_vars) == 0:
                    logger.warning(f"Corrupted file detected (no coords/vars): {file_path.name}")
                    return False
                
                # Check for required coordinates
                has_lat = any('lat' in coord.lower() for coord in ds.coords)
                has_lon = any('lon' in coord.lower() for coord in ds.coords)
                
                if not (has_lat and has_lon):
                    logger.warning(f"File missing lat/lon coordinates: {file_path.name}")
                    return False
                
                return True
                
        except Exception as e:
            logger.warning(f"Error validating file {file_path.name}: {e}")
            return False

    def extract_multi_point_data(self, datasets: List[str], lat: float, lon: float, date_str: Optional[str] = None) -> MultiDatasetResponse:
        """Simple multi-dataset extraction - no async, no timeouts, no parallel complexity."""
        start_time = time.time()
        logger.info(f"🔄 Simple multi-dataset extraction for {datasets} at ({lat}, {lon})")
        
        # Extract data from each dataset sequentially
        dataset_data = {}
        for dataset in datasets:
            try:
                logger.info(f"📊 Extracting {dataset}")
                result = self.extract_point_data(dataset, lat, lon, date_str)
                dataset_data[dataset] = result
                logger.info(f"✅ Successfully extracted data for {dataset}")
            except Exception as e:
                logger.error(f"❌ Error extracting data for {dataset}: {e}")
                dataset_data[dataset] = {
                    "error": str(e),
                    "dataset": dataset
                }
        
        total_time = (time.time() - start_time) * 1000
        
        # Use provided date or "latest"
        response_date = date_str or "latest"
        if dataset_data and not date_str:
            for data in dataset_data.values():
                if hasattr(data, 'date'):
                    response_date = data.date
                    break
        
        return MultiDatasetResponse(
            location=Coordinates(lat=lat, lon=lon),
            date=response_date,
            datasets=dataset_data,
            total_extraction_time_ms=round(total_time, 2)
        )

    async def _handle_acidity_fallback(self, requested_dataset: str, lat: float, lon: float, date_str: Optional[str], start_time: float) -> PointDataResponse:
        """Optimized acidity data fallback with intelligent dataset selection."""
        from datetime import datetime
        
        logger.info(f"🔄 Optimized acidity fallback for {requested_dataset}, date: {date_str}")
        
        # Define optimal fallback strategy based on date and temporal coverage
        fallback_order = []
        optimal_dataset = None
        
        if date_str:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d")
                year = target_date.year
                
                # Optimized dataset selection based on temporal coverage
                if year <= 2022:
                    # Historical period (2003-2022): historical data is primary
                    optimal_dataset = "acidity_historical"
                    fallback_order = ["acidity_historical", "acidity_current"]
                elif year >= 2023:
                    # Current period (2023-present): current data is primary
                    optimal_dataset = "acidity_current" 
                    fallback_order = ["acidity_current", "acidity_historical"]
                else:
                    # Edge case: try both
                    fallback_order = ["acidity_current", "acidity_historical"]
                
                logger.info(f"📅 Date {date_str} (year {year}) → optimal dataset: {optimal_dataset}")
                
            except Exception as e:
                logger.warning(f"Invalid date format {date_str}: {e}, trying all datasets")
                fallback_order = ["acidity_current", "acidity_historical"]
        else:
            # No date specified, prefer current data for real-time queries
            optimal_dataset = "acidity_current"
            fallback_order = ["acidity_current", "acidity_historical"]
        
        # Remove the originally requested dataset to avoid infinite recursion
        fallback_order = [ds for ds in fallback_order if ds != requested_dataset]
        
        # Track fallback performance
        fallback_attempts = 0
        fallback_start_time = time.time()
        
        # Try each fallback dataset with early success detection
        for fallback_dataset in fallback_order:
            try:
                fallback_attempts += 1
                attempt_start = time.time()
                logger.info(f"🧪 Trying fallback dataset {fallback_attempts}/{len(fallback_order)}: {fallback_dataset}")
                
                # Fast file existence check before extraction attempt
                file_path = self._find_dataset_file(fallback_dataset, date_str)
                if file_path:
                    logger.info(f"✅ Found data file in {fallback_dataset}, extracting...")
                    
                    # Extract data using the fallback dataset
                    try:
                        result = await self._extract_point_data_optimized(fallback_dataset, file_path, lat, lon, date_str or "latest")
                        
                        # Calculate fallback performance metrics
                        attempt_time = (time.time() - attempt_start) * 1000
                        total_fallback_time = (time.time() - fallback_start_time) * 1000
                        
                        # Add enhanced metadata about fallback with performance info
                        if result.data:
                            result.data["_fallback_info"] = DataValue(
                                value=f"Data from {fallback_dataset} (fallback from {requested_dataset})",
                                units="metadata",
                                long_name="Data Source Fallback Information",
                                valid=True
                            )
                            result.data["_fallback_performance"] = DataValue(
                                value=f"Success in {attempt_time:.1f}ms (attempt {fallback_attempts}/{len(fallback_order)})",
                                units="metadata",
                                long_name="Fallback Performance Metrics",
                                valid=True
                            )
                            result.data["_optimal_dataset"] = DataValue(
                                value=optimal_dataset or "unknown",
                                units="metadata", 
                                long_name="Optimal Dataset for This Date",
                                valid=True
                            )
                        
                        logger.info(f"🎯 SUCCESS: Acidity fallback to {fallback_dataset} completed in {attempt_time:.1f}ms (total: {total_fallback_time:.1f}ms)")
                        return result
                        
                    except Exception as e:
                        attempt_time = (time.time() - attempt_start) * 1000
                        logger.warning(f"❌ Extraction failed for {fallback_dataset} in {attempt_time:.1f}ms: {e}")
                        continue
                else:
                    attempt_time = (time.time() - attempt_start) * 1000
                    logger.warning(f"❌ No file found for {fallback_dataset} in {attempt_time:.1f}ms")
                        
            except Exception as e:
                attempt_time = (time.time() - attempt_start) * 1000
                logger.warning(f"❌ Error checking fallback dataset {fallback_dataset} in {attempt_time:.1f}ms: {e}")
                continue
        
        # No fallback worked, return empty response with information
        extraction_time = (time.time() - start_time) * 1000
        logger.warning(f"❌ All acidity fallbacks failed for {requested_dataset}")
        
        return PointDataResponse(
            dataset=requested_dataset,
            location=Coordinates(lat=lat, lon=lon),
            actual_location=Coordinates(lat=lat, lon=lon),
            date=date_str or "no-data",
            data={
                "_availability_info": DataValue(
                    value="No acidity data available for this date/location",
                    units="metadata",
                    long_name="Data Availability Information", 
                    valid=True
                ),
                "_attempted_fallbacks": DataValue(
                    value=", ".join(fallback_order),
                    units="metadata",
                    long_name="Attempted Fallback Datasets",
                    valid=True
                )
            },
            extraction_time_ms=round(extraction_time, 2),
            file_source="no-data-fallback"
        )