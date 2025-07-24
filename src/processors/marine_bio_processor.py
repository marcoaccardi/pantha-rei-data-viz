#!/usr/bin/env python3
"""
Marine Biogeochemistry Live Processor - Real-time marine biogeochemical data collection.
Adapted from Copernicus marine biogeochemistry system for live API-based queries.
Uses standardized WGS84 coordinate validation and ERDDAP formatting.
"""

import requests
from datetime import datetime
from typing import Optional, Dict, Any
import numpy as np

from ..utils.api_client import APIClient
from ..utils.erddap_utils import ERDDAPUtils
from .base_processor import OceanDataProcessor


class MarineBiogeochemistryProcessor(OceanDataProcessor):
    """Live marine biogeochemistry data collection using Copernicus/ERDDAP APIs."""
    
    def __init__(self):
        """Initialize marine biogeochemistry processor with WGS84 coordinate validation."""
        super().__init__()  # Initialize coordinate validation
        self.api_client = APIClient()
        
        # Multiple potential data sources for marine biogeochemistry
        self.data_sources = [
            {
                'name': 'NOAA_CoastWatch',
                'base_url': 'https://coastwatch.pfeg.noaa.gov/erddap/griddap',
                'datasets': [
                    {'id': 'erdMBchla8day', 'target_types': ['chlorophyll']},
                    {'id': 'erdMH1chla8day', 'target_types': ['chlorophyll']},
                    {'id': 'nesdisVHNSQchlaMonthly', 'target_types': ['chlorophyll']},
                    {'id': 'erdMBsstd8day', 'target_types': ['temperature']}
                ]
            },
            {
                'name': 'PacIOOS_Marine',
                'base_url': 'https://pae-paha.pacioos.hawaii.edu/erddap/griddap',
                'datasets': [
                    {'id': 'esa-cci-chla-monthly-v6-0', 'target_types': ['chlorophyll']},
                    {'id': 'hawaii_soest_2ee3_8f5a_299d', 'target_types': ['chlorophyll']},
                    {'id': 'noaa_pfeg_e9ae_3356_22f8', 'target_types': ['chlorophyll']}
                ]
            }
        ]
        
        # Simplified parameter mapping for available biogeochemical data
        self.target_parameters = ['chlorophyll', 'chl', 'chla', 'sea_surface_temperature', 'sst']
        
        # Parameter descriptions for marine biogeochemistry
        self.parameter_descriptions = {
            'spco2': 'Surface partial pressure of CO2 - measure of ocean CO2 saturation (μatm)',
            'o2': 'Dissolved oxygen concentration - critical for marine life (mmol/m³)',
            'chl': 'Chlorophyll-a concentration - phytoplankton biomass indicator (mg/m³)',
            'no3': 'Nitrate concentration - key marine nutrient for primary productivity (mmol/m³)',
            'po4': 'Phosphate concentration - essential marine nutrient (mmol/m³)',
            'phyc': 'Phytoplankton carbon biomass - measure of marine primary producers (mg/m³)',
            'si': 'Silicate concentration - nutrient important for diatoms (mmol/m³)',
            'ph': 'Ocean pH - measure of ocean acidification affecting marine ecosystems',
            'talk': 'Total alkalinity - ocean buffering capacity against acidification (mmol/m³)',
            'nppv': 'Net primary productivity - rate of organic carbon production (mgC/m³/day)',
            'dissic': 'Dissolved inorganic carbon - key component of ocean carbon cycle (mmol/m³)',
            'fe': 'Iron concentration - limiting nutrient in many ocean regions (mmol/m³)'
        }
        
        print("🧪 Marine Biogeochemistry Processor initialized")
        print("📡 Source: Copernicus Marine Service / ERDDAP")
        print("🌍 Coverage: Global ocean biogeochemical conditions")

    def get_processor_data(self, lat: float, lon: float, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Implementation of abstract base class method.
        Delegates to get_marine_biogeochemistry_data for backward compatibility.
        """
        return self.get_marine_biogeochemistry_data(lat, lon, date)
    
    def get_marine_biogeochemistry_data(self, lat: float, lon: float, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get live marine biogeochemistry data with WGS84 coordinate validation.
        
        Args:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees
            date: Date string (YYYY-MM-DD), defaults to today
            
        Returns:
            Dictionary with marine biogeochemistry data and standardized metadata
        """
        # Validate and normalize coordinates using base class
        normalized_lat, normalized_lon = self.get_normalized_coordinates(lat, lon)
        validated_date = self.validate_date_parameter(date)
        
        # Log the request with standardized format
        self.log_coordinate_request(lat, lon, validated_date, "MarineBiogeochemistryProcessor")
        
        print(f"🧪 Fetching marine biogeochemistry data for {normalized_lat:.6f}, {normalized_lon:.6f} on {validated_date}")
        
        # Try multiple data sources and datasets
        for source in self.data_sources:
            for dataset_info in source['datasets']:
                dataset_id = dataset_info['id']
                target_types = dataset_info['target_types']
                
                try:
                    print(f"📡 Trying: {source['name']}/{dataset_id}")
                    
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
                    headers = {'User-Agent': 'NOAA-Climate-System/1.0 (Marine Biogeochemistry Research)'}
                    response = requests.get(query_url, headers=headers, timeout=30)
                    response.raise_for_status()
                    
                    # Parse response
                    bio_data = ERDDAPUtils.parse_erddap_response(response.text)
                    
                    if bio_data:  # If we got some data
                        # Convert to expected format
                        formatted_data = {}
                        for key, value in bio_data.items():
                            if key not in ['time', 'latitude', 'longitude']:
                                # Map to standard names
                                if 'chlorophyll' in key.lower() or 'chl' in key.lower():
                                    std_key = 'chl'
                                else:
                                    std_key = key
                                    
                                formatted_data[std_key] = {
                                    'value': value,
                                    'units': self._get_parameter_units_by_name(key),
                                    'description': self.parameter_descriptions.get(
                                        std_key, f'{key} from {dataset_id}'
                                    )
                                }
                        
                        # Add metadata
                        formatted_data['metadata'] = {
                            'source': source['name'],
                            'dataset': dataset_id,
                            'variable_queried': variable,
                            'coordinates': {'lat': lat, 'lon': lon},
                            'date': query_date,
                            'query_timestamp': datetime.now().isoformat(),
                            'data_quality': 'model_analysis',
                            'spatial_resolution': 'variable',
                            'temporal_resolution': 'daily'
                        }
                        
                        # Calculate marine ecosystem indicators
                        formatted_data['ecosystem_analysis'] = self._analyze_marine_ecosystem(formatted_data)
                        
                        print("✅ Marine biogeochemistry data retrieved")
                        return formatted_data
                        
                except Exception as e:
                    print(f"⚠️ {source['name']}/{dataset_id} failed: {e}")
                    continue
        
        # If all sources fail, return fallback
        print("⚠️ All biogeochemistry sources failed, generating fallback estimates")
        return self._generate_fallback_bio_data(lat, lon, date)
    
    
    
    def _get_parameter_units(self, parameter: str) -> str:
        """Get units for biogeochemical parameters."""
        units_map = {
            'spco2': 'μatm',
            'o2': 'mmol/m³',
            'chl': 'mg/m³',
            'no3': 'mmol/m³',
            'po4': 'mmol/m³',
            'phyc': 'mg/m³',
            'si': 'mmol/m³',
            'ph': 'pH_units',
            'talk': 'mmol/m³',
            'nppv': 'mgC/m³/day',
            'dissic': 'mmol/m³',
            'fe': 'mmol/m³'
        }
        return units_map.get(parameter, 'unknown')
    
    def _get_parameter_units_by_name(self, parameter: str) -> str:
        """Get units for parameter by name."""
        if 'chl' in parameter.lower() or 'chlorophyll' in parameter.lower():
            return 'mg/m³'
        elif 'temperature' in parameter.lower() or 'sst' in parameter.lower():
            return '°C'
        elif 'ph' in parameter.lower():
            return 'pH_units'
        elif 'o2' in parameter.lower() or 'oxygen' in parameter.lower():
            return 'mmol/m³'
        else:
            return 'unknown'
    
    def _analyze_marine_ecosystem(self, bio_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze marine ecosystem health and productivity indicators.
        """
        analysis = {
            'productivity_level': 'unknown',
            'acidification_status': 'unknown',
            'oxygen_status': 'unknown',
            'nutrient_status': 'unknown',
            'ecosystem_health': 'unknown'
        }
        
        try:
            # Analyze chlorophyll (productivity indicator)
            chl = bio_data.get('chl', {}).get('value')
            if chl is not None:
                if chl < 0.1:
                    analysis['productivity_level'] = 'oligotrophic'  # Low productivity
                elif chl < 1.0:
                    analysis['productivity_level'] = 'mesotrophic'  # Moderate productivity
                elif chl < 10.0:
                    analysis['productivity_level'] = 'eutrophic'   # High productivity
                else:
                    analysis['productivity_level'] = 'hypereutrophic'  # Very high
            
            # Analyze ocean pH (acidification)
            ph = bio_data.get('ph', {}).get('value')
            if ph is not None:
                if ph > 8.2:
                    analysis['acidification_status'] = 'normal'
                elif ph > 8.0:
                    analysis['acidification_status'] = 'slight_acidification'
                elif ph > 7.8:
                    analysis['acidification_status'] = 'moderate_acidification'
                else:
                    analysis['acidification_status'] = 'severe_acidification'
            
            # Analyze dissolved oxygen
            o2 = bio_data.get('o2', {}).get('value')
            if o2 is not None:
                if o2 > 200:
                    analysis['oxygen_status'] = 'well_oxygenated'
                elif o2 > 100:
                    analysis['oxygen_status'] = 'moderate_oxygen'
                elif o2 > 50:
                    analysis['oxygen_status'] = 'low_oxygen'
                else:
                    analysis['oxygen_status'] = 'hypoxic'
            
            # Analyze nutrients (nitrate as proxy)
            no3 = bio_data.get('no3', {}).get('value')
            if no3 is not None:
                if no3 < 1:
                    analysis['nutrient_status'] = 'nutrient_limited'
                elif no3 < 10:
                    analysis['nutrient_status'] = 'moderate_nutrients'
                else:
                    analysis['nutrient_status'] = 'nutrient_rich'
            
            # Overall ecosystem health assessment
            health_indicators = []
            if analysis['productivity_level'] in ['mesotrophic', 'eutrophic']:
                health_indicators.append('productive')
            if analysis['acidification_status'] in ['normal', 'slight_acidification']:
                health_indicators.append('stable_chemistry')
            if analysis['oxygen_status'] in ['well_oxygenated', 'moderate_oxygen']:
                health_indicators.append('adequate_oxygen')
            
            if len(health_indicators) >= 2:
                analysis['ecosystem_health'] = 'healthy'
            elif len(health_indicators) >= 1:
                analysis['ecosystem_health'] = 'stressed'
            else:
                analysis['ecosystem_health'] = 'degraded'
                
        except Exception as e:
            print(f"⚠️ Ecosystem analysis failed: {e}")
            
        return analysis
    
    def _generate_fallback_bio_data(self, lat: float, lon: float, date: str) -> Dict[str, Any]:
        """
        Generate fallback marine biogeochemistry estimates when APIs fail.
        """
        print("🔄 Generating fallback marine biogeochemistry estimates...")
        
        # Generate estimates based on latitude (ocean productivity patterns)
        abs_lat = abs(lat)
        
        # Different biogeochemical conditions by latitude
        if abs_lat < 10:  # Tropical - oligotrophic
            chl_base = np.random.uniform(0.05, 0.2)   # Low chlorophyll
            no3_base = np.random.uniform(0.1, 2.0)    # Low nitrate
            o2_base = np.random.uniform(180, 220)     # Normal oxygen
            ph_base = np.random.uniform(8.0, 8.2)     # Normal pH
            productivity_type = "oligotrophic"
            
        elif abs_lat < 30:  # Subtropical - variable
            chl_base = np.random.uniform(0.1, 0.5)
            no3_base = np.random.uniform(0.5, 5.0)
            o2_base = np.random.uniform(160, 200)
            ph_base = np.random.uniform(7.9, 8.1)
            productivity_type = "mesotrophic"
            
        elif abs_lat < 50:  # Temperate - productive
            chl_base = np.random.uniform(0.3, 2.0)
            no3_base = np.random.uniform(2.0, 15.0)
            o2_base = np.random.uniform(200, 250)
            ph_base = np.random.uniform(7.8, 8.1)
            productivity_type = "eutrophic"
            
        else:  # Polar - highly variable
            chl_base = np.random.uniform(0.1, 5.0)    # Seasonal extremes
            no3_base = np.random.uniform(5.0, 25.0)   # High nutrients
            o2_base = np.random.uniform(220, 280)     # High oxygen
            ph_base = np.random.uniform(7.9, 8.2)
            productivity_type = "polar"
        
        # Generate other parameters based on these base values
        fallback_data = {
            'chl': {
                'value': chl_base,
                'units': 'mg/m³',
                'description': self.parameter_descriptions['chl']
            },
            'no3': {
                'value': no3_base,
                'units': 'mmol/m³',
                'description': self.parameter_descriptions['no3']
            },
            'o2': {
                'value': o2_base,
                'units': 'mmol/m³',
                'description': self.parameter_descriptions['o2']
            },
            'ph': {
                'value': ph_base,
                'units': 'pH_units',
                'description': self.parameter_descriptions['ph']
            },
            'po4': {
                'value': no3_base * 0.066,  # Redfield ratio approximation
                'units': 'mmol/m³',
                'description': self.parameter_descriptions['po4']
            },
            'si': {
                'value': no3_base * 0.5,    # Approximate Si:N ratio
                'units': 'mmol/m³',
                'description': self.parameter_descriptions['si']
            },
            'spco2': {
                'value': np.random.uniform(350, 450),  # Typical oceanic pCO2
                'units': 'μatm',
                'description': self.parameter_descriptions['spco2']
            },
            'metadata': {
                'source': 'Fallback_Estimate',
                'productivity_type': productivity_type,
                'coordinates': {'lat': lat, 'lon': lon},
                'date': date,
                'confidence': 0.3,
                'note': 'Estimated values based on typical biogeochemical patterns'
            },
            'ecosystem_analysis': self._analyze_marine_ecosystem({
                'chl': {'value': chl_base},
                'no3': {'value': no3_base},
                'o2': {'value': o2_base},
                'ph': {'value': ph_base}
            })
        }
        
        print(f"🧪 Applied biogeochemistry fallback ({productivity_type}: chl={chl_base:.2f} mg/m³)")
        return fallback_data
    
    def close(self):
        """Clean up resources."""
        self.api_client.close()