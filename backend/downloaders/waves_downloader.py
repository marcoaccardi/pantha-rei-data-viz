#!/usr/bin/env python3
"""
Waves downloader for CMEMS Global Ocean Waves data.
Downloads daily NetCDF files from Copernicus Marine Environment Monitoring Service.
"""

import requests
import numpy as np
import xarray as xr
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
import tempfile
import shutil
import subprocess
import json
import warnings

from .base_downloader import BaseDataDownloader

class WavesDownloader(BaseDataDownloader):
    """Downloads and processes CMEMS Global Ocean Waves data."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize Waves downloader."""
        super().__init__("waves", config_path)
        
        # Waves-specific configuration
        self.product_id = self.dataset_config["product_id"]
        self.dataset_id = self.dataset_config["dataset_id"]
        self.base_url = self.dataset_config["base_url"]
        self.spatial_resolution = self.dataset_config["spatial_resolution"]
        self.variables = self.dataset_config["variables"]
        
        # Processing configuration
        self.needs_coord_harmonization = self.dataset_config["processing"]["harmonize_coords"]
        
        # Create processed data directories if needed
        if self.needs_coord_harmonization:
            self.harmonized_path = self.processed_data_path / "unified_coords" / "waves"
            self.harmonized_path.mkdir(parents=True, exist_ok=True)
        
        # Validate CMEMS credentials
        if not self.credentials.get("CMEMS_USERNAME") or not self.credentials.get("CMEMS_PASSWORD"):
            raise ValueError("CMEMS credentials not found. Please configure CMEMS_USERNAME and CMEMS_PASSWORD in .env file")
        
        # Dataset validity monitoring - operational forecast product
        
        self.logger.info(f"Initialized CMEMS Waves downloader with credentials for user: {self.credentials['CMEMS_USERNAME']}")
    
    def _check_dataset_validity(self) -> None:
        """Check dataset validity and warn about upcoming expiration."""
        now = datetime.now()
        days_until_expiry = (self.dataset_expiry_date - now).days
        
        if days_until_expiry < 0:
            self.logger.error(f"❌ Dataset {self.product_id} has expired! Expiry date: {self.dataset_expiry_date.date()}")
            self.logger.error("🔍 Check CMEMS for replacement datasets or contact support")
            warnings.warn(f"CMEMS dataset {self.product_id} has expired", UserWarning)
        elif days_until_expiry <= 30:
            self.logger.warning(f"⚠️  Dataset {self.product_id} expires in {days_until_expiry} days!")
            self.logger.warning(f"📅 Expiry date: {self.dataset_expiry_date.date()}")
            self.logger.warning("🔍 Check for replacement dataset at: https://marine.copernicus.eu/user-corner/product-roadmap")
        elif days_until_expiry <= 90:
            self.logger.info(f"📋 Dataset {self.product_id} expires in {days_until_expiry} days ({self.dataset_expiry_date.date()})")
    
    def get_dataset_status(self) -> Dict[str, Any]:
        """Get current dataset validity status."""
        now = datetime.now()
        days_until_expiry = (self.dataset_expiry_date - now).days
        
        status = {
            "dataset_id": self.product_id,
            "expiry_date": self.dataset_expiry_date.isoformat(),
            "days_until_expiry": days_until_expiry,
            "is_expired": days_until_expiry < 0,
            "needs_attention": days_until_expiry <= 90,
            "critical": days_until_expiry <= 30,
            "alternatives": {
                "reanalysis": "GLOBAL_MULTIYEAR_WAV_001_032",
                "roadmap_url": "https://marine.copernicus.eu/user-corner/product-roadmap"
            }
        }
        
        if days_until_expiry < 0:
            status["status"] = "expired"
        elif days_until_expiry <= 30:
            status["status"] = "critical"
        elif days_until_expiry <= 90:
            status["status"] = "warning"
        else:
            status["status"] = "healthy"
            
        return status

    def _get_filename_for_date(self, target_date: date) -> str:
        """Get filename for CMEMS waves file for given date."""
        return f"waves_global_{target_date.strftime('%Y%m%d')}.nc"
    
    def _get_cmems_download_command(self, target_date: date, output_file: Path) -> list:
        """
        Generate copernicusmarine command for downloading waves data.
        
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
            "--variable", "VHM0",  # Significant wave height
            "--variable", "VMDR",  # Mean wave direction  
            "--variable", "VTPK",  # Peak wave period
            "--start-datetime", f"{date_str}T00:00:00",
            "--end-datetime", f"{date_str}T23:59:59",
            "--output-filename", str(output_file),
            "--force-download"
        ]
        
        return command
    
    def download_date(self, target_date: date) -> bool:
        """
        Download waves data for a specific date using copernicusmarine CLI.
        
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
            self.logger.info(f"Downloading CMEMS waves data for {target_date}")
            
            # Set up environment variables for copernicusmarine
            env = {
                "COPERNICUSMARINE_SERVICE_USERNAME": self.credentials["CMEMS_USERNAME"],
                "COPERNICUSMARINE_SERVICE_PASSWORD": self.credentials["CMEMS_PASSWORD"]
            }
            
            # Create temporary file for download
            with tempfile.NamedTemporaryFile(delete=False, suffix='.nc') as temp_file:
                temp_path = Path(temp_file.name)
            
            # Generate download command
            command = self._get_cmems_download_command(target_date, temp_path)
            
            # Execute copernicusmarine command
            self.logger.info(f"Executing: {' '.join(command[:8])}...")  # Log partial command for security
            
            result = subprocess.run(
                command,
                env={**subprocess.os.environ, **env},
                capture_output=True,
                text=True,
                timeout=self.download_config["timeout_seconds"]
            )
            
            if result.returncode != 0:
                self.logger.error(f"CMEMS download failed: {result.stderr}")
                if temp_path.exists():
                    temp_path.unlink()
                return False
            
            # Validate downloaded file
            if not temp_path.exists() or not self._validate_netcdf_file(temp_path):
                self.logger.error(f"Downloaded file is invalid or missing: {temp_path}")
                if temp_path.exists():
                    temp_path.unlink()
                return False
            
            # Move to final location
            shutil.move(str(temp_path), str(raw_file_path))
            
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
        """Validate that NetCDF file is readable and contains expected wave data."""
        try:
            with xr.open_dataset(file_path) as ds:
                # Check for required variables
                required_vars = ['VHM0']  # At minimum, significant wave height
                for var in required_vars:
                    if var not in ds.data_vars:
                        self.logger.error(f"Missing required variable '{var}' in {file_path}")
                        return False
                
                # Check dimensions
                if 'latitude' not in ds.dims or 'longitude' not in ds.dims:
                    self.logger.error(f"Missing required dimensions in {file_path}")
                    return False
                
                # Check coordinate ranges (global coverage expected)
                lat_range = float(ds.latitude.max()) - float(ds.latitude.min())
                lon_range = float(ds.longitude.max()) - float(ds.longitude.min())
                
                if lat_range < 120:  # Should cover most of globe
                    self.logger.warning(f"Limited latitude coverage: {lat_range}°")
                
                if lon_range < 300:  # Should cover most of globe
                    self.logger.warning(f"Limited longitude coverage: {lon_range}°")
                
                # Check data values are reasonable for wave heights
                vhm0_data = ds['VHM0']
                if vhm0_data.size > 0:
                    max_wave_height = float(vhm0_data.max())
                    if max_wave_height > 20.0:  # Unreasonably high wave
                        self.logger.warning(f"Suspiciously high wave height: {max_wave_height}m")
                    elif max_wave_height < 0.1:  # Unreasonably low max wave
                        self.logger.warning(f"Suspiciously low maximum wave height: {max_wave_height}m")
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error validating NetCDF file {file_path}: {e}")
            return False
    
    def _process_downloaded_file(self, raw_file_path: Path, target_date: date) -> bool:
        """
        Process downloaded waves file (coordinate harmonization if needed).
        
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
                
                # Step 1: Harmonize coordinates if needed (waves should already be -180-180)
                if self.needs_coord_harmonization:
                    self.logger.info("Checking coordinate system")
                    processed_ds = self._harmonize_coordinates(processed_ds)
                    
                    # Save harmonized version if coordinates were changed
                    if not self._coordinates_already_harmonized(ds):
                        year_month = target_date.strftime("%Y/%m")
                        harmonized_dir = self.harmonized_path / year_month
                        harmonized_dir.mkdir(parents=True, exist_ok=True)
                        
                        harmonized_filename = f"waves_harmonized_{target_date.strftime('%Y%m%d')}.nc"
                        harmonized_file_path = harmonized_dir / harmonized_filename
                        
                        processed_ds.to_netcdf(harmonized_file_path, format='NETCDF4', engine='netcdf4')
                        self.logger.info(f"Saved harmonized file: {harmonized_file_path}")
                        
                        # Set harmonized as final file
                        final_file_path = harmonized_file_path
                        intermediate_files.append(raw_file_path)
                
                # Auto-optimize storage by removing raw and intermediate files
                optimization_result = self._auto_optimize_storage(
                    target_date=target_date,
                    raw_file_path=raw_file_path,
                    intermediate_files=intermediate_files,
                    final_file_path=final_file_path
                )
                
                # Log API data sample for development
                api_sample = self._log_api_data_sample(target_date, final_file_path)
                
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
    
    def get_date_coverage(self) -> dict:
        """Get information about date coverage for downloaded waves data."""
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
                # Extract date from filename: waves_global_YYYYMMDD.nc
                filename = file_path.name
                if filename.startswith("waves_global_") and filename.endswith(".nc"):
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
        """Validate all downloaded waves data."""
        base_validation = super().validate_downloaded_data()
        
        # Add waves-specific validation
        waves_validation = {
            "date_coverage": self.get_date_coverage(),
            "processing_status": {
                "harmonized_files": 0
            },
            "data_quality": {
                "avg_wave_height": None,
                "max_wave_height": None,
                "valid_data_percentage": None
            }
        }
        
        # Check processed files
        if self.needs_coord_harmonization and self.harmonized_path.exists():
            harmonized_files = list(self.harmonized_path.rglob("*.nc"))
            waves_validation["processing_status"]["harmonized_files"] = len(harmonized_files)
        
        # Analyze data quality from a sample file
        nc_files = list(self.raw_data_path.rglob("*.nc"))
        if nc_files:
            try:
                with xr.open_dataset(nc_files[0]) as ds:
                    if 'VHM0' in ds.data_vars:
                        wave_data = ds['VHM0']
                        valid_data = wave_data.where(~np.isnan(wave_data))
                        
                        waves_validation["data_quality"] = {
                            "avg_wave_height": float(valid_data.mean()),
                            "max_wave_height": float(valid_data.max()),
                            "valid_data_percentage": float((~np.isnan(wave_data)).sum() / wave_data.size * 100)
                        }
            except Exception as e:
                waves_validation["data_quality"]["error"] = str(e)
        
        # Combine validations
        combined_validation = {**base_validation, **waves_validation}
        
        return combined_validation