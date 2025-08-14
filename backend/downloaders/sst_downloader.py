#!/usr/bin/env python3
"""
SST (Sea Surface Temperature) downloader for NOAA OISST v2.1 data.
Downloads daily NetCDF files and downsamples from 0.25° to 1° resolution.
"""

import requests
import numpy as np
import xarray as xr
from datetime import date
from pathlib import Path
from typing import Optional
import tempfile
import shutil

from .base_downloader import BaseDataDownloader

class SSTDownloader(BaseDataDownloader):
    """Downloads and processes NOAA OISST v2.1 sea surface temperature data."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize SST downloader."""
        super().__init__("sst", config_path)
        
        # SST-specific configuration
        self.base_url = self.dataset_config["base_url"]
        self.file_pattern = self.dataset_config["file_pattern"]
        self.url_pattern = self.dataset_config["url_pattern"]
        self.spatial_resolution = self.dataset_config["spatial_resolution"]
        self.target_resolution = self.dataset_config["target_resolution"]
        
        # Processing configuration
        self.needs_downsampling = self.dataset_config["processing"]["downsample"]
        self.needs_coord_harmonization = self.dataset_config["processing"]["harmonize_coords"]
        
        # Create processed data directories
        if self.needs_downsampling:
            self.downsampled_path = self.processed_data_path / "sst_downsampled"
            self.downsampled_path.mkdir(parents=True, exist_ok=True)
        
        if self.needs_coord_harmonization:
            self.harmonized_path = self.processed_data_path / "unified_coords" / "sst"
            self.harmonized_path.mkdir(parents=True, exist_ok=True)
    
    def _get_filename_for_date(self, target_date: date) -> str:
        """Get filename for NOAA OISST file for given date."""
        return f"oisst-avhrr-v02r01.{target_date.strftime('%Y%m%d')}.nc"
    
    def _get_download_url(self, target_date: date) -> str:
        """Get download URL for given date (final version)."""
        year_month = target_date.strftime("%Y%m")
        filename = self._get_filename_for_date(target_date)
        return f"{self.base_url}{year_month}/{filename}"
    
    def _get_preliminary_download_url(self, target_date: date) -> str:
        """Get download URL for preliminary version."""
        year_month = target_date.strftime("%Y%m")
        filename = self._get_preliminary_filename_for_date(target_date)
        return f"{self.base_url}{year_month}/{filename}"
    
    def _get_preliminary_filename_for_date(self, target_date: date) -> str:
        """Get preliminary filename for NOAA OISST file for given date."""
        return f"oisst-avhrr-v02r01.{target_date.strftime('%Y%m%d')}_preliminary.nc"
    
    def download_date(self, target_date: date) -> bool:
        """
        Download SST data for a specific date.
        
        Args:
            target_date: Date to download data for
            
        Returns:
            True if successful, False otherwise
        """
        # Try final version first, then preliminary version
        final_url = self._get_download_url(target_date)
        preliminary_url = self._get_preliminary_download_url(target_date)
        
        # Try final version first
        success = self._attempt_download(target_date, final_url, is_preliminary=False)
        if success:
            return True
            
        # If final version fails, try preliminary version
        self.logger.info(f"Final version not available, trying preliminary version for {target_date}")
        return self._attempt_download(target_date, preliminary_url, is_preliminary=True)
    
    def _attempt_download(self, target_date: date, url: str, is_preliminary: bool = False) -> bool:
        """Attempt to download SST data from given URL."""
        # Create year/month directory structure
        year_month = target_date.strftime("%Y/%m")
        output_dir = self.raw_data_path / year_month
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Define file paths (always save as final filename, regardless of source)
        filename = self._get_filename_for_date(target_date)
        raw_file_path = output_dir / filename
        
        # Skip if file already exists and is valid
        if raw_file_path.exists() and self._validate_netcdf_file(raw_file_path):
            self.logger.info(f"File already exists and is valid: {raw_file_path}")
            return True
        
        try:
            file_type = "preliminary" if is_preliminary else "final"
            self.logger.info(f"Downloading {file_type} version from: {url}")
            
            # Download with streaming to handle large files
            response = self.session.get(
                url,
                stream=True,
                timeout=self.download_config["timeout_seconds"]
            )
            response.raise_for_status()
            
            # Save to temporary file first
            with tempfile.NamedTemporaryFile(delete=False, suffix='.nc') as temp_file:
                temp_path = Path(temp_file.name)
                
                # Download in chunks
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        temp_file.write(chunk)
            
            # Validate downloaded file
            if not self._validate_netcdf_file(temp_path):
                self.logger.error(f"Downloaded file is invalid: {temp_path}")
                temp_path.unlink()
                return False
            
            # Move to final location
            shutil.move(str(temp_path), str(raw_file_path))
            
            # Get file size for logging
            file_size_mb = raw_file_path.stat().st_size / (1024 * 1024)
            version_note = " (preliminary version)" if is_preliminary else ""
            self.logger.info(f"Successfully downloaded {filename}{version_note} ({file_size_mb:.1f} MB)")
            
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
            
        except requests.exceptions.RequestException as e:
            if e.response and e.response.status_code == 404:
                self.logger.debug(f"File not available: {url}")
            else:
                self.logger.error(f"Network error downloading {filename}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error downloading {filename}: {e}")
            return False
    
    def _validate_netcdf_file(self, file_path: Path) -> bool:
        """Validate that NetCDF file is readable and contains expected data."""
        try:
            with xr.open_dataset(file_path) as ds:
                # Check for required variables
                required_vars = ['sst']  # Minimum required
                for var in required_vars:
                    if var not in ds.data_vars:
                        self.logger.error(f"Missing required variable '{var}' in {file_path}")
                        return False
                
                # Check dimensions
                if 'lat' not in ds.dims or 'lon' not in ds.dims:
                    self.logger.error(f"Missing required dimensions in {file_path}")
                    return False
                
                # Check data size (should be roughly 0.25 degree resolution)
                expected_lat_size = int(180 / self.spatial_resolution)  # ~720
                expected_lon_size = int(360 / self.spatial_resolution)  # ~1440
                
                if abs(len(ds.lat) - expected_lat_size) > 50:  # Allow some tolerance
                    self.logger.warning(f"Unexpected lat dimension size: {len(ds.lat)} (expected ~{expected_lat_size})")
                
                if abs(len(ds.lon) - expected_lon_size) > 50:  # Allow some tolerance
                    self.logger.warning(f"Unexpected lon dimension size: {len(ds.lon)} (expected ~{expected_lon_size})")
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error validating NetCDF file {file_path}: {e}")
            return False
    
    def _process_downloaded_file(self, raw_file_path: Path, target_date: date) -> bool:
        """
        Process downloaded SST file (downsample and harmonize coordinates).
        
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
                final_file_path = None
                
                # Step 1: Downsample if needed
                if self.needs_downsampling:
                    self.logger.info(f"Downsampling from {self.spatial_resolution}° to {self.target_resolution}°")
                    processed_ds = self._downsample_sst(processed_ds)
                    
                    # Save downsampled version
                    year_month = target_date.strftime("%Y/%m")
                    downsampled_dir = self.downsampled_path / year_month
                    downsampled_dir.mkdir(parents=True, exist_ok=True)
                    
                    downsampled_filename = f"sst_1deg_{target_date.strftime('%Y%m%d')}.nc"
                    downsampled_file_path = downsampled_dir / downsampled_filename
                    
                    processed_ds.to_netcdf(downsampled_file_path, format='NETCDF4', engine='netcdf4')
                    self.logger.info(f"Saved downsampled file: {downsampled_file_path}")
                    
                    # Set as potential final file and intermediate
                    final_file_path = downsampled_file_path
                    if self.needs_coord_harmonization:
                        intermediate_files.append(downsampled_file_path)
                
                # Step 2: Harmonize coordinates if needed
                if self.needs_coord_harmonization:
                    self.logger.info("Converting coordinates from 0-360° to -180-180°")
                    processed_ds = self._harmonize_coordinates(processed_ds)
                    
                    # Save harmonized version
                    year_month = target_date.strftime("%Y/%m")
                    harmonized_dir = self.harmonized_path / year_month
                    harmonized_dir.mkdir(parents=True, exist_ok=True)
                    
                    harmonized_filename = f"sst_harmonized_{target_date.strftime('%Y%m%d')}.nc"
                    harmonized_file_path = harmonized_dir / harmonized_filename
                    
                    processed_ds.to_netcdf(harmonized_file_path, format='NETCDF4', engine='netcdf4')
                    self.logger.info(f"Saved harmonized file: {harmonized_file_path}")
                    
                    # Set harmonized as final file
                    final_file_path = harmonized_file_path
                
                # Auto-optimize storage by removing raw and intermediate files
                if final_file_path:
                    optimization_result = self._auto_optimize_storage(
                        target_date=target_date,
                        raw_file_path=raw_file_path,
                        intermediate_files=intermediate_files,
                        final_file_path=final_file_path,
                        keep_raw_files=True
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
    
    def _downsample_sst(self, ds: xr.Dataset) -> xr.Dataset:
        """
        Downsample SST data from 0.25° to 1° resolution using spatial averaging.
        
        Args:
            ds: Input xarray Dataset
            
        Returns:
            Downsampled Dataset
        """
        # Calculate coarsening factors
        lat_factor = int(self.target_resolution / self.spatial_resolution)  # 4
        lon_factor = int(self.target_resolution / self.spatial_resolution)  # 4
        
        # Use xarray's coarsen method for efficient downsampling
        coarsened = ds.coarsen(
            lat=lat_factor,
            lon=lon_factor,
            boundary='trim'  # Drop incomplete edge cells
        ).mean()
        
        # Add attributes to indicate processing
        coarsened.attrs.update({
            'processing_note': f'Downsampled from {self.spatial_resolution}° to {self.target_resolution}° resolution',
            'processing_method': 'spatial_averaging',
            'processing_date': str(date.today()),
            'original_resolution': f'{self.spatial_resolution}°',
            'target_resolution': f'{self.target_resolution}°'
        })
        
        return coarsened
    
    def _harmonize_coordinates(self, ds: xr.Dataset) -> xr.Dataset:
        """
        Convert longitude coordinates from 0-360° to -180-180°.
        
        Args:
            ds: Input xarray Dataset
            
        Returns:
            Dataset with harmonized coordinates
        """
        # Check if conversion is needed
        lon_min, lon_max = float(ds.lon.min()), float(ds.lon.max())
        
        if lon_min >= 0 and lon_max > 180:
            # Need to convert from 0-360 to -180-180
            ds = ds.assign_coords(lon=(ds.lon + 180) % 360 - 180)
            ds = ds.sortby('lon')
            
            # Add processing note
            ds.attrs.update({
                'coordinate_processing': 'Converted longitude from 0-360° to -180-180°',
                'coordinate_processing_date': str(date.today())
            })
            
            self.logger.info("Converted longitude coordinates from 0-360° to -180-180°")
        else:
            self.logger.info("Coordinates already in -180-180° format")
        
        return ds
    
    def get_date_coverage(self) -> dict:
        """Get information about date coverage for downloaded SST data."""
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
                # Extract date from filename: oisst-avhrr-v02r01.YYYYMMDD.nc
                date_str = file_path.name.split('.')[1]
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
        """Validate all downloaded SST data."""
        base_validation = super().validate_downloaded_data()
        
        # Add SST-specific validation
        sst_validation = {
            "date_coverage": self.get_date_coverage(),
            "processing_status": {
                "downsampled_files": 0,
                "harmonized_files": 0
            }
        }
        
        # Check processed files
        if self.needs_downsampling and self.downsampled_path.exists():
            downsampled_files = list(self.downsampled_path.rglob("*.nc"))
            sst_validation["processing_status"]["downsampled_files"] = len(downsampled_files)
        
        if self.needs_coord_harmonization and self.harmonized_path.exists():
            harmonized_files = list(self.harmonized_path.rglob("*.nc"))
            sst_validation["processing_status"]["harmonized_files"] = len(harmonized_files)
        
        # Combine validations
        combined_validation = {**base_validation, **sst_validation}
        
        return combined_validation