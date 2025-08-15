#!/usr/bin/env python3
"""
GLODAP pH downloader for Global Ocean Data Analysis Project (1993-2021).
Downloads discrete pH measurements from CMEMS In Situ Carbon Observations.
"""

import os
import subprocess
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import date, datetime, timedelta
import pandas as pd
import logging

from .base_downloader import BaseDataDownloader

class GLODAPDownloader(BaseDataDownloader):
    """Downloads GLODAP discrete pH data from CMEMS (1993-2021)."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize GLODAP pH downloader."""
        super().__init__("glodap_ph", config_path)
        
        # Load GLODAP specific configuration
        self.dataset_config = self.config["datasets"]["glodap_ph"]
        
        # GLODAP-specific configuration
        self.product_id = self.dataset_config["product_id"]
        self.dataset_id = self.dataset_config["dataset_id"]
        self.base_url = self.dataset_config["base_url"]
        self.variables = self.dataset_config["variables"]
        self.data_type = self.dataset_config.get("data_type", "discrete_samples")
        
        # Processing configuration
        self.needs_coord_harmonization = self.dataset_config["processing"]["harmonize_coords"]
        
        # Update paths for GLODAP data
        self.raw_data_path = self.raw_data_path.parent / "glodap_ph"
        self.raw_data_path.mkdir(parents=True, exist_ok=True)
        
        # Create processed data directories if needed
        if self.needs_coord_harmonization:
            self.harmonized_path = self.processed_data_path / "unified_coords" / "glodap_ph"
            self.harmonized_path.mkdir(parents=True, exist_ok=True)
        
        # Load CMEMS credentials
        self._load_cmems_credentials()
        
        self.logger.info(f"Initialized GLODAP downloader for product: {self.product_id}")
    
    def _load_cmems_credentials(self):
        """Load CMEMS credentials from config or environment."""
        env_file = self.config_path / ".env"
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
            raise ValueError("CMEMS credentials not found. Please configure CMEMS_USERNAME and CMEMS_PASSWORD in .env file")
    
    def download_glodap_dataset(self, start_year: int = 1993, end_year: int = 2021) -> bool:
        """
        Download complete GLODAP dataset for specified year range.
        
        GLODAP provides discrete samples, not daily files, so we download
        the complete dataset and then filter by time period.
        
        Args:
            start_year: Starting year for data
            end_year: Ending year for data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # GLODAP filename - single dataset file
            filename = f"glodap_ph_{start_year}_{end_year}.nc"
            output_file = self.raw_data_path / filename
            
            # Skip if file already exists and is valid
            if output_file.exists() and self._validate_netcdf_file(output_file):
                self.logger.info(f"GLODAP file already exists and is valid: {filename}")
                return True
            
            # Build copernicusmarine command for GLODAP dataset
            cmd = [
                "copernicusmarine", "subset",
                "--dataset-id", self.dataset_id,
                "--username", self.cmems_username,
                "--password", self.cmems_password,
                "--output-filename", filename,
                "--output-directory", str(self.raw_data_path),
                "--force-download"  # Overwrite if exists
            ]
            
            # Add variable selection
            for variable in self.variables:
                cmd.extend(["--variable", variable])
            
            # Add temporal constraints
            cmd.extend([
                "--start-datetime", f"{start_year}-01-01T00:00:00",
                "--end-datetime", f"{end_year}-12-31T23:59:59"
            ])
            
            # Add global spatial coverage (GLODAP is global)
            cmd.extend([
                "--minimum-longitude", "-180",
                "--maximum-longitude", "180",
                "--minimum-latitude", "-90",
                "--maximum-latitude", "90"
            ])
            
            self.logger.info(f"Starting GLODAP download: {' '.join(cmd)}")
            
            # Execute download
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout for large dataset
            )
            
            if result.returncode != 0:
                self.logger.error(f"GLODAP download failed: {result.stderr}")
                return False
            
            # Validate downloaded file
            if not output_file.exists():
                self.logger.error(f"GLODAP download completed but file not found: {filename}")
                return False
            
            if not self._validate_netcdf_file(output_file):
                self.logger.error(f"Downloaded GLODAP file failed validation: {filename}")
                return False
            
            # Log success and file info
            file_size = output_file.stat().st_size / 1024 / 1024  # MB
            self.logger.info(f"Successfully downloaded GLODAP data: {filename} ({file_size:.1f} MB)")
            
            # Process the downloaded file
            success = self._process_downloaded_file(output_file, date(start_year, 1, 1))
            
            return success
            
        except subprocess.TimeoutExpired:
            self.logger.error("GLODAP download timed out after 1 hour")
            return False
        except Exception as e:
            self.logger.error(f"Error downloading GLODAP data: {e}")
            return False
    
    def download_date(self, target_date: date) -> bool:
        """
        Download GLODAP data for specific date.
        
        Note: GLODAP provides discrete samples, not daily files.
        This method downloads the complete dataset if not already available.
        
        Args:
            target_date: Target date for data
            
        Returns:
            True if successful, False otherwise
        """
        # Determine year range based on target date
        target_year = target_date.year
        
        # GLODAP covers 1993-2021, validate the year
        if target_year < 1993 or target_year > 2021:
            self.logger.warning(f"Target year {target_year} outside GLODAP range (1993-2021)")
            return False
        
        # Download complete dataset (will skip if already exists)
        return self.download_glodap_dataset(1993, 2021)
    
    def download_date_range(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """
        Download GLODAP data for date range.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            Dictionary with download results
        """
        results = {
            'total_requested': 1,  # Single dataset file
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        try:
            # Validate date range
            validated_start, validated_end = self.validate_date_range(start_date, end_date)
            
            # Download complete GLODAP dataset
            success = self.download_glodap_dataset(validated_start.year, validated_end.year)
            
            if success:
                results['successful'] = 1
                self.logger.info(f"Successfully downloaded GLODAP data for {validated_start} to {validated_end}")
            else:
                results['failed'] = 1
                results['errors'].append("Failed to download GLODAP dataset")
                
        except Exception as e:
            results['failed'] = 1
            results['errors'].append(f"Error in GLODAP download: {e}")
            self.logger.error(f"Error downloading GLODAP data range: {e}")
        
        return results
    
    def validate_date_range(self, start_date: date, end_date: date) -> tuple[date, date]:
        """
        Validate and adjust date range for GLODAP dataset.
        
        Args:
            start_date: Requested start date
            end_date: Requested end date
            
        Returns:
            Tuple of (validated_start_date, validated_end_date)
        """
        # GLODAP dataset boundaries
        dataset_start = date(1993, 1, 1)
        dataset_end = date(2021, 12, 31)
        
        # Adjust dates to fit within GLODAP dataset bounds
        validated_start = max(start_date, dataset_start)
        validated_end = min(end_date, dataset_end)
        
        if validated_start > dataset_end or validated_end < dataset_start:
            raise ValueError(
                f"Date range {start_date} to {end_date} is outside GLODAP dataset range "
                f"({dataset_start} to {dataset_end})"
            )
        
        if validated_start != start_date or validated_end != end_date:
            self.logger.info(
                f"Adjusted date range from {start_date}-{end_date} to {validated_start}-{validated_end} "
                f"to fit GLODAP dataset bounds"
            )
        
        return validated_start, validated_end
    
    def _validate_netcdf_file(self, file_path: Path) -> bool:
        """
        Validate NetCDF file containing GLODAP data.
        
        Args:
            file_path: Path to NetCDF file
            
        Returns:
            True if valid, False otherwise
        """
        try:
            import xarray as xr
            
            with xr.open_dataset(file_path) as ds:
                # Check for expected GLODAP variables
                required_vars = ["ph", "latitude", "longitude", "time"]
                missing_vars = [var for var in required_vars if var not in ds.variables]
                
                if missing_vars:
                    self.logger.error(f"GLODAP file missing required variables: {missing_vars}")
                    return False
                
                # Check for data
                if ds.sizes.get('obs', 0) == 0:  # GLODAP uses 'obs' dimension for observations
                    self.logger.error("GLODAP file contains no observations")
                    return False
                
                # Check pH data validity
                ph_data = ds['ph']
                if ph_data.isnull().all():
                    self.logger.error("All pH values are null in GLODAP file")
                    return False
                
                valid_ph_count = ((ph_data >= 6.0) & (ph_data <= 9.0)).sum()
                if valid_ph_count == 0:
                    self.logger.error("No valid pH values found in GLODAP file")
                    return False
                
                self.logger.info(f"GLODAP validation passed: {valid_ph_count} valid pH observations")
                return True
                
        except Exception as e:
            self.logger.error(f"Error validating GLODAP NetCDF file {file_path}: {e}")
            return False
    
    def _process_downloaded_file(self, raw_file_path: Path, target_date: date) -> bool:
        """
        Process downloaded GLODAP file.
        
        Args:
            raw_file_path: Path to downloaded raw file
            target_date: Target date (used for logging)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # For GLODAP, we don't need immediate processing since it's discrete data
            # Just validate and log success
            if self._validate_netcdf_file(raw_file_path):
                self.logger.info(f"GLODAP file validated and ready: {raw_file_path}")
                
                # Generate API sample data for testing
                self._log_api_data_sample(target_date, raw_file_path)
                
                return True
            else:
                self.logger.error(f"GLODAP file validation failed: {raw_file_path}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error processing GLODAP file {raw_file_path}: {e}")
            return False
    
    def _log_api_data_sample(self, target_date: date, processed_file: Path) -> dict:
        """Log GLODAP API data sample for testing."""
        try:
            import xarray as xr
            
            # Create API sample directory
            api_sample_dir = self.logs_path / "api_samples"
            api_sample_dir.mkdir(parents=True, exist_ok=True)
            
            sample_filename = f"glodap_ph_api_sample_{target_date.strftime('%Y%m%d')}.json"
            sample_file = api_sample_dir / sample_filename
            
            # Load dataset and extract sample data
            with xr.open_dataset(processed_file) as ds:
                # Get a sample of observations
                n_obs = min(100, ds.sizes.get('obs', 0))  # Sample first 100 observations
                
                if n_obs > 0:
                    sample_data = {
                        "dataset": "glodap_ph",
                        "source": f"{self.product_id} (GLODAP pH Observations)",
                        "data_type": "discrete_samples",
                        "sample_date": target_date.isoformat(),
                        "file_source": str(processed_file),
                        "total_observations": int(ds.sizes.get('obs', 0)),
                        "sample_size": n_obs,
                        "variables": {
                            var: {
                                "long_name": str(ds[var].attrs.get('long_name', var)),
                                "units": str(ds[var].attrs.get('units', '')),
                                "sample_values": ds[var].isel(obs=slice(0, min(10, n_obs))).values.tolist()
                            }
                            for var in self.variables if var in ds.variables
                        },
                        "coordinate_ranges": {
                            "latitude": {
                                "min": float(ds['latitude'].min()),
                                "max": float(ds['latitude'].max())
                            },
                            "longitude": {
                                "min": float(ds['longitude'].min()),
                                "max": float(ds['longitude'].max())
                            }
                        },
                        "time_range": {
                            "start": str(ds['time'].min().values),
                            "end": str(ds['time'].max().values)
                        },
                        "api_readiness": {
                            "ready_for_api": True,
                            "discrete_data": True,
                            "interpolation_required": True
                        }
                    }
                else:
                    sample_data = {
                        "dataset": "glodap_ph",
                        "error": "No observations found in dataset",
                        "api_readiness": {"ready_for_api": False}
                    }
            
            # Save sample data
            with open(sample_file, 'w') as f:
                json.dump(sample_data, f, indent=2, default=str)
            
            self.logger.info(f"GLODAP API sample data generated: {sample_file}")
            return sample_data
            
        except Exception as e:
            self.logger.error(f"Error generating GLODAP API sample: {e}")
            return {"api_readiness": {"ready_for_api": False}}
    
    def _get_filename_for_date(self, target_date: date) -> str:
        """Get filename for GLODAP data (single file covers all dates)."""
        return f"glodap_ph_1993_2021.nc"
    
    def get_dataset_info(self) -> Dict[str, Any]:
        """Get information about GLODAP dataset."""
        return {
            "name": self.dataset_config["name"],
            "description": self.dataset_config["description"],
            "data_type": self.data_type,
            "variables": self.variables,
            "temporal_coverage": self.dataset_config["temporal_coverage"],
            "spatial_coverage": "Global Ocean",
            "data_portal": self.dataset_config.get("data_portal_url", ""),
            "advantages": self.dataset_config.get("advantages", []),
            "limitations": self.dataset_config.get("limitations", [])
        }