#!/usr/bin/env python3
"""
Ocean Currents Live Processor - Real-time OSCAR ocean current data collection.
Adapted from currents monitoring system for live API-based queries.
"""

import requests
from datetime import datetime
from typing import Optional, Dict, Any
import numpy as np

from ..utils.api_client import APIClient
from ..utils.erddap_utils import ERDDAPUtils


class OceanCurrentsProcessor:
    """Live ocean currents data collection using OSCAR ERDDAP API."""
    
    def __init__(self):
        """Initialize ocean currents processor."""
        self.api_client = APIClient()
        
        # Multiple ERDDAP endpoints to try for ocean currents data
        self.erddap_sources = [
            {
                'base_url': 'https://coastwatch.pfeg.noaa.gov/erddap/griddap',
                'datasets': [
                    {'id': 'ncepRtofsG3DFore3hrlyDiag', 'target_types': ['current_u', 'current_v']},
                    {'id': 'ncepRtofsG2DForeDailyDiag', 'target_types': ['current_u', 'current_v']},
                    {'id': 'ncepRtofsG2DNowDailyDiag', 'target_types': ['current_u', 'current_v']},
                    {'id': 'hycomGOMeDaily', 'target_types': ['current_u', 'current_v']},
                    {'id': 'oscar_vel10days', 'target_types': ['current_u', 'current_v']}
                ]
            },
            {
                'base_url': 'https://pae-paha.pacioos.hawaii.edu/erddap/griddap',
                'datasets': [
                    {'id': 'oscar_latlon_180', 'target_types': ['current_u', 'current_v']},
                    {'id': 'noaa_pfeg_1d0a_7f8c_d0b6', 'target_types': ['current_u', 'current_v']},
                    {'id': 'hawaii_soest_69ee_7d7d_74e6', 'target_types': ['current_u', 'current_v']}
                ]
            }
        ]
        
        # Simplified parameter mapping for available current data
        self.target_parameters = ['water_u', 'water_v', 'u', 'v', 'sea_water_velocity']
        
        # Parameter descriptions for ocean currents
        self.parameter_descriptions = {
            'u': 'Ocean current U-component - eastward velocity (positive = eastward flow)',
            'v': 'Ocean current V-component - northward velocity (positive = northward flow)',
            'current_speed': 'Ocean current speed - magnitude of velocity vector (m/s)',
            'current_direction': 'Ocean current direction - compass direction of flow (degrees)'
        }
        
        print("🌊 Ocean Currents Processor initialized")
        print("📡 Source: OSCAR Ocean Currents (ERDDAP)")
        print("🌍 Coverage: Global ocean surface currents")
    
    def get_ocean_currents_data(self, lat: float, lon: float, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get live ocean currents data from OSCAR.
        
        Args:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees
            date: Date string (YYYY-MM-DD), defaults to today
            
        Returns:
            Dictionary with ocean currents data and metadata
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        print(f"🌊 Fetching ocean currents data for {lat:.4f}, {lon:.4f} on {date}")
        
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
                    
                    # Find matching variable for U component
                    u_variable = ERDDAPUtils.find_matching_variable(
                        dataset_meta['variables'], ['current_u']
                    )
                    
                    if not u_variable:
                        print(f"   ⚠️ No matching U-component variable found")
                        continue
                    
                    # Try to get recent available date if current date fails
                    query_date = date
                    recent_date = ERDDAPUtils.get_recent_available_date(source['base_url'], dataset_id)
                    if recent_date and recent_date < date:
                        query_date = recent_date
                        print(f"   📅 Using recent available date: {query_date}")
                    
                    # Build query URL for both U and V components
                    # First get U component
                    query_url = ERDDAPUtils.build_query_url(
                        source['base_url'], dataset_id, u_variable, lat, lon, query_date
                    )
                    
                    # Make API request
                    headers = {'User-Agent': 'NOAA-Climate-System/1.0 (Ocean Current Research)'}
                    response = requests.get(query_url, headers=headers, timeout=30)
                    response.raise_for_status()
                    
                    # Parse response
                    currents_data = ERDDAPUtils.parse_erddap_response(response.text)
                    
                    # Try to get V component as well
                    v_variable = ERDDAPUtils.find_matching_variable(
                        dataset_meta['variables'], ['current_v']
                    )
                    
                    if v_variable and u_variable != v_variable:
                        try:
                            v_query_url = ERDDAPUtils.build_query_url(
                                source['base_url'], dataset_id, v_variable, lat, lon, query_date
                            )
                            v_response = requests.get(v_query_url, headers=headers, timeout=30)
                            v_response.raise_for_status()
                            v_data = ERDDAPUtils.parse_erddap_response(v_response.text)
                            currents_data.update(v_data)
                        except:
                            pass
                    
                    if currents_data:  # If we got some data
                        # Convert to expected format
                        formatted_data = {}
                        for key, value in currents_data.items():
                            if key not in ['time', 'latitude', 'longitude']:
                                # Map common variable names to standard u/v
                                if 'water_u' in key or key == 'u' or 'eastward' in key.lower():
                                    std_key = 'u'
                                elif 'water_v' in key or key == 'v' or 'northward' in key.lower():
                                    std_key = 'v'
                                else:
                                    std_key = key
                                    
                                formatted_data[std_key] = {
                                    'value': value,
                                    'units': 'm/s',
                                    'description': self.parameter_descriptions.get(
                                        std_key, f'{key} from {dataset_id}'
                                    )
                                }
                        
                        # Add metadata
                        formatted_data['metadata'] = {
                            'source': 'NOAA/ERDDAP',
                            'dataset': dataset_id,
                            'variables_queried': [u_variable, v_variable] if v_variable else [u_variable],
                            'coordinates': {'lat': lat, 'lon': lon},
                            'date': query_date,
                            'query_timestamp': datetime.now().isoformat(),
                            'data_quality': 'model_analysis',
                            'spatial_resolution': 'variable'
                        }
                        
                        # Calculate derived current properties
                        formatted_data['current_analysis'] = self._analyze_current_properties(formatted_data)
                        
                        print("✅ Ocean currents data retrieved")
                        return formatted_data
                        
                except Exception as e:
                    print(f"⚠️ {dataset_id} failed: {e}")
                    continue
        
        # If all sources fail, return fallback
        print("⚠️ All ocean currents sources failed, generating fallback estimates")
        return self._generate_fallback_currents_data(lat, lon, date)
    
    
    
    def _analyze_current_properties(self, currents_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate derived current properties from U/V components.
        """
        analysis = {
            'current_speed': None,
            'current_direction': None,
            'flow_regime': 'unknown',
            'current_strength': 'unknown'
        }
        
        try:
            # Get U and V components
            u_component = currents_data.get('u', {}).get('value')
            v_component = currents_data.get('v', {}).get('value')
            
            if u_component is not None and v_component is not None:
                # Calculate speed (magnitude)
                speed = np.sqrt(u_component**2 + v_component**2)
                analysis['current_speed'] = speed
                
                # Calculate direction (oceanographic convention: direction TO which current flows)
                direction_rad = np.arctan2(v_component, u_component)
                direction_deg = np.degrees(direction_rad)
                
                # Convert to compass heading (0-360°)
                if direction_deg < 0:
                    direction_deg += 360
                    
                analysis['current_direction'] = direction_deg
                
                # Classify current strength
                if speed < 0.05:
                    analysis['current_strength'] = 'very_weak'
                elif speed < 0.15:
                    analysis['current_strength'] = 'weak'
                elif speed < 0.30:
                    analysis['current_strength'] = 'moderate'
                elif speed < 0.50:
                    analysis['current_strength'] = 'strong'
                else:
                    analysis['current_strength'] = 'very_strong'
                
                # Basic flow regime classification
                if speed < 0.10:
                    analysis['flow_regime'] = 'sluggish'
                elif speed < 0.25:
                    analysis['flow_regime'] = 'typical'
                else:
                    analysis['flow_regime'] = 'energetic'
                
        except Exception as e:
            print(f"⚠️ Current analysis failed: {e}")
            
        return analysis
    
    def _generate_fallback_currents_data(self, lat: float, lon: float, date: str) -> Dict[str, Any]:
        """
        Generate fallback ocean currents estimates when API fails.
        Based on typical ocean circulation patterns.
        """
        print("🔄 Generating fallback ocean currents estimates...")
        
        # Estimate currents based on latitude and ocean basin
        abs_lat = abs(lat)
        
        # Basic ocean circulation patterns
        if abs_lat < 10:  # Equatorial region
            # Equatorial current systems - typically westward
            base_speed = np.random.uniform(0.1, 0.4)
            base_direction = 270 + np.random.uniform(-30, 30)  # Generally westward
            flow_type = "equatorial"
            
        elif abs_lat < 30:  # Subtropical region  
            # Subtropical gyres - variable directions
            base_speed = np.random.uniform(0.05, 0.25)
            base_direction = np.random.uniform(0, 360)  # More variable
            flow_type = "subtropical_gyre"
            
        elif abs_lat < 60:  # Mid-latitude
            # Westerly-driven currents
            base_speed = np.random.uniform(0.08, 0.30)
            base_direction = 90 + np.random.uniform(-45, 45)  # Generally eastward
            flow_type = "mid_latitude"
            
        else:  # Polar region
            # Weaker, variable currents
            base_speed = np.random.uniform(0.02, 0.15)
            base_direction = np.random.uniform(0, 360)
            flow_type = "polar"
        
        # Convert speed and direction to U/V components
        direction_rad = np.radians(base_direction)
        u_component = base_speed * np.cos(direction_rad)
        v_component = base_speed * np.sin(direction_rad)
        
        fallback_data = {
            'u': {
                'value': u_component,
                'units': 'm/s',
                'description': self.parameter_descriptions['u']
            },
            'v': {
                'value': v_component,
                'units': 'm/s',
                'description': self.parameter_descriptions['v']
            },
            'metadata': {
                'source': 'Fallback_Estimate',
                'flow_type': flow_type,
                'coordinates': {'lat': lat, 'lon': lon},
                'date': date,
                'confidence': 0.4,
                'note': 'Estimated values based on typical circulation patterns'
            },
            'current_analysis': {
                'current_speed': base_speed,
                'current_direction': base_direction,
                'flow_regime': 'estimated',
                'current_strength': 'estimated'
            }
        }
        
        print(f"🌊 Applied currents fallback ({flow_type}: {base_speed:.2f} m/s @ {base_direction:.0f}°)")
        return fallback_data
    
    def close(self):
        """Clean up resources."""
        self.api_client.close()