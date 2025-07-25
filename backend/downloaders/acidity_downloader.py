#!/usr/bin/env python3
"""
Acidity downloader for CMEMS Global Ocean Biogeochemistry data.
Downloads daily NetCDF files from Copernicus Marine Environment Monitoring Service.
"""

import requests
import numpy as np
import xarray as xr
from datetime import date, datetime
from pathlib import Path
from typing import Optional
import tempfile
import shutil
import subprocess
import json
import time
import copernicusmarine
import os

from .base_downloader import BaseDataDownloader

class AcidityDownloader(BaseDataDownloader):
    """Downloads and processes CMEMS Global Ocean Biogeochemistry (acidity) data."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize Acidity downloader."""
        super().__init__("acidity", config_path)
        
        # Acidity-specific configuration
        self.product_id = self.dataset_config["product_id"]
        self.dataset_id = self.dataset_config["dataset_id"]
        self.base_url = self.dataset_config["base_url"]
        self.spatial_resolution = self.dataset_config["spatial_resolution"]
        self.variables = self.dataset_config["variables"]
        self.layers = self.dataset_config.get("layers", ["surface"])
        
        # Processing configuration
        self.needs_coord_harmonization = self.dataset_config["processing"]["harmonize_coords"]
        
        # Create processed data directories if needed
        if self.needs_coord_harmonization:
            self.harmonized_path = self.processed_data_path / "unified_coords" / "acidity"
            self.harmonized_path.mkdir(parents=True, exist_ok=True)
        
        # Load credentials directly from .env file
        env_file = self.config_path / "credentials.env"
        self.cmems_username = None
        self.cmems_password = None
        
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        if key.strip() == 'CMEMS_USERNAME':
                            self.cmems_username = value.strip()
                        elif key.strip() == 'CMEMS_PASSWORD':
                            self.cmems_password = value.strip()
        
        # Also check environment variables as fallback
        if not self.cmems_username:
            self.cmems_username = os.getenv("CMEMS_USERNAME")
        if not self.cmems_password:
            self.cmems_password = os.getenv("CMEMS_PASSWORD")
        
        # Validate CMEMS credentials
        if not self.cmems_username or not self.cmems_password:
            raise ValueError("CMEMS credentials not found. Please configure CMEMS_USERNAME and CMEMS_PASSWORD in credentials.env file")
        
        self.logger.info(f"Initialized CMEMS Acidity downloader with credentials for user: {self.cmems_username}")
    
    def _get_filename_for_date(self, target_date: date) -> str:
        """Get filename for CMEMS acidity file for given date."""
        return f"acidity_bgc_{target_date.strftime('%Y%m%d')}.nc"
    
    def download_date(self, target_date: date) -> bool:
        """
        Download acidity data for a specific date using copernicusmarine Python API.
        
        Args:
            target_date: Date to download data for
            
        Returns:
            True if successful, False otherwise
        """
        # Create year/month directory structure
        year_month = target_date.strftime("%Y/%m")
        output_dir = self.raw_data_path / year_month
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Define file paths
        filename = self._get_filename_for_date(target_date)
        raw_file_path = output_dir / filename
        
        # Skip if file already exists and is valid
        if raw_file_path.exists() and self._validate_netcdf_file(raw_file_path):
            self.logger.info(f"File already exists and is valid: {raw_file_path}")
            return True
        
        try:
            self.logger.info(f"Downloading CMEMS biogeochemistry data for {target_date}")
            
            # Use temporary file during download
            with tempfile.NamedTemporaryFile(suffix='.nc', delete=False) as temp_file:
                temp_path = Path(temp_file.name)
            
            try:
                # Format date for CMEMS API
                date_str = target_date.strftime("%Y-%m-%d")
                
                self.logger.info(f"Using Python API to download acidity data for {date_str}")
                
                # Login first, then use subset
                try:
                    self.logger.info("Authenticating with CMEMS...")
                    
                    # Remove existing credentials file to avoid confirmation prompt
                    import pathlib
                    creds_file = pathlib.Path.home() / ".copernicusmarine" / ".copernicusmarine-credentials"
                    if creds_file.exists():
                        creds_file.unlink()
                    
                    copernicusmarine.login(
                        username=self.cmems_username,
                        password=self.cmems_password
                    )
                    self.logger.info("CMEMS authentication successful")
                except Exception as auth_error:
                    self.logger.error(f"CMEMS authentication failed: {auth_error}")
                    raise
                
                # Use copernicusmarine Python API
                self.logger.info(f"Requesting subset for dataset: {self.dataset_id}")
                copernicusmarine.subset(
                    dataset_id=self.dataset_id,
                    variables=["ph", "dissic"],  # pH and dissolved inorganic carbon
                    start_datetime=f"{date_str}T00:00:00",
                    end_datetime=f"{date_str}T23:59:59",
                    minimum_depth=0,
                    maximum_depth=5,  # Surface layer only
                    output_filename=str(temp_path)
                )
                
                # Check for downloaded file - CMEMS may add suffix
                actual_file = None
                
                # First try the original path
                if temp_path.exists() and temp_path.stat().st_size > 0:
                    actual_file = temp_path
                else:
                    # Check for variations with suffix (e.g., filename_(1).nc)
                    temp_dir = temp_path.parent
                    base_name = temp_path.stem
                    suffix = temp_path.suffix
                    
                    # Look for files with pattern: basename_(number).nc
                    for i in range(1, 10):
                        alt_file = temp_dir / f"{base_name}_({i}){suffix}"
                        if alt_file.exists() and alt_file.stat().st_size > 0:
                            actual_file = alt_file
                            self.logger.info(f"Found alternative file: {actual_file}")
                            break
                
                if actual_file is None:
                    self.logger.error(f"No valid downloaded file found (checked {temp_path} and alternatives)")
                    return False
                
                # Validate NetCDF structure
                if not self._validate_netcdf_file(actual_file):
                    self.logger.error(f"Downloaded file failed validation: {actual_file}")
                    return False
                
                # Move to final location
                shutil.move(str(actual_file), str(raw_file_path))
                
                # Get file size for logging
                file_size_mb = raw_file_path.stat().st_size / (1024 * 1024)
                self.logger.info(f"Successfully downloaded {filename} ({file_size_mb:.1f} MB)")
                
                # Process the downloaded file
                success = self._process_downloaded_file(raw_file_path, target_date)
                
                if success:
                    # Update file count and storage stats
                    current_status = self.get_status()
                    new_file_count = current_status.get("total_files", 0) + 1
                    new_storage_gb = self.get_storage_usage()
                    
                    self.update_status(
                        total_files=new_file_count,
                        storage_gb=round(new_storage_gb, 3)
                    )
                
                return success
                
            finally:
                # Clean up temporary files if they still exist
                if temp_path.exists():
                    temp_path.unlink()
                # Also clean up any alternative files that might exist
                temp_dir = temp_path.parent
                base_name = temp_path.stem
                suffix = temp_path.suffix
                for i in range(1, 10):
                    alt_file = temp_dir / f"{base_name}_({i}){suffix}"
                    if alt_file.exists():
                        alt_file.unlink()
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"Download timeout for {filename}")
            return False
        except subprocess.CalledProcessError as e:
            self.logger.error(f"CMEMS command error downloading {filename}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error downloading {filename}: {e}")
            return False
    
    def _validate_netcdf_file(self, file_path: Path) -> bool:
        """
        Validate NetCDF file structure and content for biogeochemistry data.
        
        Args:
            file_path: Path to NetCDF file to validate
            
        Returns:
            True if file is valid, False otherwise
        """
        try:
            with xr.open_dataset(file_path) as ds:
                # Check for required variables (at least pH or DIC)
                required_vars = ["ph", "dissic"]
                available_vars = [var for var in required_vars if var in ds.variables]
                if not available_vars:
                    self.logger.error(f"Missing all biogeochemistry variables: {required_vars}")
                    return False
                
                # Check for required dimensions
                required_dims = ["longitude", "latitude", "time"]
                missing_dims = [dim for dim in required_dims if dim not in ds.dims]
                if missing_dims:
                    self.logger.error(f"Missing required dimensions: {missing_dims}")
                    return False
                
                # Validate pH ranges (typical ocean pH: 7.5-8.5)
                if "ph" in ds.variables:
                    ph_data = ds["ph"].values
                    valid_ph = ph_data[~np.isnan(ph_data)]
                    if len(valid_ph) > 0:
                        min_ph, max_ph = float(np.min(valid_ph)), float(np.max(valid_ph))
                        if min_ph < 6.0 or max_ph > 10.0:
                            self.logger.warning(f"pH values outside expected range: {min_ph:.2f} - {max_ph:.2f}")
                        if min_ph < 7.0 or max_ph > 9.0:
                            self.logger.warning(f"pH values at extreme ends: {min_ph:.2f} - {max_ph:.2f}")
                
                # Validate DIC ranges (typical ocean DIC: 1.8-2.4 mol/m³)
                if "dissic" in ds.variables:
                    dissic_data = ds["dissic"].values
                    valid_dissic = dissic_data[~np.isnan(dissic_data)]
                    if len(valid_dissic) > 0:
                        min_dissic, max_dissic = float(np.min(valid_dissic)), float(np.max(valid_dissic))
                        if min_dissic < 1.0 or max_dissic > 3.0:
                            self.logger.warning(f"DIC values outside expected range: {min_dissic:.3f} - {max_dissic:.3f} mol/m³")
                
                # Check spatial coverage
                if "longitude" in ds.coords and "latitude" in ds.coords:
                    lon_range = (float(ds.longitude.min()), float(ds.longitude.max()))
                    lat_range = (float(ds.latitude.min()), float(ds.latitude.max()))
                    
                    # Expect global coverage (approximately)
                    if lon_range[1] - lon_range[0] < 300:  # Should span most longitudes
                        self.logger.warning(f"Limited longitude coverage: {lon_range}")
                    if lat_range[1] - lat_range[0] < 120:  # Should span most latitudes
                        self.logger.warning(f"Limited latitude coverage: {lat_range}")
                
                return True
                
        except Exception as e:
            self.logger.error(f"NetCDF validation error: {e}")
            return False
    
    def _process_downloaded_file(self, raw_file_path: Path, target_date: date) -> bool:
        """
        Process downloaded acidity file (coordinate harmonization if needed).
        
        Args:
            raw_file_path: Path to raw downloaded file
            target_date: Date of the data
            
        Returns:
            True if processing successful
        """
        try:
            # Load the dataset
            with xr.open_dataset(raw_file_path) as ds:
                processed_ds = ds.copy()
                intermediate_files = []
                final_file_path = raw_file_path  # Default to raw file
                
                # Step 1: Harmonize coordinates if needed (should already be -180-180 for CMEMS)
                if self.needs_coord_harmonization:
                    self.logger.info("Checking coordinate system")
                    processed_ds = self._harmonize_coordinates(processed_ds)
                    
                    # Save harmonized version if coordinates were changed
                    if not self._coordinates_already_harmonized(ds):
                        year_month = target_date.strftime("%Y/%m")
                        harmonized_dir = self.harmonized_path / year_month
                        harmonized_dir.mkdir(parents=True, exist_ok=True)
                        
                        harmonized_filename = f"acidity_harmonized_{target_date.strftime('%Y%m%d')}.nc"
                        harmonized_file_path = harmonized_dir / harmonized_filename
                        
                        processed_ds.to_netcdf(harmonized_file_path, format='NETCDF4', engine='netcdf4')
                        self.logger.info(f"Saved harmonized file: {harmonized_file_path}")
                        
                        # Set harmonized as final file
                        final_file_path = harmonized_file_path
                        intermediate_files.append(raw_file_path)
                
                # Log API data sample for development BEFORE optimization
                api_sample = self._log_api_data_sample(target_date, final_file_path)
                
                # Auto-optimize storage by removing raw and intermediate files
                optimization_result = self._auto_optimize_storage(
                    target_date=target_date,
                    raw_file_path=raw_file_path,
                    intermediate_files=intermediate_files,
                    final_file_path=final_file_path
                )
                
                # Update status with optimization results
                self.update_status(
                    last_optimization=optimization_result["timestamp"],
                    space_freed_mb=optimization_result["space_freed_mb"],
                    final_file_size_kb=optimization_result["final_file_size_kb"],
                    api_ready=api_sample.get("api_readiness", {}).get("ready_for_api", False)
                )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing file {raw_file_path}: {e}")
            return False
    
    def _coordinates_already_harmonized(self, ds: xr.Dataset) -> bool:
        """Check if coordinates are already in -180-180 format."""
        lon_coord = 'longitude' if 'longitude' in ds.dims else 'lon'
        lon_min, lon_max = float(ds[lon_coord].min()), float(ds[lon_coord].max())
        return lon_min >= -180 and lon_max <= 180
    
    def _harmonize_coordinates(self, ds: xr.Dataset) -> xr.Dataset:
        """
        Convert longitude coordinates from 0-360° to -180-180° if needed.
        CMEMS data should already be in -180-180° format.
        
        Args:
            ds: Input xarray Dataset
            
        Returns:
            Dataset with harmonized coordinates
        """
        # Determine longitude coordinate name
        lon_coord = 'longitude' if 'longitude' in ds.dims else 'lon'
        
        # Check if conversion is needed
        lon_min, lon_max = float(ds[lon_coord].min()), float(ds[lon_coord].max())
        
        if lon_min >= 0 and lon_max > 180:
            # Need to convert from 0-360 to -180-180
            ds = ds.assign_coords({lon_coord: (ds[lon_coord] + 180) % 360 - 180})
            ds = ds.sortby(lon_coord)
            
            # Add processing note
            ds.attrs.update({
                'coordinate_processing': 'Converted longitude from 0-360° to -180-180°',
                'coordinate_processing_date': str(date.today())
            })
            
            self.logger.info("Converted longitude coordinates from 0-360° to -180-180°")
        else:
            self.logger.info("Coordinates already in -180-180° format (expected for CMEMS)")
        
        return ds
    
    def _log_api_data_sample(self, target_date: date, processed_file: Path) -> dict:
        """
        Generate and log API sample data for development purposes.
        
        Args:
            target_date: Date of the data
            processed_file: Path to processed NetCDF file
            
        Returns:
            Dict with API sample metadata
        """
        try:
            with xr.open_dataset(processed_file) as ds:
                # Sample test points for biogeochemistry data
                test_points = [
                    {"lat": 0.0, "lon": 0.0, "name": "Equatorial Pacific"},
                    {"lat": 60.0, "lon": -30.0, "name": "North Atlantic"},
                    {"lat": -40.0, "lon": 140.0, "name": "Southern Ocean"}
                ]
                
                samples = []
                for point in test_points:
                    try:
                        # Find nearest grid point
                        lat_idx = np.argmin(np.abs(ds.latitude.values - point["lat"]))
                        lon_idx = np.argmin(np.abs(ds.longitude.values - point["lon"]))
                        
                        actual_lat = float(ds.latitude.values[lat_idx])
                        actual_lon = float(ds.longitude.values[lon_idx])
                        
                        # Extract data
                        start_time = time.time()
                        
                        sample_data = {}
                        
                        # pH data
                        if "ph" in ds.variables:
                            ph_data = ds.ph.isel(latitude=lat_idx, longitude=lon_idx)
                            # Handle time dimension
                            if 'time' in ph_data.dims:
                                ph_data = ph_data.isel(time=0)
                            # Handle depth dimension (take surface)
                            if 'depth' in ph_data.dims:
                                ph_data = ph_data.isel(depth=0)
                            # Extract scalar value
                            ph_val = float(ph_data.values.item() if ph_data.values.ndim == 0 else ph_data.values.flatten()[0])
                            sample_data["ph"] = {
                                "value": round(ph_val, 3) if not np.isnan(ph_val) else None,
                                "units": "pH units",
                                "long_name": "Sea water pH (total scale)",
                                "valid": not np.isnan(ph_val),
                                "typical_range": "7.5 - 8.5"
                            }
                        
                        # DIC data
                        if "dissic" in ds.variables:
                            dissic_data = ds.dissic.isel(latitude=lat_idx, longitude=lon_idx)
                            # Handle time dimension
                            if 'time' in dissic_data.dims:
                                dissic_data = dissic_data.isel(time=0)
                            # Handle depth dimension (take surface)
                            if 'depth' in dissic_data.dims:
                                dissic_data = dissic_data.isel(depth=0)
                            # Extract scalar value
                            dissic_val = float(dissic_data.values.item() if dissic_data.values.ndim == 0 else dissic_data.values.flatten()[0])
                            sample_data["dissic"] = {
                                "value": round(dissic_val, 3) if not np.isnan(dissic_val) else None,
                                "units": "mol/m³",
                                "long_name": "Dissolved inorganic carbon",
                                "valid": not np.isnan(dissic_val),
                                "typical_range": "1.8 - 2.4 mol/m³"
                            }
                        
                        extraction_time = (time.time() - start_time) * 1000
                        
                        sample = {
                            "location": point["name"],
                            "requested_coordinates": {"lat": point["lat"], "lon": point["lon"]},
                            "actual_coordinates": {"lat": actual_lat, "lon": actual_lon},
                            "data": sample_data,
                            "extraction_time_ms": round(extraction_time, 2)
                        }
                        
                        samples.append(sample)
                        
                    except Exception as e:
                        self.logger.warning(f"Error sampling point {point}: {e}")
                
                # Save API sample file
                api_sample_dir = self.logs_path / "api_samples"
                api_sample_dir.mkdir(parents=True, exist_ok=True)
                
                sample_filename = f"acidity_api_sample_{target_date.strftime('%Y%m%d')}.json"
                sample_file = api_sample_dir / sample_filename
                
                api_sample_data = {
                    "dataset": "acidity",
                    "date": target_date.strftime("%Y-%m-%d"),
                    "source": self.product_id,
                    "processing_timestamp": datetime.now().isoformat(),
                    "samples": samples,
                    "api_readiness": {
                        "ready_for_api": len(samples) > 0,
                        "average_extraction_time_ms": sum(s["extraction_time_ms"] for s in samples) / len(samples) if samples else 0,
                        "variables_available": list(samples[0]["data"].keys()) if samples else []
                    }
                }
                
                with open(sample_file, 'w') as f:
                    json.dump(api_sample_data, f, indent=2)
                
                self.logger.info(f"API sample data generated: {sample_file}")
                return api_sample_data
                
        except Exception as e:
            self.logger.error(f"Error generating API sample: {e}")
            return {"api_readiness": {"ready_for_api": False}}
    
    def get_date_coverage(self) -> dict:
        """Get information about date coverage for downloaded acidity data."""
        files = list(self.raw_data_path.rglob("*.nc"))
        
        if not files:
            return {
                "first_date": None,
                "last_date": None,
                "total_days": 0,
                "missing_days": []
            }
        
        # Extract dates from filenames
        dates = []
        for file_path in files:
            try:
                # Extract date from filename: acidity_bgc_YYYYMMDD.nc
                filename = file_path.name
                if filename.startswith("acidity_bgc_") and filename.endswith(".nc"):
                    date_str = filename.split("_")[2].split(".")[0]  # Extract YYYYMMDD
                    file_date = date.fromisoformat(f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}")
                    dates.append(file_date)
            except (ValueError, IndexError):
                continue
        
        if not dates:
            return {
                "first_date": None,
                "last_date": None,
                "total_days": 0,
                "missing_days": []
            }
        
        dates.sort()
        first_date = dates[0]
        last_date = dates[-1]
        
        # Find missing days
        expected_days = (last_date - first_date).days + 1
        missing_days = []
        
        current_date = first_date
        for i in range(expected_days):
            if current_date not in dates:
                missing_days.append(current_date.strftime("%Y-%m-%d"))
            current_date = current_date.replace(day=current_date.day + 1)
        
        return {
            "first_date": first_date.strftime("%Y-%m-%d"),
            "last_date": last_date.strftime("%Y-%m-%d"),
            "total_days": len(dates),
            "expected_days": expected_days,
            "missing_days": missing_days
        }
    
    def validate_downloaded_data(self) -> dict:
        """Validate all downloaded acidity data."""
        base_validation = super().validate_downloaded_data()
        
        # Add acidity-specific validation
        acidity_validation = {
            "date_coverage": self.get_date_coverage(),
            "processing_status": {
                "harmonized_files": 0
            },
            "data_quality": {
                "avg_ph": None,
                "avg_dissic": None,
                "valid_data_percentage": None
            }
        }
        
        # Check processed files
        if self.needs_coord_harmonization and self.harmonized_path.exists():
            harmonized_files = list(self.harmonized_path.rglob("*.nc"))
            acidity_validation["processing_status"]["harmonized_files"] = len(harmonized_files)
        
        # Analyze data quality from a sample file
        nc_files = list(self.raw_data_path.rglob("*.nc"))
        if nc_files:
            try:
                with xr.open_dataset(nc_files[0]) as ds:
                    quality_metrics = {}
                    
                    if 'ph' in ds.data_vars:
                        ph_data = ds['ph']
                        valid_ph = ph_data.where(~np.isnan(ph_data))
                        quality_metrics["avg_ph"] = float(valid_ph.mean())
                        quality_metrics["ph_range"] = [float(valid_ph.min()), float(valid_ph.max())]
                    
                    if 'dissic' in ds.data_vars:
                        dissic_data = ds['dissic']
                        valid_dissic = dissic_data.where(~np.isnan(dissic_data))
                        quality_metrics["avg_dissic"] = float(valid_dissic.mean())
                        quality_metrics["dissic_range"] = [float(valid_dissic.min()), float(valid_dissic.max())]
                    
                    acidity_validation["data_quality"].update(quality_metrics)
                    
            except Exception as e:
                acidity_validation["data_quality"]["error"] = str(e)
        
        # Combine validations
        combined_validation = {**base_validation, **acidity_validation}
        
        return combined_validation