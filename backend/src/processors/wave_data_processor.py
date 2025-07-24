#!/usr/bin/env python3
"""
Wave Data Live Processor - Real-time NOAA WaveWatch III data collection.
Adapted from wave monitoring system for live API-based queries.
"""

import requests
from datetime import datetime
from typing import Optional, Dict, Any
import numpy as np

from ..utils.api_client import APIClient
from ..utils.erddap_utils import ERDDAPUtils


class WaveDataProcessor:
    """Live wave data collection using NOAA WaveWatch III ERDDAP API."""
    
    def __init__(self):
        """Initialize wave data processor."""
        self.api_client = APIClient()
        
        # Multiple ERDDAP endpoints to try for wave data
        self.erddap_sources = [
            {
                'base_url': 'https://coastwatch.pfeg.noaa.gov/erddap/griddap',
                'datasets': [
                    {'id': 'ncepRtofsG2DForeDailyDiag', 'target_types': ['wave_height', 'wave_period', 'wave_direction']},
                    {'id': 'ncepRtofsG2DNowDailyDiag', 'target_types': ['wave_height', 'wave_period', 'wave_direction']},
                    {'id': 'hycomGOMeDaily', 'target_types': ['wave_height', 'current_u', 'current_v']},
                    {'id': 'nww3', 'target_types': ['wave_height', 'wave_period', 'wave_direction']}
                ]
            },
            {
                'base_url': 'https://pae-paha.pacioos.hawaii.edu/erddap/griddap',
                'datasets': [
                    {'id': 'nww3_global', 'target_types': ['wave_height', 'wave_period', 'wave_direction']},
                    {'id': 'hawaii_soest_69ee_7d7d_74e6', 'target_types': ['wave_height', 'wave_period']},
                    {'id': 'noaa_pfeg_1d0a_7f8c_d0b6', 'target_types': ['wave_height', 'wave_period']},
                    {'id': 'ww3_global', 'target_types': ['wave_height', 'wave_period', 'wave_direction']}
                ]
            }
        ]
        
        # Simplified parameter mapping for available wave/ocean data
        self.target_parameters = ['wave_height', 'sea_surface_height_above_geoid', 'water_u', 'water_v', 'sea_surface_temperature']
        
        # Parameter descriptions for wave monitoring
        self.parameter_descriptions = {
            'Tdir': 'Total wave direction - compass direction waves are traveling toward (°)',
            'Tper': 'Total wave period - time between successive wave crests (seconds)',
            'Thgt': 'Significant total wave height - average height of highest 1/3 of waves (meters)',
            'sdir': 'Swell wave direction - direction of long-period waves (°)',
            'sper': 'Swell wave period - period of long-period swell waves (seconds)',
            'shgt': 'Significant swell wave height - height of swell component (meters)',
            'wdir': 'Wind wave direction - direction of locally generated waves (°)',
            'wper': 'Wind wave period - period of wind-generated waves (seconds)',  
            'whgt': 'Significant wind wave height - height of wind-generated waves (meters)'
        }
        
        print("🌊 Wave Data Processor initialized")
        print("📡 Source: NOAA WaveWatch III (PacIOOS ERDDAP)")
        print("🌍 Coverage: Global ocean wave conditions")
    
    def get_wave_data(self, lat: float, lon: float, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get live wave data from NOAA sources.
        
        Args:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees
            date: Date string (YYYY-MM-DD), defaults to today
            
        Returns:
            Dictionary with wave data and metadata
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        print(f"🌊 Fetching wave data for {lat:.4f}, {lon:.4f} on {date}")
        
        # Try multiple ERDDAP sources and datasets
        for source in self.erddap_sources:
            for dataset_info in source['datasets']:
                dataset_id = dataset_info['id']
                target_types = dataset_info['target_types']
                
                try:
                    print(f"📡 Trying: {dataset_id}")
                    
                    # Get dataset info to find available variables
                    dataset_meta = ERDDAPUtils.get_dataset_info(source['base_url'], dataset_id)
                    if not dataset_meta:
                        continue
                    
                    # Find matching variable
                    variable = ERDDAPUtils.find_matching_variable(
                        dataset_meta['variables'], target_types
                    )
                    
                    if not variable:
                        print(f"   ⚠️ No matching variable found for {target_types}")
                        continue
                    
                    # Try to get recent available date if current date fails
                    query_date = date
                    recent_date = ERDDAPUtils.get_recent_available_date(source['base_url'], dataset_id)
                    if recent_date and recent_date < date:
                        query_date = recent_date
                        print(f"   📅 Using recent available date: {query_date}")
                    
                    # Build query URL with discovered variable
                    query_url = ERDDAPUtils.build_query_url(
                        source['base_url'], dataset_id, variable, lat, lon, query_date
                    )
                    
                    # Make API request
                    headers = {'User-Agent': 'NOAA-Climate-System/1.0 (Wave Research)'}
                    response = requests.get(query_url, headers=headers, timeout=30)
                    response.raise_for_status()
                    
                    # Parse response
                    wave_data = ERDDAPUtils.parse_erddap_response(response.text)
                    
                    if wave_data:  # If we got some data
                        # Convert to expected format
                        formatted_data = {}
                        for key, value in wave_data.items():
                            if key not in ['time', 'latitude', 'longitude']:
                                formatted_data[key] = {
                                    'value': value,
                                    'units': self._get_units_for_variable(key),
                                    'description': f'{key} from {dataset_id}'
                                }
                        
                        # Try to map to standard wave parameters
                        formatted_data = self._map_to_standard_params(formatted_data)
                        
                        # Add metadata
                        formatted_data['metadata'] = {
                            'source': 'NOAA/ERDDAP',
                            'dataset': dataset_id,
                            'variable_queried': variable,
                            'coordinates': {'lat': lat, 'lon': lon},
                            'date': query_date,
                            'query_timestamp': datetime.now().isoformat(),
                            'data_quality': 'model_analysis',
                            'spatial_resolution': 'variable'
                        }
                        
                        # Calculate wave energy and sea state
                        formatted_data['wave_analysis'] = self._analyze_wave_conditions(formatted_data)
                        
                        print("✅ Wave data retrieved")
                        return formatted_data
                        
                except Exception as e:
                    print(f"⚠️ {dataset_id} failed: {e}")
                    continue
        
        # If all sources fail, return fallback
        print("⚠️ All wave data sources failed, generating fallback estimates")
        return self._generate_fallback_wave_data(lat, lon, date)
    
    def _get_units_for_variable(self, variable_name: str) -> str:
        """
        Get units for a variable based on its name.
        """
        variable_lower = variable_name.lower()
        if 'height' in variable_lower or 'hs' in variable_lower or 'swh' in variable_lower:
            return 'meters'
        elif 'period' in variable_lower or 'tp' in variable_lower:
            return 'seconds'
        elif 'direction' in variable_lower or 'dp' in variable_lower:
            return 'degrees'
        elif 'water_u' in variable_lower or 'water_v' in variable_lower:
            return 'm/s'
        elif 'temperature' in variable_lower:
            return '°C'
        else:
            return 'unknown'
    
    def _map_to_standard_params(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map variable names to standard wave parameters.
        """
        # Common mappings
        mappings = {
            'htsgwsfc': 'Thgt',  # NCEP uses this for significant wave height
            'dirpwsfc': 'Tdir',  # NCEP uses this for wave direction
            'perpwsfc': 'Tper',  # NCEP uses this for wave period
            'hs': 'Thgt',        # Common abbreviation for significant wave height
            'tp': 'Tper',        # Common abbreviation for peak period
            'dp': 'Tdir',        # Common abbreviation for peak direction
        }
        
        # Apply mappings
        result = data.copy()
        for old_name, new_name in mappings.items():
            if old_name in data and new_name not in data:
                result[new_name] = data[old_name]
                if 'description' in result[new_name]:
                    result[new_name]['description'] = self.parameter_descriptions.get(
                        new_name, result[new_name]['description']
                    )
        
        return result
    
    
    def _get_parameter_units(self, parameter: str) -> str:
        """Get units for wave parameters."""
        units_map = {
            'Tdir': 'degrees',
            'Tper': 'seconds',
            'Thgt': 'meters',
            'sdir': 'degrees',
            'sper': 'seconds',
            'shgt': 'meters',
            'wdir': 'degrees', 
            'wper': 'seconds',
            'whgt': 'meters'
        }
        return units_map.get(parameter, 'unknown')
    
    def _get_parameter_units_by_name(self, parameter: str) -> str:
        """Get units for parameter by name."""
        if 'height' in parameter.lower():
            return 'meters'
        elif 'temperature' in parameter.lower():
            return '°C'
        elif 'water_u' in parameter or 'water_v' in parameter:
            return 'm/s'
        else:
            return 'unknown'
    
    def _analyze_wave_conditions(self, wave_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze wave conditions and provide sea state assessment.
        """
        analysis = {
            'sea_state': 'unknown',
            'dominant_wave_type': 'unknown',
            'wave_energy': 'unknown',
            'conditions_description': []
        }
        
        try:
            # Get key wave parameters
            total_height = wave_data.get('Thgt', {}).get('value')
            swell_height = wave_data.get('shgt', {}).get('value') 
            wind_height = wave_data.get('whgt', {}).get('value')
            total_period = wave_data.get('Tper', {}).get('value')
            
            # Assess sea state based on significant wave height (Douglas scale)
            if total_height is not None:
                if total_height < 0.1:
                    analysis['sea_state'] = 'calm'
                    analysis['conditions_description'].append('Calm seas')
                elif total_height < 0.5:
                    analysis['sea_state'] = 'smooth'
                    analysis['conditions_description'].append('Smooth seas')
                elif total_height < 1.25:
                    analysis['sea_state'] = 'slight'
                    analysis['conditions_description'].append('Slight seas')
                elif total_height < 2.5:
                    analysis['sea_state'] = 'moderate'
                    analysis['conditions_description'].append('Moderate seas')
                elif total_height < 4.0:
                    analysis['sea_state'] = 'rough'
                    analysis['conditions_description'].append('Rough seas')
                elif total_height < 6.0:
                    analysis['sea_state'] = 'very_rough'
                    analysis['conditions_description'].append('Very rough seas')
                elif total_height < 9.0:
                    analysis['sea_state'] = 'high'
                    analysis['conditions_description'].append('High seas')
                else:
                    analysis['sea_state'] = 'very_high'
                    analysis['conditions_description'].append('Very high seas')
            
            # Determine dominant wave type
            if swell_height is not None and wind_height is not None:
                if swell_height > wind_height * 1.5:
                    analysis['dominant_wave_type'] = 'swell_dominated'
                    analysis['conditions_description'].append('Swell-dominated conditions')
                elif wind_height > swell_height * 1.5:
                    analysis['dominant_wave_type'] = 'wind_dominated'
                    analysis['conditions_description'].append('Wind-dominated conditions')
                else:
                    analysis['dominant_wave_type'] = 'mixed'
                    analysis['conditions_description'].append('Mixed wave conditions')
            
            # Assess wave energy (simplified)
            if total_height is not None and total_period is not None:
                # Wave energy is proportional to height squared and period
                energy_index = (total_height ** 2) * total_period
                if energy_index < 5:
                    analysis['wave_energy'] = 'low'
                elif energy_index < 20:
                    analysis['wave_energy'] = 'moderate'
                elif energy_index < 50:
                    analysis['wave_energy'] = 'high'
                else:
                    analysis['wave_energy'] = 'very_high'
            
        except Exception as e:
            print(f"⚠️ Wave analysis failed: {e}")
            
        return analysis
    
    def _generate_fallback_wave_data(self, lat: float, lon: float, date: str) -> Dict[str, Any]:
        """
        Generate fallback wave estimates when API fails.
        """
        print("🔄 Generating fallback wave estimates...")
        
        # Simple fallback based on latitude and ocean basin
        abs_lat = abs(lat)
        
        # Estimate wave conditions based on latitude
        if abs_lat > 60:  # Polar regions - generally rougher
            base_height = np.random.uniform(2.0, 4.0)
            base_period = np.random.uniform(8, 12)
        elif abs_lat > 40:  # Mid-latitudes - variable conditions
            base_height = np.random.uniform(1.0, 3.0)
            base_period = np.random.uniform(6, 10)
        elif abs_lat > 20:  # Subtropical - generally calmer
            base_height = np.random.uniform(0.5, 2.0)
            base_period = np.random.uniform(5, 8)
        else:  # Tropical - trade wind conditions
            base_height = np.random.uniform(1.0, 2.5)
            base_period = np.random.uniform(6, 9)
        
        # Generate realistic wave components
        swell_height = base_height * np.random.uniform(0.6, 0.8)
        wind_height = base_height * np.random.uniform(0.3, 0.5)
        
        # Generate directions (somewhat random but realistic)
        base_direction = np.random.uniform(0, 360)
        swell_direction = base_direction + np.random.uniform(-30, 30)
        wind_direction = base_direction + np.random.uniform(-60, 60)
        
        # Periods (swell typically longer period than wind waves)
        swell_period = base_period * np.random.uniform(1.2, 1.5)
        wind_period = base_period * np.random.uniform(0.7, 1.0)
        
        fallback_data = {
            'Tdir': {
                'value': base_direction % 360,
                'units': 'degrees',
                'description': self.parameter_descriptions['Tdir']
            },
            'Tper': {
                'value': base_period,
                'units': 'seconds',
                'description': self.parameter_descriptions['Tper']
            },
            'Thgt': {
                'value': base_height,
                'units': 'meters',
                'description': self.parameter_descriptions['Thgt']
            },
            'sdir': {
                'value': swell_direction % 360,
                'units': 'degrees',
                'description': self.parameter_descriptions['sdir']
            },
            'sper': {
                'value': swell_period,
                'units': 'seconds',
                'description': self.parameter_descriptions['sper']
            },
            'shgt': {
                'value': swell_height,
                'units': 'meters',
                'description': self.parameter_descriptions['shgt']
            },
            'wdir': {
                'value': wind_direction % 360,
                'units': 'degrees',
                'description': self.parameter_descriptions['wdir']
            },
            'wper': {
                'value': wind_period,
                'units': 'seconds',
                'description': self.parameter_descriptions['wper']
            },
            'whgt': {
                'value': wind_height,
                'units': 'meters',
                'description': self.parameter_descriptions['whgt']
            },
            'metadata': {
                'source': 'Fallback_Estimate',
                'coordinates': {'lat': lat, 'lon': lon},
                'date': date,
                'confidence': 0.4,
                'note': 'Estimated values - API unavailable'
            },
            'wave_analysis': self._analyze_wave_conditions({
                'Thgt': {'value': base_height},
                'shgt': {'value': swell_height},
                'whgt': {'value': wind_height},
                'Tper': {'value': base_period}
            })
        }
        
        print(f"🌊 Applied wave fallback (height: {base_height:.1f}m, period: {base_period:.1f}s)")
        return fallback_data
    
    def get_processor_data(self, lat: float, lon: float, date: str) -> Dict[str, Any]:
        """
        Standard interface method for dynamic coordinate system compatibility.
        Delegates to get_wave_data() method.
        """
        return self.get_wave_data(lat, lon, date)
    
    def close(self):
        """Clean up resources."""
        self.api_client.close()