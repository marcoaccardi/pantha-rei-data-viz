#!/usr/bin/env python3
"""
Currents downloader for CMEMS Global Ocean Currents data.
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

class CurrentsDownloader(BaseDataDownloader):
    """Downloads and processes CMEMS Global Ocean Currents data."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize Currents downloader."""
        super().__init__("currents", config_path)
        
        # Currents-specific configuration
        self.product_id = self.dataset_config["product_id"]
        self.dataset_id = self.dataset_config["dataset_id"]
        self.base_url = self.dataset_config["base_url"]
        self.spatial_resolution = self.dataset_config["spatial_resolution"]
        self.variables = self.dataset_config["variables"]
        self.layers = self.dataset_config.get("layers", ["surface"])
        
        # Processing configuration
        self.needs_coord_harmonization = self.dataset_config["processing"]["harmonize_coords"]
        
        # Always create harmonized path for consistency, even if coordinates don't need conversion
        self.harmonized_path = self.processed_data_path / "unified_coords" / "currents"
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
        
        self.logger.info(f"Initialized CMEMS Currents downloader with credentials for user: {self.cmems_username}")
    
    def _get_filename_for_date(self, target_date: date) -> str:
        """Get filename for CMEMS currents file for given date."""
        return f"currents_global_{target_date.strftime('%Y%m%d')}.nc"
    
    def _get_cmems_download_command(self, target_date: date, output_file: Path) -> list:
        """
        Generate copernicusmarine command for downloading currents data.
        
        Args:
            target_date: Date to download data for
            output_file: Path where to save the downloaded file
            
        Returns:
            Command list for subprocess
        """
        # Format date for CMEMS API
        date_str = target_date.strftime("%Y-%m-%d")
        
        command = [
            "copernicusmarine", "subset",
            "--dataset-id", self.dataset_id,
            "--variable", "uo",  # Zonal (eastward) velocity
            "--variable", "vo",  # Meridional (northward) velocity
            "--start-datetime", f"{date_str}T00:00:00",
            "--end-datetime", f"{date_str}T23:59:59",
            "--output-filename", str(output_file),
            "--force-download"
        ]
        
        # Add depth constraint for surface layer only (Phase 1)
        if "surface" in self.layers:
            command.extend(["--minimum-depth", "0", "--maximum-depth", "5"])
        
        return command
    
    def download_date(self, target_date: date) -> bool:
        """
        Download currents data for a specific date using copernicusmarine CLI.
        
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
            self.logger.info(f"Downloading CMEMS currents data for {target_date}")
            
            # Use temporary file during download
            with tempfile.NamedTemporaryFile(suffix='.nc', delete=False) as temp_file:
                temp_path = Path(temp_file.name)
            
            try:
                # Format date for CMEMS API
                date_str = target_date.strftime("%Y-%m-%d")
                
                self.logger.info(f"Using Python API to download currents data for {date_str}")
                
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
                    variables=["uo", "vo"],  # Zonal and meridional velocities
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
                self.logger.info(f"Successfully downloaded: {raw_file_path}")
                
                # Process the file (harmonize coordinates if needed)
                processed_file = self._process_file(raw_file_path, target_date)
                if processed_file:
                    # Generate API sample data for development
                    self._generate_api_sample(processed_file, target_date)
                    
                    # Auto-optimize storage
                    self._auto_optimize_storage(raw_file_path, processed_file, target_date)
                
                # Update status
                self.update_status(
                    last_date=target_date.strftime("%Y-%m-%d"),
                    last_success=self._get_current_timestamp(),
                    status="success"
                )
                
                return True
                
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
        Validate NetCDF file structure and content for currents data.
        
        Args:
            file_path: Path to NetCDF file to validate
            
        Returns:
            True if file is valid, False otherwise
        """
        try:
            with xr.open_dataset(file_path) as ds:
                # Check for required variables
                required_vars = ["uo", "vo"]  # Zonal and meridional velocities
                missing_vars = [var for var in required_vars if var not in ds.variables]
                if missing_vars:
                    self.logger.error(f"Missing required variables: {missing_vars}")
                    return False
                
                # Check for required dimensions
                required_dims = ["longitude", "latitude", "time"]
                missing_dims = [dim for dim in required_dims if dim not in ds.dims]
                if missing_dims:
                    self.logger.error(f"Missing required dimensions: {missing_dims}")
                    return False
                
                # Check data ranges (velocities typically -5 to +5 m/s)
                for var in ["uo", "vo"]:
                    if var in ds.variables:
                        data = ds[var].values
                        valid_data = data[~np.isnan(data)]
                        if len(valid_data) > 0:
                            if np.any(np.abs(valid_data) > 10):  # Allow up to 10 m/s for extreme currents
                                self.logger.warning(f"Unusually high {var} values detected (max: {np.max(np.abs(valid_data)):.2f} m/s)")
                
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
    
    def _process_file(self, raw_file_path: Path, target_date: date) -> Optional[Path]:
        """
        Process downloaded currents file - coordinate harmonization if needed.
        
        Args:
            raw_file_path: Path to raw downloaded file
            target_date: Date of the data
            
        Returns:
            Path to processed file, or None if processing failed
        """
        try:
            # For CMEMS currents, coordinates should already be in -180-180° format
            # But we still process to ensure consistency and add metadata
            
            with xr.open_dataset(raw_file_path) as ds:
                # Check coordinate system
                if "longitude" in ds.coords:
                    lon_min, lon_max = float(ds.longitude.min()), float(ds.longitude.max())
                    
                    if lon_min >= -180 and lon_max <= 180:
                        self.logger.info("Coordinates already in -180-180° format (expected for CMEMS)")
                        # Still create harmonized version for consistency
                        processed_ds = ds.copy()
                    else:
                        self.logger.info("Converting coordinates from 0-360° to -180-180°")
                        # Convert coordinates if needed
                        processed_ds = ds.assign_coords(
                            longitude=((ds.longitude + 180) % 360) - 180
                        ).sortby('longitude')
                
                # Add processing metadata
                processed_ds.attrs.update({
                    'processing_date': self._get_current_timestamp(),
                    'processing_version': '1.1',
                    'coordinate_system': '-180_to_180_degrees',
                    'source_dataset': self.product_id,
                    'variables_included': ', '.join(self.variables),
                    'spatial_resolution_degrees': self.spatial_resolution,
                    'depth_layers': ', '.join(self.layers)
                })
                
                # Define output path
                year_month = target_date.strftime("%Y/%m")
                output_dir = self.harmonized_path / year_month
                output_dir.mkdir(parents=True, exist_ok=True)
                
                output_filename = f"currents_harmonized_{target_date.strftime('%Y%m%d')}.nc"
                output_path = output_dir / output_filename
                
                # Save processed file
                processed_ds.to_netcdf(output_path, engine='netcdf4')
                self.logger.info(f"Processed file saved: {output_path}")
                
                return output_path
                
        except Exception as e:
            self.logger.error(f"Error processing file {raw_file_path}: {e}")
            return None
    
    def _generate_api_sample(self, processed_file: Path, target_date: date):
        """
        Generate API sample data for development purposes.
        
        Args:
            processed_file: Path to processed NetCDF file
            target_date: Date of the data
        """
        try:
            with xr.open_dataset(processed_file) as ds:
                # Sample a few test points for API development
                test_points = [
                    {"lat": 0.0, "lon": 0.0, "name": "Equatorial Atlantic"},
                    {"lat": 25.0, "lon": -80.0, "name": "Gulf Stream"},
                    {"lat": -40.0, "lon": 20.0, "name": "Agulhas Current"}
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
                        
                        uo_val = float(ds.uo.isel(latitude=lat_idx, longitude=lon_idx, time=0).values)
                        vo_val = float(ds.vo.isel(latitude=lat_idx, longitude=lon_idx, time=0).values)
                        
                        # Calculate current speed and direction
                        speed = np.sqrt(uo_val**2 + vo_val**2)
                        direction = np.arctan2(vo_val, uo_val) * 180 / np.pi  # Degrees from east
                        
                        extraction_time = (time.time() - start_time) * 1000
                        
                        sample = {
                            "location": point["name"],
                            "requested_coordinates": {"lat": point["lat"], "lon": point["lon"]},
                            "actual_coordinates": {"lat": actual_lat, "lon": actual_lon},
                            "data": {
                                "uo": {
                                    "value": round(uo_val, 3) if not np.isnan(uo_val) else None,
                                    "units": "m/s",
                                    "long_name": "Zonal (eastward) current velocity",
                                    "valid": not np.isnan(uo_val)
                                },
                                "vo": {
                                    "value": round(vo_val, 3) if not np.isnan(vo_val) else None,
                                    "units": "m/s",
                                    "long_name": "Meridional (northward) current velocity",
                                    "valid": not np.isnan(vo_val)
                                },
                                "speed": {
                                    "value": round(float(speed), 3) if not np.isnan(speed) else None,
                                    "units": "m/s",
                                    "long_name": "Current speed",
                                    "valid": not np.isnan(speed)
                                },
                                "direction": {
                                    "value": round(float(direction), 1) if not np.isnan(direction) else None,
                                    "units": "degrees",
                                    "long_name": "Current direction (degrees from east)",
                                    "valid": not np.isnan(direction)
                                }
                            },
                            "extraction_time_ms": round(extraction_time, 2)
                        }
                        
                        samples.append(sample)
                        
                    except Exception as e:
                        self.logger.warning(f"Error sampling point {point}: {e}")
                
                # Save API sample file
                api_sample_dir = self.logs_path / "api_samples"
                api_sample_dir.mkdir(parents=True, exist_ok=True)
                
                sample_filename = f"currents_api_sample_{target_date.strftime('%Y%m%d')}.json"
                sample_file = api_sample_dir / sample_filename
                
                with open(sample_file, 'w') as f:
                    json.dump({
                        "dataset": "currents",
                        "date": target_date.strftime("%Y-%m-%d"),
                        "source": self.product_id,
                        "processing_timestamp": self._get_current_timestamp(),
                        "samples": samples
                    }, f, indent=2)
                
                self.logger.info(f"API sample data generated: {sample_file}")
                
        except Exception as e:
            self.logger.error(f"Error generating API sample: {e}")
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp as ISO format string."""
        return datetime.now().isoformat()
    
    def _auto_optimize_storage(self, raw_file_path: Path, processed_file: Path, target_date: date, keep_raw_files: bool = True):
        """
        Auto-optimize storage by removing raw files after successful processing.
        
        Args:
            raw_file_path: Path to raw downloaded file
            processed_file: Path to final processed file  
            target_date: Date of the data
            keep_raw_files: If True, preserve raw files for further processing
        """
        try:
            if processed_file.exists() and processed_file.stat().st_size > 0:
                # Remove raw file to save space (unless preservation is requested)
                if raw_file_path.exists() and not keep_raw_files:
                    raw_size_mb = raw_file_path.stat().st_size / (1024 * 1024)
                    raw_file_path.unlink()
                    self.logger.info(f"Auto-optimization: removed raw file, freed {raw_size_mb:.1f} MB")
                elif keep_raw_files and raw_file_path.exists():
                    self.logger.info(f"Preserving raw file for further processing: {raw_file_path}")
                
                # Clean up empty directories
                try:
                    raw_file_path.parent.rmdir()
                except OSError:
                    pass  # Directory not empty, that's fine
                    
        except Exception as e:
            self.logger.error(f"Error during storage optimization: {e}")