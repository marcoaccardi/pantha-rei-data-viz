#!/usr/bin/env python3
"""
OSCAR Currents downloader for NASA Ocean Surface Current Analyses Real-time data.
Downloads daily NetCDF files from NASA Earthdata using authenticated access.
"""

import requests
import numpy as np
import xarray as xr
import tempfile
import shutil
import subprocess
import json
import time
import os
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from .base_downloader import BaseDataDownloader


class CurrentsOscarDownloader(BaseDataDownloader):
    """Downloads and processes NASA OSCAR Currents data."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize OSCAR Currents downloader."""
        super().__init__("currents_oscar", config_path)
        
        # Override paths to use unified currents folder
        self.raw_data_path = self.base_path / self.storage_config["raw_data_path"] / "currents"
        self.raw_data_path.mkdir(parents=True, exist_ok=True)
        
        # OSCAR-specific configuration
        self.base_url = self.dataset_config["base_url"]
        self.spatial_resolution = self.dataset_config["spatial_resolution"]
        self.variables = self.dataset_config["variables"]
        self.layers = self.dataset_config.get("layers", ["surface"])
        
        # Processing configuration
        self.needs_coord_harmonization = self.dataset_config["processing"]["harmonize_coords"]
        
        # Create harmonized path for processed files
        self.harmonized_path = self.processed_data_path / "unified_coords" / "currents"
        self.harmonized_path.mkdir(parents=True, exist_ok=True)
        
        # Load NASA Earthdata credentials
        self.nasa_username = None
        self.nasa_password = None
        self._load_nasa_credentials()
        
        # Validate credentials
        if not self.nasa_username or not self.nasa_password:
            raise ValueError("NASA Earthdata credentials not found. Please configure in credentials.env file")
        
        self.logger.info(f"Initialized OSCAR Currents downloader with NASA credentials for user: {self.nasa_username}")
    
    def _load_nasa_credentials(self):
        """Load NASA Earthdata credentials from environment file."""
        env_file = self.config_path / ".env"
        
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        if key.strip() == 'NASA_USERNAME':
                            self.nasa_username = value.strip()
                        elif key.strip() == 'NASA_PASSWORD':
                            self.nasa_password = value.strip()
        
        # Also check environment variables as fallback
        if not self.nasa_username:
            self.nasa_username = os.getenv("NASA_USERNAME")
        if not self.nasa_password:
            self.nasa_password = os.getenv("NASA_PASSWORD")
    
    def _get_filename_for_date(self, target_date: date) -> str:
        """Get filename for OSCAR currents file for given date."""
        return f"oscar_currents_{target_date.strftime('%Y%m%d')}.nc4"
    
    def _get_oscar_url(self, target_date: date) -> str:
        """
        Generate NASA Earthdata URL for downloading OSCAR currents data.
        
        Args:
            target_date: Date to download data for
            
        Returns:
            Full URL for the OSCAR file
        """
        date_str = target_date.strftime("%Y%m%d")
        return f"{self.base_url}oscar_currents_nrt_{date_str}.dap.nc4"
    
    def _setup_nasa_session(self) -> requests.Session:
        """Set up authenticated session for NASA Earthdata."""
        session = requests.Session()
        
        # Create a temporary netrc file for authentication
        netrc_content = f"machine urs.earthdata.nasa.gov login {self.nasa_username} password {self.nasa_password}\n"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.netrc', delete=False) as f:
            f.write(netrc_content)
            netrc_path = f.name
        
        # Set proper permissions
        os.chmod(netrc_path, 0o600)
        
        # Store netrc path for cleanup
        self._netrc_path = netrc_path
        
        return session
    
    def _cleanup_auth(self):
        """Clean up temporary authentication files."""
        if hasattr(self, '_netrc_path') and os.path.exists(self._netrc_path):
            os.unlink(self._netrc_path)
    
    def _download_oscar_file(self, target_date: date, output_file: Path) -> bool:
        """
        Download OSCAR currents file for a specific date using NASA Earthdata authentication.
        
        Args:
            target_date: Date to download data for
            output_file: Path where to save the downloaded file
            
        Returns:
            True if download successful, False otherwise
        """
        url = self._get_oscar_url(target_date)
        
        self.logger.info(f"Downloading OSCAR currents data for {target_date}")
        self.logger.info(f"URL: {url}")
        
        session = self._setup_nasa_session()
        
        try:
            # First, check if authentication is required
            response = session.head(url, timeout=30)
            
            if response.status_code in [401, 403]:
                self.logger.info("Authentication required, logging in to NASA Earthdata...")
                
                # Follow redirects for authentication
                response = session.get(url, stream=True, timeout=120, allow_redirects=True)
            else:
                response = session.get(url, stream=True, timeout=120)
            
            if response.status_code == 200:
                # Download the file
                with open(output_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                file_size_mb = output_file.stat().st_size / (1024 * 1024)
                self.logger.info(f"Successfully downloaded OSCAR file: {output_file.name} ({file_size_mb:.1f} MB)")
                return True
                
            else:
                self.logger.error(f"Failed to download OSCAR file. HTTP {response.status_code}: {response.reason}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error downloading OSCAR file: {e}")
            return False
        finally:
            session.close()
            self._cleanup_auth()
    
    def _process_oscar_file(self, raw_file: Path, target_date: date) -> Optional[Path]:
        """
        Process OSCAR file: coordinate harmonization and standardization.
        
        Args:
            raw_file: Path to raw OSCAR file
            target_date: Date of the data
            
        Returns:
            Path to processed file, or None if processing failed
        """
        try:
            # Load the dataset
            with xr.open_dataset(raw_file) as ds:
                self.logger.info(f"Processing OSCAR file with variables: {list(ds.data_vars.keys())}")
                
                # Variable mapping: OSCAR -> standard names
                var_mapping = {
                    'u': 'uo',  # zonal (eastward) velocity
                    'v': 'vo'   # meridional (northward) velocity
                }
                
                # Rename variables to standard names
                ds_renamed = ds.rename(var_mapping)
                
                # Handle coordinate harmonization (0-360° -> -180-180°)
                if self.needs_coord_harmonization:
                    self.logger.info("Converting coordinates from 0-360° to -180-180°")
                    
                    # Check current coordinate system
                    if 'lon' in ds_renamed.coords:
                        lon_coord = 'lon'
                    elif 'longitude' in ds_renamed.coords:
                        lon_coord = 'longitude'
                    else:
                        self.logger.error("No longitude coordinate found")
                        return None
                    
                    # Convert longitude if needed
                    lon_values = ds_renamed[lon_coord].values
                    if lon_values.max() > 180:
                        # Convert 0-360 to -180-180
                        lon_values = np.where(lon_values > 180, lon_values - 360, lon_values)
                        ds_renamed = ds_renamed.assign_coords({lon_coord: lon_values})
                        
                        # Sort by longitude to maintain proper order
                        ds_renamed = ds_renamed.sortby(lon_coord)
                        
                        self.logger.info("Coordinate conversion complete")
                    else:
                        self.logger.info("Coordinates already in -180-180° format")
                
                # Rename coordinate to standard names if needed
                if 'lon' in ds_renamed.coords:
                    ds_renamed = ds_renamed.rename({'lon': 'longitude'})
                if 'lat' in ds_renamed.coords:
                    ds_renamed = ds_renamed.rename({'lat': 'latitude'})
                
                # Add processing metadata
                ds_renamed.attrs.update({
                    'source': 'NASA OSCAR',
                    'processing_date': datetime.now().isoformat(),
                    'coordinate_system': '-180-180',
                    'processed_by': 'panta-rhei-data-map'
                })
                
                # Save processed file
                processed_filename = f"oscar_currents_harmonized_{target_date.strftime('%Y%m%d')}.nc"
                processed_path = self.harmonized_path / target_date.strftime('%Y') / target_date.strftime('%m')
                processed_path.mkdir(parents=True, exist_ok=True)
                processed_file = processed_path / processed_filename
                
                # Save with compression
                ds_renamed.to_netcdf(
                    processed_file,
                    encoding={var: {'zlib': True, 'complevel': 4} for var in ds_renamed.data_vars}
                )
                
                file_size_mb = processed_file.stat().st_size / (1024 * 1024)
                self.logger.info(f"Processed file saved: {processed_file} ({file_size_mb:.1f} MB)")
                
                return processed_file
                
        except Exception as e:
            self.logger.error(f"Error processing OSCAR file {raw_file}: {e}")
            return None
    
    def download_for_date(self, target_date: date) -> dict:
        """
        Download and process OSCAR currents data for a specific date.
        
        Args:
            target_date: Date to download data for
            
        Returns:
            Dictionary with download results
        """
        filename = self._get_filename_for_date(target_date)
        
        # Check if file already exists
        final_file = self.harmonized_path / target_date.strftime('%Y') / target_date.strftime('%m') / f"oscar_currents_harmonized_{target_date.strftime('%Y%m%d')}.nc"
        
        if final_file.exists() and not self.force_redownload:
            self.logger.info(f"Processed file already exists: {final_file}")
            return {
                'success': True,
                'filename': filename,
                'path': final_file,
                'skipped': True,
                'message': 'File already exists'
            }
        
        # Create temporary file for raw download
        with tempfile.NamedTemporaryFile(suffix='.nc4', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        
        try:
            # Download raw file
            if not self._download_oscar_file(target_date, temp_path):
                return {
                    'success': False,
                    'filename': filename,
                    'error': 'Download failed'
                }
            
            # Save raw file for preservation
            raw_filename = f"oscar_currents_raw_{target_date.strftime('%Y%m%d')}.nc4"
            raw_dir = self.raw_data_path / target_date.strftime('%Y') / target_date.strftime('%m')
            raw_dir.mkdir(parents=True, exist_ok=True)
            raw_file = raw_dir / raw_filename
            
            shutil.copy2(temp_path, raw_file)
            self.logger.info(f"Raw file preserved: {raw_file}")
            
            # Process the file
            processed_file = self._process_oscar_file(temp_path, target_date)
            
            if processed_file:
                # Generate API sample
                self._generate_api_sample(processed_file, target_date)
                
                return {
                    'success': True,
                    'filename': filename,
                    'raw_path': raw_file,
                    'processed_path': processed_file,
                    'message': 'Download and processing successful'
                }
            else:
                return {
                    'success': False,
                    'filename': filename,
                    'error': 'Processing failed'
                }
                
        except Exception as e:
            self.logger.error(f"Unexpected error downloading OSCAR file for {target_date}: {e}")
            return {
                'success': False,
                'filename': filename,
                'error': str(e)
            }
        finally:
            # Clean up temporary file
            if temp_path.exists():
                temp_path.unlink()
    
    def download_date(self, target_date: date) -> bool:
        """
        Download data for a specific date (abstract method implementation).
        
        Args:
            target_date: Date to download data for
            
        Returns:
            True if download successful, False otherwise
        """
        try:
            result = self.download_for_date(target_date)
            return result.get('success', False)
        except Exception as e:
            self.logger.error(f"Error in OSCAR download_date for {target_date}: {e}")
            return False
    
    def _generate_api_sample(self, processed_file: Path, target_date: date):
        """Generate API sample data for testing and validation."""
        try:
            sample_points = [
                {'lat': 0.0, 'lon': 0.0, 'name': 'Equatorial Atlantic'},
                {'lat': 25.0, 'lon': -80.0, 'name': 'Gulf Stream'},
                {'lat': -40.0, 'lon': 20.0, 'name': 'Agulhas Current'},
            ]
            
            samples = []
            
            with xr.open_dataset(processed_file) as ds:
                for point in sample_points:
                    try:
                        # Find nearest point
                        data_point = ds.sel(
                            latitude=point['lat'], 
                            longitude=point['lon'], 
                            method='nearest'
                        )
                        
                        # Extract data
                        sample_data = {}
                        for var in ['uo', 'vo']:
                            if var in data_point:
                                value = float(data_point[var].values)
                                if not np.isnan(value):
                                    sample_data[var] = {
                                        'value': round(value, 4),
                                        'units': 'm/s',
                                        'long_name': f'{"Eastward" if var == "uo" else "Northward"} velocity',
                                        'valid': True
                                    }
                                else:
                                    sample_data[var] = {
                                        'value': None,
                                        'valid': False
                                    }
                        
                        if sample_data:
                            samples.append({
                                'location': point['name'],
                                'requested_coordinates': {'lat': point['lat'], 'lon': point['lon']},
                                'actual_coordinates': {
                                    'lat': float(data_point.latitude.values),
                                    'lon': float(data_point.longitude.values)
                                },
                                'data': sample_data
                            })
                    
                    except Exception as e:
                        self.logger.warning(f"Error sampling point {point['name']}: {e}")
            
            # Save API sample
            api_sample = {
                'dataset': 'currents_oscar',
                'date': target_date.strftime('%Y-%m-%d'),
                'source': 'NASA OSCAR',
                'processing_timestamp': datetime.now().isoformat(),
                'samples': samples,
                'api_readiness': {
                    'ready_for_api': len(samples) > 0,
                    'variables_available': ['uo', 'vo']
                }
            }
            
            # Save to logs directory
            api_logs_dir = self.logs_path / "api_samples"
            api_logs_dir.mkdir(parents=True, exist_ok=True)
            
            sample_file = api_logs_dir / f"oscar_currents_api_sample_{target_date.strftime('%Y%m%d')}.json"
            with open(sample_file, 'w') as f:
                json.dump(api_sample, f, indent=2)
            
            self.logger.info(f"API sample data generated: {sample_file}")
            
        except Exception as e:
            self.logger.warning(f"Failed to generate API sample: {e}")