#!/usr/bin/env python3
"""
Copernicus Marine Service API client.
#1 RECOMMENDED API for comprehensive ocean climate data.
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

from .base_client import BaseAPIClient

class CopernicusMarineClient(BaseAPIClient):
    """
    Client for Copernicus Marine Service API.
    
    Features:
    - Direct API access with subset queries (no downloads)
    - Ocean Climate Portal with pre-calculated indicators
    - Global and regional data for all climate parameters
    - No quotas on volume or bandwidth
    """
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize Copernicus Marine Service client."""
        super().__init__(
            api_name="Copernicus Marine Service",
            base_url="https://data.marine.copernicus.eu",
            cache_dir=cache_dir
        )
        
        # Copernicus-specific endpoints
        self.catalog_url = f"{self.base_url}/catalogue"
        self.products_url = f"{self.base_url}/products"
        self.subset_url = f"{self.base_url}/api/subset"
        
        # Climate data portal
        self.climate_portal_url = "https://marine.copernicus.eu/ocean-climate-portal"
        
        # Known key datasets for climate analysis
        self.key_datasets = {
            # Sea Surface Temperature
            'sst_global_l4': {
                'dataset_id': 'cmems_obs-sst_glo_phy_nrt_l4_0.083deg_P1D',
                'name': 'Global SST Level 4 Daily',
                'parameters': ['analysed_sst', 'sst_anomaly'],
                'spatial_resolution': '0.083_degree',
                'temporal_resolution': 'daily',
                'coverage': {'global': True}
            },
            
            # Sea Level
            'sea_level_global': {
                'dataset_id': 'cmems_obs-sl_glo_phy-ssh_nrt_allsat-l4-duacs-0.25deg_P1D',
                'name': 'Global Sea Level Daily',
                'parameters': ['adt', 'sla', 'ugos', 'vgos'],
                'spatial_resolution': '0.25_degree',
                'temporal_resolution': 'daily',
                'coverage': {'global': True}
            },
            
            # Ocean Heat Content
            'ocean_heat_content': {
                'dataset_id': 'cmems_obs-oc_glo_bgc-plankton_nrt_l4-gapfree-multi-4km_P1D',
                'name': 'Global Ocean Heat Content',
                'parameters': ['ohc300', 'ohc700', 'ohc2000'],
                'spatial_resolution': '4km',
                'temporal_resolution': 'daily',
                'coverage': {'global': True}
            },
            
            # Biogeochemistry
            'biogeochemistry_global': {
                'dataset_id': 'cmems_mod_glo_bgc_anfc_0.25deg_P1D-m',
                'name': 'Global Biogeochemistry Analysis and Forecast',
                'parameters': ['chl', 'ph', 'o2', 'no3', 'po4'],
                'spatial_resolution': '0.25_degree', 
                'temporal_resolution': 'daily',
                'coverage': {'global': True}
            },
            
            # Ocean Currents
            'currents_global': {
                'dataset_id': 'cmems_mod_glo_phy_anfc_0.083deg_P1D-m',
                'name': 'Global Ocean Physics Analysis and Forecast',
                'parameters': ['uo', 'vo', 'thetao', 'so'],
                'spatial_resolution': '0.083_degree',
                'temporal_resolution': 'daily', 
                'coverage': {'global': True}
            },
            
            # Sea Ice
            'sea_ice_arctic': {
                'dataset_id': 'cmems_obs-si_arc_phy_nrt_l4_P1D',
                'name': 'Arctic Sea Ice Daily',
                'parameters': ['sea_ice_concentration', 'sea_ice_thickness'],
                'spatial_resolution': '10km',
                'temporal_resolution': 'daily',
                'coverage': {'region': 'Arctic'}
            },
            
            'sea_ice_antarctic': {
                'dataset_id': 'cmems_obs-si_ant_phy_nrt_l4_P1D', 
                'name': 'Antarctic Sea Ice Daily',
                'parameters': ['sea_ice_concentration', 'sea_ice_thickness'],
                'spatial_resolution': '10km',
                'temporal_resolution': 'daily',
                'coverage': {'region': 'Antarctic'}
            }
        }
        
        # Initialize coverage information
        self.coverage_info = {
            'spatial_bounds': {
                'lat_min': -90, 'lat_max': 90,
                'lon_min': -180, 'lon_max': 180
            },
            'temporal_bounds': {
                'start': '1993-01-01',  # Satellite era beginning
                'end': datetime.now().strftime('%Y-%m-%d'),
                'real_time_lag': '1-3 days'
            },
            'available_parameters': [
                'sea_surface_temperature', 'sst_anomaly', 'sea_level_anomaly',
                'ocean_heat_content', 'chlorophyll_a', 'ph', 'dissolved_oxygen',
                'ocean_currents_u', 'ocean_currents_v', 'sea_ice_concentration',
                'sea_ice_thickness', 'salinity', 'temperature_profiles'
            ],
            'datasets': self.key_datasets,
            'last_updated': None
        }
        
        self.logger.info("Copernicus Marine Service client initialized")
        self.logger.info(f"Key datasets available: {len(self.key_datasets)}")
    
    def discover_coverage(self) -> Dict[str, Any]:
        """
        Discover spatial and temporal coverage from Copernicus Marine Service.
        
        Returns:
            Dictionary with comprehensive coverage information
        """
        self.logger.info("Discovering Copernicus Marine Service coverage...")
        
        coverage_data = {
            'api_name': self.api_name,
            'discovery_timestamp': datetime.now().isoformat(),
            'datasets': {},
            'global_coverage': {},
            'regional_coverage': {},
            'parameter_availability': {},
            'temporal_coverage': {},
            'access_methods': []
        }
        
        try:
            # Test connection first
            connection_status = self.test_connection()
            coverage_data['connection_status'] = connection_status
            
            if connection_status['status'] != 'connected':
                self.logger.warning("Cannot discover coverage - connection failed")
                return coverage_data
            
            # Discover datasets
            for dataset_key, dataset_info in self.key_datasets.items():
                self.logger.info(f"Analyzing dataset: {dataset_key}")
                
                dataset_coverage = self._analyze_dataset_coverage(dataset_info)
                coverage_data['datasets'][dataset_key] = dataset_coverage
                
                # Update parameter availability
                for param in dataset_info['parameters']:
                    if param not in coverage_data['parameter_availability']:
                        coverage_data['parameter_availability'][param] = []
                    coverage_data['parameter_availability'][param].append(dataset_key)
            
            # Determine global vs regional coverage
            global_datasets = [k for k, v in self.key_datasets.items() 
                             if v.get('coverage', {}).get('global', False)]
            regional_datasets = [k for k, v in self.key_datasets.items() 
                               if not v.get('coverage', {}).get('global', False)]
            
            coverage_data['global_coverage'] = {
                'available': len(global_datasets) > 0,
                'datasets': global_datasets,
                'spatial_bounds': self.coverage_info['spatial_bounds'],
                'parameters': list(set(param for dataset in global_datasets 
                                     for param in self.key_datasets[dataset]['parameters']))
            }
            
            coverage_data['regional_coverage'] = {
                'available': len(regional_datasets) > 0,
                'datasets': regional_datasets,
                'regions': list(set(v.get('coverage', {}).get('region', 'Unknown') 
                                  for k, v in self.key_datasets.items()
                                  if not v.get('coverage', {}).get('global', False)))
            }
            
            # Temporal coverage analysis
            coverage_data['temporal_coverage'] = {
                'earliest_data': self.coverage_info['temporal_bounds']['start'],
                'latest_data': self.coverage_info['temporal_bounds']['end'],
                'real_time_availability': True,
                'real_time_lag': self.coverage_info['temporal_bounds']['real_time_lag'],
                'historical_archive': True,
                'climate_time_series': True
            }
            
            # Access methods
            coverage_data['access_methods'] = [
                {
                    'method': 'Direct API Subset',
                    'description': 'Direct coordinate-based data retrieval without downloads',
                    'endpoint': self.subset_url,
                    'formats': ['netcdf', 'json', 'csv'],
                    'recommended': True
                },
                {
                    'method': 'Ocean Climate Portal',
                    'description': 'Pre-calculated climate indicators and trends',
                    'endpoint': self.climate_portal_url,
                    'formats': ['web_interface', 'downloadable_reports'],
                    'recommended': True
                },
                {
                    'method': 'OPeNDAP',
                    'description': 'Direct access to data arrays',
                    'formats': ['netcdf', 'binary'],
                    'recommended': False
                }
            ]
            
            # Update internal coverage info
            self.coverage_info['last_updated'] = datetime.now().isoformat()
            
            self.logger.info("Coverage discovery completed successfully")
            self.logger.info(f"Found {len(coverage_data['datasets'])} datasets")
            self.logger.info(f"Available parameters: {len(coverage_data['parameter_availability'])}")
            
            return coverage_data
            
        except Exception as e:
            self.logger.error(f"Coverage discovery failed: {e}")
            coverage_data['error'] = str(e)
            coverage_data['status'] = 'failed'
            return coverage_data
    
    def _analyze_dataset_coverage(self, dataset_info: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze coverage for a specific dataset."""
        
        coverage = {
            'dataset_id': dataset_info['dataset_id'],
            'name': dataset_info['name'],
            'parameters': dataset_info['parameters'],
            'spatial_resolution': dataset_info['spatial_resolution'],
            'temporal_resolution': dataset_info['temporal_resolution'],
            'coverage_type': 'global' if dataset_info.get('coverage', {}).get('global') else 'regional',
            'estimated_spatial_bounds': self.coverage_info['spatial_bounds'],
            'estimated_temporal_bounds': self.coverage_info['temporal_bounds'],
            'access_tested': False,
            'sample_query_possible': True
        }
        
        # Add region-specific bounds for regional datasets
        if not dataset_info.get('coverage', {}).get('global'):
            region = dataset_info.get('coverage', {}).get('region', 'Unknown')
            if region == 'Arctic':
                coverage['estimated_spatial_bounds'] = {
                    'lat_min': 60, 'lat_max': 90,
                    'lon_min': -180, 'lon_max': 180
                }
            elif region == 'Antarctic':
                coverage['estimated_spatial_bounds'] = {
                    'lat_min': -90, 'lat_max': -60,
                    'lon_min': -180, 'lon_max': 180
                }
        
        return coverage
    
    def get_available_datasets(self) -> List[Dict[str, Any]]:
        """
        Get list of available datasets from Copernicus Marine Service.
        
        Returns:
            List of dataset information dictionaries
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
                'api_name': self.api_name,
                'recommended_for': self._get_dataset_recommendations(dataset_key)
            })
        
        return datasets
    
    def _get_dataset_recommendations(self, dataset_key: str) -> List[str]:
        """Get recommendations for what this dataset is best used for."""
        
        recommendations = {
            'sst_global_l4': ['temperature_heat', 'marine_heatwaves', 'climate_trends'],
            'sea_level_global': ['sea_level_dynamics', 'extreme_events', 'coastal_impacts'],
            'ocean_heat_content': ['temperature_heat', 'climate_trends', 'ocean_energy'],
            'biogeochemistry_global': ['ocean_chemistry', 'biological_ecosystem', 'acidification'],
            'currents_global': ['sea_level_dynamics', 'ocean_circulation', 'transport'],
            'sea_ice_arctic': ['cryosphere_ice', 'extreme_events', 'polar_climate'],
            'sea_ice_antarctic': ['cryosphere_ice', 'extreme_events', 'polar_climate']
        }
        
        return recommendations.get(dataset_key, ['general_oceanography'])
    
    def query_data(self, lat: float, lon: float, start_date: str, end_date: str,
                  parameters: List[str] = None, dataset_key: str = None) -> Dict[str, Any]:
        """
        Query data from Copernicus Marine Service for specific location and time.
        
        Args:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            parameters: List of parameters to retrieve
            dataset_key: Specific dataset to query (optional)
            
        Returns:
            Dictionary with query results
        """
        self.logger.info(f"Querying Copernicus data for {lat:.4f}, {lon:.4f} from {start_date} to {end_date}")
        
        # Validate inputs
        if not self.validate_coordinates(lat, lon):
            raise ValueError(f"Invalid coordinates: {lat}, {lon}")
        
        if not self.validate_time_range(start_date, end_date):
            raise ValueError(f"Invalid time range: {start_date} to {end_date}")
        
        # Determine which dataset to use
        if dataset_key and dataset_key not in self.key_datasets:
            raise ValueError(f"Unknown dataset: {dataset_key}")
        
        if not dataset_key:
            # Default to SST dataset for demonstration
            dataset_key = 'sst_global_l4'
        
        dataset_info = self.key_datasets[dataset_key]
        
        # For now, return simulated data structure since actual API requires authentication
        # In production, this would make actual API calls using copernicus marine toolbox
        query_result = {
            'api_name': self.api_name,
            'dataset_key': dataset_key,
            'dataset_id': dataset_info['dataset_id'],
            'query_parameters': {
                'latitude': lat,
                'longitude': lon,
                'start_date': start_date,
                'end_date': end_date,
                'parameters': parameters or dataset_info['parameters']
            },
            'spatial_resolution': dataset_info['spatial_resolution'],
            'temporal_resolution': dataset_info['temporal_resolution'],
            'data_points_expected': self._estimate_data_points(start_date, end_date, dataset_info),
            'access_method': 'API_subset',
            'status': 'simulated',  # Would be 'success' with real API
            'message': 'Simulated response - requires Copernicus Marine authentication for real data',
            'sample_data_structure': self._generate_sample_data_structure(dataset_info, parameters),
            'next_steps': [
                'Register at https://data.marine.copernicus.eu',
                'Install copernicus-marine-toolbox: pip install copernicusmarine',
                'Authenticate and run actual subset queries'
            ]
        }
        
        return query_result
    
    def _estimate_data_points(self, start_date: str, end_date: str, dataset_info: Dict[str, Any]) -> int:
        """Estimate number of data points for a query."""
        
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        days = (end_dt - start_dt).days + 1
        
        if dataset_info['temporal_resolution'] == 'daily':
            return days
        elif dataset_info['temporal_resolution'] == 'monthly':
            return days // 30
        else:
            return days  # Default to daily
    
    def _generate_sample_data_structure(self, dataset_info: Dict[str, Any], 
                                      parameters: List[str] = None) -> Dict[str, Any]:
        """Generate sample data structure for demonstration."""
        
        params_to_use = parameters or dataset_info['parameters']
        
        sample_structure = {
            'coordinates': {
                'latitude': 'float64',
                'longitude': 'float64', 
                'time': 'datetime64[ns]'
            },
            'data_variables': {},
            'attributes': {
                'source': dataset_info['name'],
                'spatial_resolution': dataset_info['spatial_resolution'],
                'temporal_resolution': dataset_info['temporal_resolution']
            }
        }
        
        # Add parameter-specific data structures
        for param in params_to_use:
            sample_structure['data_variables'][param] = {
                'dimensions': ['time', 'latitude', 'longitude'],
                'dtype': 'float32',
                'units': self._get_parameter_units(param),
                'long_name': self._get_parameter_description(param)
            }
        
        return sample_structure
    
    def _get_parameter_units(self, parameter: str) -> str:
        """Get units for a parameter."""
        
        units_map = {
            'analysed_sst': 'degrees_C',
            'sst_anomaly': 'degrees_C',
            'adt': 'meters',
            'sla': 'meters',
            'ugos': 'm/s',
            'vgos': 'm/s',
            'chl': 'mg/m^3',
            'ph': 'pH_units',
            'o2': 'mmol/m^3',
            'no3': 'mmol/m^3',
            'po4': 'mmol/m^3',
            'uo': 'm/s',
            'vo': 'm/s',
            'thetao': 'degrees_C',
            'so': 'PSU',
            'sea_ice_concentration': 'percent',
            'sea_ice_thickness': 'meters'
        }
        
        return units_map.get(parameter, 'unknown')
    
    def _get_parameter_description(self, parameter: str) -> str:
        """Get description for a parameter."""
        
        descriptions_map = {
            'analysed_sst': 'Sea Surface Temperature',
            'sst_anomaly': 'Sea Surface Temperature Anomaly',
            'adt': 'Absolute Dynamic Topography',
            'sla': 'Sea Level Anomaly',
            'ugos': 'Geostrophic Current U-component',
            'vgos': 'Geostrophic Current V-component',
            'chl': 'Chlorophyll-a Concentration',
            'ph': 'pH of Seawater',
            'o2': 'Dissolved Oxygen',
            'no3': 'Nitrate Concentration',
            'po4': 'Phosphate Concentration',
            'uo': 'Ocean Current U-component',
            'vo': 'Ocean Current V-component',
            'thetao': 'Ocean Temperature',
            'so': 'Ocean Salinity',
            'sea_ice_concentration': 'Sea Ice Concentration',
            'sea_ice_thickness': 'Sea Ice Thickness'
        }
        
        return descriptions_map.get(parameter, f'Parameter: {parameter}')
    
    def get_climate_indicators(self) -> Dict[str, Any]:
        """
        Get pre-calculated climate indicators from Ocean Climate Portal.
        
        Returns:
            Dictionary with available climate indicators
        """
        
        climate_indicators = {
            'api_name': self.api_name,
            'source': 'Ocean Climate Portal',
            'url': self.climate_portal_url,
            'available_indicators': {
                'ocean_monitoring_indicators': {
                    'description': 'Pre-calculated Ocean Monitoring Indicators (OMIs)',
                    'indicators': [
                        'global_mean_sea_level',
                        'global_mean_sst',
                        'ocean_heat_content_global',
                        'arctic_sea_ice_extent',
                        'antarctic_sea_ice_extent',
                        'atlantic_meridional_overturning_circulation'
                    ]
                },
                'regional_indicators': {
                    'description': 'Regional climate indicators and trends',
                    'regions': ['Arctic', 'North Atlantic', 'Mediterranean', 'Baltic Sea']
                },
                'extreme_events': {
                    'description': 'Marine heatwave and extreme event indicators',
                    'parameters': ['marine_heatwave_frequency', 'marine_heatwave_intensity']
                }
            },
            'update_frequency': 'monthly',
            'time_series_length': '1993-present',
            'access_method': 'web_portal',
            'status': 'available'
        }
        
        return climate_indicators