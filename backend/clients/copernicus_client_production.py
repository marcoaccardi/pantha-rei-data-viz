#!/usr/bin/env python3
"""
Copernicus Marine Service API client - Production Version.
This client uses real API authentication via copernicusmarine toolbox.
"""

import os
import subprocess
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import logging
import numpy as np
from dotenv import load_dotenv

from .base_client import BaseAPIClient

# Load environment variables
load_dotenv()

class CopernicusMarineProductionClient(BaseAPIClient):
    """
    Production client for Copernicus Marine Service API.
    
    Features:
    - Real API authentication using credentials
    - Direct data access via copernicusmarine toolbox
    - Subset queries for specific coordinates and time ranges
    - Support for all major ocean climate parameters
    """
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize production Copernicus Marine Service client."""
        super().__init__(
            api_name="Copernicus Marine Service Production",
            base_url="https://data.marine.copernicus.eu",
            cache_dir=cache_dir
        )
        
        # Load credentials from environment (try both uppercase and lowercase)
        self.username = os.getenv('COPERNICUS_USERNAME') or os.getenv('copernicus_username')
        self.password = os.getenv('COPERNICUS_PASSWORD') or os.getenv('copernicus_password')
        
        if not self.username or not self.password:
            raise ValueError("Copernicus credentials not found. Please set copernicus_username and copernicus_password in .env file")
        
        # Updated with correct 2025 Copernicus Marine Service dataset IDs
        self.key_datasets = {
            'sst_global_l4': {
                'dataset_id': 'cmems_obs-sst_glo_phy_nrt_l4_P1D-m',
                'name': 'Global SST Level 4 Daily',
                'parameters': ['analysed_sst'],
                'spatial_resolution': '0.10_degree',
                'temporal_resolution': 'daily',
                'coverage': {'global': True}
            },
            'wave_global': {
                'dataset_id': 'cmems_mod_glo_wav_anfc_0.083deg_PT3H-i',
                'name': 'Global Ocean Waves Analysis and Forecast',
                'parameters': ['VHM0', 'VTM02', 'VMDR'],  # Wave height, period, direction
                'spatial_resolution': '0.083_degree',
                'temporal_resolution': '3hourly',
                'coverage': {'global': True}
            },
            'currents_global': {
                'dataset_id': 'cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m',
                'name': 'Global Ocean Currents',
                'parameters': ['uo', 'vo'],  # Eastward and northward currents
                'spatial_resolution': '0.083_degree',
                'temporal_resolution': 'daily',
                'coverage': {'global': True}
            },
            'salinity_global': {
                'dataset_id': 'cmems_mod_glo_phy-so_anfc_0.083deg_P1D-m',
                'name': 'Global Ocean Salinity',
                'parameters': ['so'],  # Sea water salinity
                'spatial_resolution': '0.083_degree',
                'temporal_resolution': 'daily',
                'coverage': {'global': True}
            },
            'temperature_global': {
                'dataset_id': 'cmems_mod_glo_phy-thetao_anfc_0.083deg_P1D-m',
                'name': 'Global Ocean Temperature',
                'parameters': ['thetao'],  # Sea water potential temperature
                'spatial_resolution': '0.083_degree',
                'temporal_resolution': 'daily',
                'coverage': {'global': True}
            },
            'biogeochemistry_global': {
                'dataset_id': 'cmems_mod_glo_bgc-bio_anfc_0.25deg_P1D-m',
                'name': 'Global Ocean Biogeochemistry Biology',
                'parameters': ['nppv', 'o2'],  # Net primary production, dissolved oxygen
                'spatial_resolution': '0.25_degree',
                'temporal_resolution': 'daily',
                'coverage': {'global': True}
            },
            'chlorophyll_global': {
                'dataset_id': 'cmems_mod_glo_bgc-pft_anfc_0.25deg_P1D-m',
                'name': 'Global Ocean Chlorophyll / Plankton',
                'parameters': ['chl'],  # Mass concentration of chlorophyll a
                'spatial_resolution': '0.25_degree',
                'temporal_resolution': 'daily',
                'coverage': {'global': True}
            },
            'ph_global': {
                'dataset_id': 'cmems_mod_glo_bgc-car_anfc_0.25deg_P1D-m',
                'name': 'Global Ocean pH / Ocean Acidification',
                'parameters': ['ph'],  # Sea water pH on total scale
                'spatial_resolution': '0.25_degree',
                'temporal_resolution': 'daily',
                'coverage': {'global': True}
            },
            'sea_level_global': {
                'dataset_id': 'cmems_obs-sl_glo_phy-ssh_nrt_allsat-l4-duacs-0.25deg_P1D',
                'name': 'Global Sea Level Daily',
                'parameters': ['sla', 'adt', 'ugos', 'vgos'],
                'spatial_resolution': '0.25_degree',
                'temporal_resolution': 'daily',
                'coverage': {'global': True}
            }
        }
        
        # Test authentication on initialization
        self._test_authentication()
        
        self.logger.info("Copernicus Marine Production client initialized successfully")
    
    def _test_authentication(self):
        """Test authentication with Copernicus Marine Service."""
        try:
            # Set up environment with credentials
            env = os.environ.copy()
            env['COPERNICUSMARINE_SERVICE_USERNAME'] = self.username
            env['COPERNICUSMARINE_SERVICE_PASSWORD'] = self.password
            
            # Try to login using environment variables (force overwrite any existing credentials)
            login_result = subprocess.run(
                ['copernicusmarine', 'login', '--force-overwrite'],
                capture_output=True,
                text=True,
                env=env
            )
            
            if login_result.returncode != 0:
                raise Exception(f"Authentication failed: {login_result.stderr}")
            
            # Verify credentials are valid
            check_result = subprocess.run(
                ['copernicusmarine', 'login', '--check-credentials-valid'],
                capture_output=True,
                text=True,
                env=env
            )
            
            if check_result.returncode != 0:
                raise Exception(f"Credential validation failed: {check_result.stderr}")
            
            self.logger.info("Copernicus Marine authentication successful")
            
        except FileNotFoundError:
            raise Exception("copernicusmarine CLI not found. Please install: pip install copernicusmarine")
        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            raise
    
    def query_data(self, lat: float, lon: float, start_date: str, end_date: str,
                  parameters: List[str] = None, dataset_key: str = None) -> Dict[str, Any]:
        """
        Query real data from Copernicus Marine Service for specific location and time.
        
        Args:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            parameters: List of parameters to retrieve
            dataset_key: Specific dataset to query (default: sst_global_l4)
            
        Returns:
            Dictionary with actual query results and data
        """
        self.logger.info(f"Querying real Copernicus data for {lat:.4f}, {lon:.4f} from {start_date} to {end_date}")
        
        # Validate inputs
        if not self.validate_coordinates(lat, lon):
            raise ValueError(f"Invalid coordinates: {lat}, {lon}")
        
        if not self.validate_time_range(start_date, end_date):
            raise ValueError(f"Invalid time range: {start_date} to {end_date}")
        
        # Determine which dataset to use
        if not dataset_key:
            dataset_key = 'sst_global_l4'
        
        if dataset_key not in self.key_datasets:
            raise ValueError(f"Unknown dataset: {dataset_key}")
        
        dataset_info = self.key_datasets[dataset_key]
        params_to_query = parameters or dataset_info['parameters']
        
        # Create a small bounding box around the point (0.1 degree radius)
        min_lat = lat - 0.1
        max_lat = lat + 0.1
        min_lon = lon - 0.1
        max_lon = lon + 0.1
        
        try:
            # Create temporary output directory
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                output_file = Path(temp_dir) / f"subset_{datetime.now().strftime('%Y%m%d_%H%M%S')}.nc"
                
                # Build copernicusmarine subset command
                cmd = [
                    'copernicusmarine', 'subset',
                    '--dataset-id', dataset_info['dataset_id']
                ]
                
                # Add variables (one --variable flag per variable)
                for param in params_to_query:
                    cmd.extend(['--variable', param])
                
                # Add remaining parameters
                cmd.extend([
                    '--start-datetime', f"{start_date}T00:00:00",
                    '--end-datetime', f"{end_date}T23:59:59",
                    '--minimum-longitude', str(min_lon),
                    '--maximum-longitude', str(max_lon),
                    '--minimum-latitude', str(min_lat),
                    '--maximum-latitude', str(max_lat),
                    '--output-filename', str(output_file),
                    '--force-download'
                ])
                
                # Execute the command with proper environment
                env = os.environ.copy()
                env['COPERNICUSMARINE_SERVICE_USERNAME'] = self.username
                env['COPERNICUSMARINE_SERVICE_PASSWORD'] = self.password
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    env=env
                )
                
                if result.returncode != 0:
                    self.logger.error(f"Query failed: {result.stderr}")
                    
                    # Return structured error response
                    return {
                        'api_name': self.api_name,
                        'dataset_key': dataset_key,
                        'dataset_id': dataset_info['dataset_id'],
                        'query_parameters': {
                            'latitude': lat,
                            'longitude': lon,
                            'start_date': start_date,
                            'end_date': end_date,
                            'parameters': params_to_query
                        },
                        'status': 'error',
                        'error': result.stderr,
                        'message': 'Query failed - check dataset availability and parameters'
                    }
                
                # Check if file was created and get basic info
                data_info = {
                    'command_output': result.stdout,
                    'file_created': output_file.exists(),
                    'file_size': output_file.stat().st_size if output_file.exists() else 0
                }
                
                if output_file.exists():
                    # Try to extract basic info from netcdf file (if xarray is available)
                    try:
                        import xarray as xr
                        ds = xr.open_dataset(output_file)
                        data_info['data_variables'] = list(ds.data_vars)
                        data_info['coordinates'] = list(ds.coords)
                        data_info['time_range'] = [str(ds.time.min().values), str(ds.time.max().values)]
                        data_info['spatial_bounds'] = {
                            'lat_min': float(ds.latitude.min().values),
                            'lat_max': float(ds.latitude.max().values),
                            'lon_min': float(ds.longitude.min().values),
                            'lon_max': float(ds.longitude.max().values)
                        }
                        ds.close()
                    except ImportError:
                        data_info['note'] = 'xarray not available for detailed data inspection'
                    except Exception as e:
                        data_info['data_read_error'] = str(e)
                
                # Structure the response
                query_result = {
                    'api_name': self.api_name,
                    'dataset_key': dataset_key,
                    'dataset_id': dataset_info['dataset_id'],
                    'query_parameters': {
                        'latitude': lat,
                        'longitude': lon,
                        'start_date': start_date,
                        'end_date': end_date,
                        'parameters': params_to_query
                    },
                    'spatial_resolution': dataset_info['spatial_resolution'],
                    'temporal_resolution': dataset_info['temporal_resolution'],
                    'status': 'success',
                    'data': data_info,
                    'access_method': 'copernicusmarine_subset',
                    'query_timestamp': datetime.now().isoformat(),
                    'message': 'Data successfully retrieved from Copernicus Marine Service'
                }
                
                return query_result
            
        except Exception as e:
            self.logger.error(f"Error querying Copernicus data: {e}")
            return {
                'api_name': self.api_name,
                'dataset_key': dataset_key,
                'status': 'error',
                'error': str(e),
                'message': 'Query failed due to unexpected error'
            }
    
    def get_dataset_metadata(self, dataset_id: str) -> Dict[str, Any]:
        """
        Get detailed metadata for a specific dataset.
        
        Args:
            dataset_id: Copernicus dataset ID
            
        Returns:
            Dictionary with dataset metadata
        """
        try:
            # Use copernicusmarine describe command
            cmd = [
                'copernicusmarine', 'describe',
                '--dataset-id', dataset_id
            ]
            
            env = os.environ.copy()
            env['COPERNICUSMARINE_SERVICE_USERNAME'] = self.username
            env['COPERNICUSMARINE_SERVICE_PASSWORD'] = self.password
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env
            )
            
            if result.returncode == 0:
                # The describe command returns text output, not JSON
                metadata = {
                    'description_text': result.stdout,
                    'raw_output': result.stdout
                }
                return {
                    'status': 'success',
                    'dataset_id': dataset_id,
                    'metadata': metadata,
                    'query_timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'status': 'error',
                    'dataset_id': dataset_id,
                    'error': result.stderr,
                    'message': 'Failed to retrieve dataset metadata'
                }
                
        except Exception as e:
            self.logger.error(f"Error getting dataset metadata: {e}")
            return {
                'status': 'error',
                'dataset_id': dataset_id,
                'error': str(e)
            }
    
    def download_data(self, dataset_key: str, output_dir: Path,
                     start_date: str, end_date: str,
                     bbox: Tuple[float, float, float, float] = None) -> Dict[str, Any]:
        """
        Download data for offline processing.
        
        Args:
            dataset_key: Key for dataset to download
            output_dir: Directory to save downloaded files
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            bbox: Bounding box (min_lon, min_lat, max_lon, max_lat)
            
        Returns:
            Dictionary with download status and file paths
        """
        if dataset_key not in self.key_datasets:
            raise ValueError(f"Unknown dataset: {dataset_key}")
        
        dataset_info = self.key_datasets[dataset_key]
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate output filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f"{dataset_key}_{timestamp}.nc"
        
        try:
            # Build download command
            cmd = [
                'copernicusmarine', 'subset',
                '--dataset-id', dataset_info['dataset_id']
            ]
            
            # Add variables (one --variable flag per variable)
            for param in dataset_info['parameters']:
                cmd.extend(['--variable', param])
            
            # Add remaining parameters
            cmd.extend([
                '--start-datetime', f"{start_date}T00:00:00",
                '--end-datetime', f"{end_date}T23:59:59",
                '--output-directory', str(output_dir),
                '--output-filename', output_file.name,
                '--force-download'
            ])
            
            # Add bounding box if provided
            if bbox:
                min_lon, min_lat, max_lon, max_lat = bbox
                cmd.extend([
                    '--minimum-longitude', str(min_lon),
                    '--maximum-longitude', str(max_lon),
                    '--minimum-latitude', str(min_lat),
                    '--maximum-latitude', str(max_lat)
                ])
            
            # Execute download
            env = os.environ.copy()
            env['COPERNICUSMARINE_SERVICE_USERNAME'] = self.username
            env['COPERNICUSMARINE_SERVICE_PASSWORD'] = self.password
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env
            )
            
            if result.returncode == 0:
                return {
                    'status': 'success',
                    'dataset_key': dataset_key,
                    'output_file': str(output_file),
                    'file_size': output_file.stat().st_size if output_file.exists() else 0,
                    'download_timestamp': datetime.now().isoformat(),
                    'message': 'Data downloaded successfully'
                }
            else:
                return {
                    'status': 'error',
                    'dataset_key': dataset_key,
                    'error': result.stderr,
                    'message': 'Download failed'
                }
                
        except Exception as e:
            self.logger.error(f"Error downloading data: {e}")
            return {
                'status': 'error',
                'dataset_key': dataset_key,
                'error': str(e)
            }
    
    def get_available_parameters(self, dataset_key: str) -> List[str]:
        """Get list of available parameters for a dataset."""
        if dataset_key in self.key_datasets:
            return self.key_datasets[dataset_key]['parameters']
        else:
            # Try to get from API
            dataset_id = dataset_key  # Assume direct dataset_id if not in our list
            metadata = self.get_dataset_metadata(dataset_id)
            
            if metadata['status'] == 'success':
                # Extract parameters from metadata
                # This depends on the actual structure returned by copernicusmarine
                return metadata.get('metadata', {}).get('variables', [])
            else:
                return []
    
    def discover_coverage(self) -> Dict[str, Any]:
        """
        Discover spatial and temporal coverage from Copernicus Marine Service.
        Production implementation using real API.
        """
        self.logger.info("Discovering Copernicus Marine Service coverage...")
        
        coverage_data = {
            'api_name': self.api_name,
            'discovery_timestamp': datetime.now().isoformat(),
            'datasets': {},
            'global_coverage': {},
            'parameter_availability': {},
            'connection_status': {'status': 'connected', 'authenticated': True}
        }
        
        try:
            # Discover datasets
            for dataset_key, dataset_info in self.key_datasets.items():
                self.logger.info(f"Checking dataset: {dataset_key}")
                
                # Try to get metadata for each dataset
                metadata = self.get_dataset_metadata(dataset_info['dataset_id'])
                
                if metadata['status'] == 'success':
                    coverage_data['datasets'][dataset_key] = {
                        'dataset_id': dataset_info['dataset_id'],
                        'name': dataset_info['name'],
                        'parameters': dataset_info['parameters'],
                        'spatial_resolution': dataset_info['spatial_resolution'],
                        'temporal_resolution': dataset_info['temporal_resolution'],
                        'metadata_available': True
                    }
                else:
                    coverage_data['datasets'][dataset_key] = dataset_info
                    coverage_data['datasets'][dataset_key]['metadata_available'] = False
                
                # Update parameter availability
                for param in dataset_info['parameters']:
                    if param not in coverage_data['parameter_availability']:
                        coverage_data['parameter_availability'][param] = []
                    coverage_data['parameter_availability'][param].append(dataset_key)
            
            # Set global coverage info
            coverage_data['global_coverage'] = {
                'available': True,
                'spatial_bounds': {
                    'lat_min': -90, 'lat_max': 90,
                    'lon_min': -180, 'lon_max': 180
                },
                'temporal_bounds': {
                    'start': '1993-01-01',
                    'end': datetime.now().strftime('%Y-%m-%d'),
                    'real_time_lag': '1-3 days'
                }
            }
            
            return coverage_data
            
        except Exception as e:
            self.logger.error(f"Coverage discovery failed: {e}")
            coverage_data['error'] = str(e)
            coverage_data['connection_status']['status'] = 'error'
            return coverage_data
    
    def get_available_datasets(self) -> List[Dict[str, Any]]:
        """
        Get list of available datasets from Copernicus Marine Service.
        """
        datasets = []
        
        for dataset_key, dataset_info in self.key_datasets.items():
            datasets.append({
                'key': dataset_key,
                'dataset_id': dataset_info['dataset_id'],
                'name': dataset_info['name'],
                'parameters': dataset_info['parameters'],
                'spatial_resolution': dataset_info['spatial_resolution'],
                'temporal_resolution': dataset_info['temporal_resolution'],
                'coverage': dataset_info['coverage'],
                'api_name': self.api_name
            })
        
        return datasets