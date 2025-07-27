"""
Data extraction engine for Ocean Data Management API.

Handles reading NetCDF files and extracting point data with high performance.
Supports all datasets: SST, waves, currents, and acidity.
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

logger = logging.getLogger(__name__)

class DataExtractor:
    """High-performance data extraction engine."""
    
    def __init__(self):
        """Initialize the data extractor."""
        self.data_path = Path("/Volumes/Backup/panta-rhei-data-map/ocean-data/processed/unified_coords")
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Dataset configuration with ALL available variables
        self.dataset_config = {
            "sst": {
                "name": "Sea Surface Temperature",
                "description": "NOAA OISST v2.1 daily sea surface temperature",
                "variables": ["sst", "anom", "err", "ice"],
                "file_pattern": "sst_harmonized_*.nc",
                "spatial_resolution": "1.0° (downsampled from 0.25°)"
            },
            "waves": {
                "name": "Ocean Waves",
                "description": "CMEMS Global Ocean Waves Analysis and Forecast",
                "variables": ["VHM0", "VMDR", "VTPK", "MWD", "PP1D", "VTM10"],
                "file_pattern": "waves_processed_*.nc", 
                "spatial_resolution": "0.083° (1/12 degree)"
            },
            "currents": {
                "name": "Ocean Currents",
                "description": "CMEMS Global Ocean Currents Analysis and Forecast",
                "variables": ["uo", "vo", "u", "v", "speed", "direction", "thetao", "so"],
                "file_pattern": "currents_harmonized_*.nc",
                "spatial_resolution": "0.083° (1/12 degree)"
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
            "acidity": {
                "name": "Ocean Acidity (Multi-Source)",
                "description": "Comprehensive ocean acidity data combining historical nutrients, current pH/carbon, and discrete observations",
                "variables": ["ph", "ph_insitu", "ph_insitu_total", "talk", "dissic", "pco2", "revelle", "no3", "po4", "si", "o2", "chl", "nppv"],
                "file_pattern": "acidity_*.nc",
                "spatial_resolution": "Multi-resolution (0.25° gridded + discrete samples)",
                "temporal_coverage": "1993-present",
                "data_source": "Hybrid (CMEMS + GLODAP)",
                "fallback_datasets": ["acidity_current", "acidity_historical"]
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

    def _extract_date_from_filename(self, filename: str) -> Optional[str]:
        """Extract date from filename in YYYY-MM-DD format."""
        # Handle different filename patterns
        if "harmonized_" in filename:
            # Format: sst_harmonized_20240115.nc -> 2024-01-15
            date_part = filename.split("_")[-1].split(".")[0]
        elif "processed_" in filename:
            # Format: waves_processed_20240723.nc -> 2024-07-23
            date_part = filename.split("_")[-1].split(".")[0]
        else:
            return None
            
        if len(date_part) == 8 and date_part.isdigit():
            return f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
        return None

    async def extract_point_data(self, dataset: str, lat: float, lon: float, date_str: Optional[str] = None) -> PointDataResponse:
        """Extract data at a specific point from the specified dataset with ultra-fast caching."""
        start_time = time.time()
        
        if dataset not in self.dataset_config:
            raise ValueError(f"Unknown dataset: {dataset}")
        
        # CACHE LAYER 1: Check memory cache first
        cache_date = date_str or "latest"
        cached_point = await cache_manager.get_cached_point(dataset, lat, lon, cache_date)
        
        if cached_point:
            # Cache hit - return cached data instantly
            cache_time = (time.time() - start_time) * 1000
            logger.info(f"🚀 CACHE HIT: {dataset} at ({lat}, {lon}) in {cache_time:.1f}ms")
            
            return PointDataResponse(
                dataset=dataset,
                location=Coordinates(lat=lat, lon=lon),
                actual_location=Coordinates(lat=cached_point.actual_location[0], 
                                          lon=cached_point.actual_location[1]),
                date=cache_date,
                data=cached_point.data,
                extraction_time_ms=cache_time,
                file_source="cache"
            )
        
        # Cache miss - extract from file with optimization and fallback strategy
        file_path = await self._find_dataset_file(dataset, date_str)
        if not file_path:
            # ACIDITY FALLBACK STRATEGY: Try alternative acidity datasets
            if dataset in ["acidity_historical", "acidity_current", "acidity"] or dataset.startswith("acidity"):
                logger.info(f"No direct data for {dataset}, attempting acidity fallback strategy")
                return await self._handle_acidity_fallback(dataset, lat, lon, date_str, start_time)
            
            # Return empty response for other datasets
            logger.warning(f"No data file found for dataset {dataset}, returning empty response")
            return PointDataResponse(
                dataset=dataset,
                location=Coordinates(lat=lat, lon=lon),
                actual_location=Coordinates(lat=lat, lon=lon),
                date=date_str or "no-data",
                data={},
                extraction_time_ms=0,
                file_source="no-file"
            )
        
        # OPTIMIZATION: Use smart file manager and coordinate grids
        try:
            return await self._extract_point_data_optimized(dataset, file_path, lat, lon, cache_date)
        except Exception as e:
            logger.error(f"Optimized extraction failed, falling back to legacy method: {e}")
            # Fallback to legacy method
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self.executor, 
                self._extract_point_data_sync, 
                dataset, file_path, lat, lon
            )

    async def _extract_point_data_optimized(self, dataset: str, file_path: Path, lat: float, lon: float, cache_date: str) -> PointDataResponse:
        """Ultra-fast point data extraction using smart caching and coordinate grids."""
        start_time = time.time()
        
        try:
            # Special handling for microplastics and discrete data
            if dataset == "microplastics":
                return await self._extract_microplastics_optimized(file_path, lat, lon, cache_date)
            
            
            # OPTIMIZATION: Use smart file manager with coordinate grids
            ds, coord_grid = await cache_manager.get_dataset_with_grid(file_path, dataset)
            
            # FAST SPATIAL LOOKUP: Use pre-loaded coordinate grid
            lat_idx, lon_idx, actual_lat, actual_lon = coord_grid.find_nearest_indices(lat, lon)
            
            # Determine coordinate names
            lat_coord = 'latitude' if 'latitude' in ds.coords else 'lat'
            lon_coord = 'longitude' if 'longitude' in ds.coords else 'lon'
            
            # Extract data variables efficiently
            data = {}
            variables = self.dataset_config[dataset]["variables"]
            
            for var_name in variables:
                if var_name in ds.data_vars:
                    # Direct indexing - much faster than searching
                    var_data = ds[var_name].isel({lat_coord: lat_idx, lon_coord: lon_idx})
                    
                    # Handle time dimension if present
                    if 'time' in var_data.dims:
                        var_data = var_data.isel(time=0)
                    
                    # Handle depth dimension if present (take surface)
                    if 'depth' in var_data.dims:
                        var_data = var_data.isel(depth=0)
                    
                    # Extract scalar value
                    value = float(var_data.values.item() if var_data.values.ndim == 0 else var_data.values.flatten()[0])
                    
                    data[var_name] = DataValue(
                        value=value if not np.isnan(value) else None,
                        units=var_data.attrs.get("units", "unknown"),
                        long_name=var_data.attrs.get("long_name", var_name),
                        valid=not np.isnan(value)
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
        """Synchronous point data extraction."""
        start_time = time.time()
        
        try:
            # Special handling for microplastics point data
            if dataset == "microplastics":
                return self._extract_microplastics_point_data(file_path, lat, lon, start_time)
            
            # Special handling for discrete GLODAP data
            
            # Standard gridded data extraction
            with xr.open_dataset(file_path) as ds:
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
                        
                        data[var_name] = DataValue(
                            value=value if not np.isnan(value) else None,
                            units=var_data.attrs.get("units", "unknown"),
                            long_name=var_data.attrs.get("long_name", var_name),
                            valid=not np.isnan(value)
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
                
        except Exception as e:
            logger.error(f"Error extracting data from {file_path}: {e}")
            raise

    def _extract_microplastics_point_data(self, file_path: Path, lat: float, lon: float, start_time: float) -> PointDataResponse:
        """Extract microplastics point data with nearest neighbor matching."""
        try:
            with xr.open_dataset(file_path) as ds:
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
                
                # Get date from time coordinate
                time_val = ds['time'].values[nearest_idx]  
                if hasattr(time_val, 'strftime'):
                    data_date = time_val.strftime('%Y-%m-%d')
                else:
                    # Handle numpy datetime64
                    dt = np.datetime64(time_val, 'D')
                    data_date = str(dt)
                
                # Build response data with environmental metadata
                data = {
                    "microplastics_concentration": DataValue(
                        value=concentration if not np.isnan(concentration) else None,
                        units="pieces/m³",
                        long_name="Microplastics Concentration",
                        valid=not np.isnan(concentration)
                    ),
                    "confidence": DataValue(
                        value=confidence if not np.isnan(confidence) else None,
                        units="ratio",
                        long_name="Data Confidence Level",
                        valid=not np.isnan(confidence)
                    ),
                    "data_source": DataValue(
                        value=data_source,
                        units="category",
                        long_name="Data Source Type (real/synthetic)",
                        valid=True
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
                    
                    data["concentration_class"] = DataValue(
                        value=class_text,
                        units="category",
                        long_name="Concentration Classification",
                        valid=True
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
                        
                        data[var_name] = DataValue(
                            value=value if not np.isnan(value) else None,
                            units=var_data.attrs.get("units", "unknown"),
                            long_name=var_data.attrs.get("long_name", var_name),
                            valid=not np.isnan(value)
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
        file_path = await self._find_dataset_file("microplastics")
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

    async def _find_dataset_file(self, dataset: str, date_str: Optional[str] = None) -> Optional[Path]:
        """Find the appropriate file for the dataset and date."""
        # Special handling for microplastics - single file with all data
        if dataset == "microplastics":
            microplastics_path = self.data_path / "microplastics" / "unified" / "microplastics_complete_1993_2025.nc"
            return microplastics_path if microplastics_path.exists() else None
        
        # Standard file finding for other datasets
        dataset_path = self.data_path / dataset
        if not dataset_path.exists():
            return None
        
        pattern = self.dataset_config[dataset]["file_pattern"]
        files = list(dataset_path.rglob(pattern))
        
        if not files:
            return None
        
        if date_str is None:
            # Return the most recent valid file
            files_with_dates = []
            for f in files:
                file_date = self._extract_date_from_filename(f.name)
                if file_date and self._validate_dataset_file(f):
                    files_with_dates.append((file_date, f))
            
            if files_with_dates:
                files_with_dates.sort(key=lambda x: x[0], reverse=True)
                return files_with_dates[0][1]
            else:
                # Fallback: find any valid file
                for f in files:
                    if self._validate_dataset_file(f):
                        return f
                return None  # No valid files found
        
        else:
            # Find file matching the date or nearest available
            files_with_dates = []
            for f in files:
                file_date = self._extract_date_from_filename(f.name)
                if file_date and self._validate_dataset_file(f):
                    if file_date == date_str:
                        # Exact match found
                        return f
                    files_with_dates.append((file_date, f))
            
            # No exact match, find nearest date
            if files_with_dates:
                from datetime import datetime
                
                try:
                    target_date = datetime.strptime(date_str, "%Y-%m-%d")
                    
                    # Sort by distance from target date
                    files_with_dates.sort(key=lambda x: abs((datetime.strptime(x[0], "%Y-%m-%d") - target_date).days))
                    
                    nearest_file = files_with_dates[0][1]
                    nearest_date = files_with_dates[0][0]
                    
                    logger.info(f"No exact date match for {date_str}, using nearest available: {nearest_date}")
                    return nearest_file
                except Exception as e:
                    logger.error(f"Error finding nearest date: {e}")
                    # Fallback to most recent
                    files_with_dates.sort(key=lambda x: x[0], reverse=True)
                    return files_with_dates[0][1]
            
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

    async def extract_multi_point_data(self, datasets: List[str], lat: float, lon: float, date_str: Optional[str] = None) -> MultiDatasetResponse:
        """Extract data from multiple datasets at a single point."""
        start_time = time.time()
        logger.info(f"🔄 Starting multi-dataset extraction for {datasets} at ({lat}, {lon})")
        
        # Validate datasets
        invalid_datasets = [d for d in datasets if d not in self.dataset_config]
        if invalid_datasets:
            raise ValueError(f"Unknown datasets: {invalid_datasets}")
        
        # Extract data from each dataset with timeout protection
        tasks = []
        for dataset in datasets:
            logger.info(f"📊 Creating task for dataset: {dataset}")
            task = asyncio.wait_for(
                self.extract_point_data(dataset, lat, lon, date_str),
                timeout=5.0  # 5 second timeout per dataset
            )
            tasks.append((dataset, task))
        
        # Wait for all extractions to complete with individual timeouts
        results = []
        for dataset, task in tasks:
            try:
                result = await task
                results.append((dataset, result))
                logger.info(f"✅ Successfully extracted data for {dataset}")
            except asyncio.TimeoutError:
                logger.warning(f"⏰ Timeout extracting data for {dataset}")
                results.append((dataset, Exception(f"Timeout extracting {dataset} data")))
            except Exception as e:
                logger.error(f"❌ Error extracting data for {dataset}: {e}")
                results.append((dataset, e))
        
        # Process results
        dataset_data = {}
        for dataset, result in results:
            if isinstance(result, Exception):
                logger.error(f"Error extracting data for {dataset}: {result}")
                # Create error response
                dataset_data[dataset] = {
                    "error": str(result),
                    "dataset": dataset
                }
            else:
                dataset_data[dataset] = result
        
        total_time = (time.time() - start_time) * 1000
        
        # Use date from first successful extraction, or provided date
        response_date = date_str or "unknown"
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
        """Handle acidity data fallback by trying available acidity datasets."""
        from datetime import datetime
        
        logger.info(f"🔄 Handling acidity fallback for {requested_dataset}, date: {date_str}")
        
        # Define fallback strategy based on date and dataset
        fallback_order = []
        
        if date_str:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d")
                year = target_date.year
                
                # Smart fallback based on temporal coverage
                if year <= 2021:
                    # Historical period: prefer historical data, then current
                    fallback_order = ["acidity_historical", "acidity_current"]
                else:
                    # Current period: prefer current data, then historical
                    fallback_order = ["acidity_current", "acidity_historical"]
            except:
                # Invalid date format, try all options
                fallback_order = ["acidity_current", "acidity_historical"]
        else:
            # No date specified, try current first then historical
            fallback_order = ["acidity_current", "acidity_historical"]
        
        # Remove the originally requested dataset to avoid infinite recursion
        fallback_order = [ds for ds in fallback_order if ds != requested_dataset]
        
        # Try each fallback dataset
        for fallback_dataset in fallback_order:
            try:
                logger.info(f"🧪 Trying fallback dataset: {fallback_dataset}")
                
                # Check if the fallback dataset has data
                file_path = await self._find_dataset_file(fallback_dataset, date_str)
                if file_path:
                    logger.info(f"✅ Found data in {fallback_dataset}, extracting...")
                    
                    # Extract data using the fallback dataset
                    try:
                        result = await self._extract_point_data_optimized(fallback_dataset, file_path, lat, lon, date_str or "latest")
                        
                        # Add metadata about fallback
                        if result.data:
                            result.data["_fallback_info"] = DataValue(
                                value=f"Data from {fallback_dataset} (fallback from {requested_dataset})",
                                units="metadata",
                                long_name="Data Source Fallback Information",
                                valid=True
                            )
                            result.data["_original_request"] = DataValue(
                                value=requested_dataset,
                                units="metadata", 
                                long_name="Originally Requested Dataset",
                                valid=True
                            )
                        
                        logger.info(f"🎯 Successfully extracted acidity data using fallback: {fallback_dataset}")
                        return result
                        
                    except Exception as e:
                        logger.warning(f"Failed to extract from fallback {fallback_dataset}: {e}")
                        continue
                        
            except Exception as e:
                logger.warning(f"Error checking fallback dataset {fallback_dataset}: {e}")
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