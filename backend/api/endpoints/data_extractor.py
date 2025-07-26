"""
Data extraction engine for Ocean Data Management API.

Handles reading NetCDF files and extracting point data with high performance.
Supports all datasets: SST, waves, currents, and acidity.
"""

import xarray as xr
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import time
import logging
from datetime import datetime, date
import asyncio
from concurrent.futures import ThreadPoolExecutor

from api.models.responses import (
    DatasetInfo, PointDataResponse, MultiDatasetResponse, 
    Coordinates, DataValue
)

logger = logging.getLogger(__name__)

class DataExtractor:
    """High-performance data extraction engine."""
    
    def __init__(self):
        """Initialize the data extractor."""
        self.data_path = Path("/Volumes/Backup/panta-rhei-data-map/ocean-data/processed/unified_coords")
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Dataset configuration
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
                "variables": ["VHM0", "VMDR", "VTPK"],
                "file_pattern": "waves_processed_*.nc", 
                "spatial_resolution": "0.083° (1/12 degree)"
            },
            "currents": {
                "name": "Ocean Currents",
                "description": "CMEMS Global Ocean Currents Analysis and Forecast",
                "variables": ["uo", "vo", "speed", "direction"],
                "file_pattern": "currents_harmonized_*.nc",
                "spatial_resolution": "0.083° (1/12 degree)"
            },
            "acidity": {
                "name": "Ocean Biogeochemistry",
                "description": "CMEMS Global Ocean Biogeochemistry Analysis and Forecast",
                "variables": ["ph", "dissic"],
                "file_pattern": "acidity_harmonized_*.nc",
                "spatial_resolution": "0.25° degree"
            },
            "microplastics": {
                "name": "Marine Microplastics",
                "description": "NOAA microplastics data (1993-2019) combined with GAN-generated synthetic data (2019-2025)",
                "variables": ["microplastics_concentration", "confidence", "data_source"],
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
        """Extract data at a specific point from the specified dataset."""
        if dataset not in self.dataset_config:
            raise ValueError(f"Unknown dataset: {dataset}")
        
        # Find the appropriate file
        file_path = await self._find_dataset_file(dataset, date_str)
        if not file_path:
            raise ValueError(f"No data file found for dataset {dataset}" + (f" and date {date_str}" if date_str else ""))
        
        # Extract data in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, 
            self._extract_point_data_sync, 
            dataset, file_path, lat, lon
        )

    def _extract_point_data_sync(self, dataset: str, file_path: Path, lat: float, lon: float) -> PointDataResponse:
        """Synchronous point data extraction."""
        start_time = time.time()
        
        try:
            # Special handling for microplastics point data
            if dataset == "microplastics":
                return self._extract_microplastics_point_data(file_path, lat, lon, start_time)
            
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
                
                # Build response data
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
            # Return the most recent file
            files_with_dates = []
            for f in files:
                file_date = self._extract_date_from_filename(f.name)
                if file_date:
                    files_with_dates.append((file_date, f))
            
            if files_with_dates:
                files_with_dates.sort(key=lambda x: x[0], reverse=True)
                return files_with_dates[0][1]
            else:
                return files[0]  # Fallback to first file
        
        else:
            # Find file matching the date
            for f in files:
                file_date = self._extract_date_from_filename(f.name)
                if file_date == date_str:
                    return f
            return None

    async def extract_multi_point_data(self, datasets: List[str], lat: float, lon: float, date_str: Optional[str] = None) -> MultiDatasetResponse:
        """Extract data from multiple datasets at a single point."""
        start_time = time.time()
        
        # Validate datasets
        invalid_datasets = [d for d in datasets if d not in self.dataset_config]
        if invalid_datasets:
            raise ValueError(f"Unknown datasets: {invalid_datasets}")
        
        # Extract data from each dataset concurrently
        tasks = []
        for dataset in datasets:
            task = self.extract_point_data(dataset, lat, lon, date_str)
            tasks.append(task)
        
        # Wait for all extractions to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        dataset_data = {}
        for dataset, result in zip(datasets, results):
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