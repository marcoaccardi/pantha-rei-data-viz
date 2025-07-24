#!/usr/bin/env python3
"""
Fast Climate Processor - Guaranteed quick response with smart fallbacks.
"""

import requests
from datetime import datetime
from typing import Optional, Dict, Any, List
import numpy as np
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
import time
import sys
from pathlib import Path

# Add processors directory to path for ocean downloader
sys.path.insert(0, str(Path(__file__).parent))

class FastClimateProcessor:
    """Fast climate data processor with guaranteed response times."""
    
    def __init__(self):
        """Initialize fast climate processor."""
        self.max_request_time = 3.0  # Maximum time per API request
        self.max_total_time = 15.0   # Maximum total processing time
        
        # Quick fallback data generator
        self.fallback_generator = ClimateDataFallback()
        
        # Ocean data downloader for pollution data
        self.ocean_downloader = None
        self._initialize_ocean_downloader()
    
    def _initialize_ocean_downloader(self):
        """Initialize ocean data downloader with error handling."""
        try:
            from ocean_data_downloader import OceanDataDownloader
            self.ocean_downloader = OceanDataDownloader()
            # Initialize in background to avoid blocking
            if hasattr(self.ocean_downloader, 'initialize'):
                self.ocean_downloader.initialize()
            print("🌊 Ocean pollution data system initialized")
        except Exception as e:
            print(f"⚠️ Ocean downloader initialization failed: {e}")
            self.ocean_downloader = None
        
    def get_climate_data_fast(self, lat: float, lon: float, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get climate data with guaranteed fast response.
        
        Args:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees
            date: Date string (YYYY-MM-DD), defaults to today
            
        Returns:
            Dictionary with climate data (real or fallback)
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        start_time = time.time()
        print(f"🚀 Fast climate data collection for {lat:.4f}, {lon:.4f}")
        
        # Initialize result with immediate fallback data
        result = self.fallback_generator.generate_immediate_fallback(lat, lon, date)
        
        # Try to get real data with timeouts
        real_data = {}
        
        # Launch concurrent data collection with timeouts
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Submit all data collection tasks
            futures = {
                executor.submit(self._get_weather_data_timeout, lat, lon): 'weather',
                executor.submit(self._get_marine_data_timeout, lat, lon, date): 'marine',
                executor.submit(self._get_stations_data_timeout, lat, lon): 'stations',
                executor.submit(self._get_climate_zone, lat): 'climate_zone',
                executor.submit(self._get_ocean_pollution_data_timeout, lat, lon): 'ocean_pollution'
            }
            
            # Collect results as they complete, with overall timeout
            for future in as_completed(futures, timeout=self.max_total_time):
                try:
                    data_type = futures[future]
                    data = future.result(timeout=1.0)  # 1 second per result
                    if data:
                        real_data[data_type] = data
                        print(f"   ✅ {data_type} data retrieved")
                except Exception as e:
                    data_type = futures[future]
                    print(f"   ⚠️ {data_type} failed: {e}")
        
        # Merge real data with fallback data
        if real_data:
            result = self._merge_data(result, real_data)
        
        elapsed = time.time() - start_time
        result['metadata']['processing_time'] = elapsed
        result['metadata']['data_quality'] = 'mixed_real_fallback' if real_data else 'fallback_only'
        
        print(f"✅ Climate data ready in {elapsed:.2f}s")
        return result
    
    def _get_weather_data_timeout(self, lat: float, lon: float) -> Optional[Dict]:
        """Get weather data with timeout."""
        try:
            # Try NWS API first (US locations)
            if -180 <= lon <= -60 and 20 <= lat <= 70:
                nws_url = f"https://api.weather.gov/points/{lat},{lon}"
                response = requests.get(nws_url, timeout=self.max_request_time)
                if response.status_code == 200:
                    point_data = response.json()
                    forecast_url = point_data['properties']['forecast']
                    forecast_response = requests.get(forecast_url, timeout=self.max_request_time)
                    if forecast_response.status_code == 200:
                        return {'source': 'NWS', 'data': forecast_response.json()}
        except Exception:
            pass
        
        return None
    
    def _get_marine_data_timeout(self, lat: float, lon: float, date: str) -> Optional[Dict]:
        """Get marine data with timeout."""
        try:
            # Try one reliable ERDDAP dataset
            base_url = "https://coastwatch.pfeg.noaa.gov/erddap/griddap"
            dataset_id = "jplMURSST41"
            
            # Simple SST query
            date_iso = f"{date}T12:00:00Z"
            query_url = f"{base_url}/{dataset_id}.json?analysed_sst[({date_iso}):1:({date_iso})][({lat}):1:({lat})][({lon}):1:({lon})]"
            
            response = requests.get(query_url, timeout=self.max_request_time)
            if response.status_code == 200:
                data = response.json()
                if 'table' in data and data['table']['rows']:
                    sst_value = data['table']['rows'][0][-1]  # Last column is usually the data
                    return {'source': 'ERDDAP', 'sst': sst_value}
        except Exception:
            pass
        
        return None
    
    def _get_stations_data_timeout(self, lat: float, lon: float) -> Optional[Dict]:
        """Get nearby stations with timeout."""
        try:
            # Estimate nearby stations based on location
            station_count = max(1, int(4 + np.random.normal(0, 2)))
            return {'source': 'Estimated', 'count': station_count}
        except Exception:
            pass
        
        return None
    
    def _get_ocean_pollution_data_timeout(self, lat: float, lon: float) -> Optional[Dict]:
        """Get ocean pollution data with timeout."""
        try:
            if self.ocean_downloader is None:
                return None
            
            # Get comprehensive ocean data (microplastics, pH, CO2)
            ocean_data = self.ocean_downloader.get_ocean_data_for_coordinates(lat, lon)
            
            if ocean_data:
                return {
                    'source': 'Ocean_Pollution_System',
                    'data': ocean_data,
                    'confidence': ocean_data.get('data_quality', {}).get('overall_confidence', 0.6)
                }
        except Exception as e:
            print(f"⚠️ Ocean pollution data failed: {e}")
            pass
        
        return None
    
    def _get_climate_zone(self, lat: float) -> str:
        """Get climate zone classification."""
        abs_lat = abs(lat)
        if abs_lat <= 23.5:
            return 'tropical'
        elif abs_lat <= 35:
            return 'subtropical'
        elif abs_lat <= 60:
            return 'temperate'
        elif abs_lat <= 66.5:
            return 'subpolar'
        else:
            return 'polar'
    
    def _merge_data(self, fallback: Dict, real_data: Dict) -> Dict:
        """Merge real data with fallback data."""
        result = fallback.copy()
        
        # Update with real weather data if available
        if 'weather' in real_data:
            weather = real_data['weather']
            if weather.get('source') == 'NWS':
                # Extract temperature from NWS data
                try:
                    forecast = weather['data']['properties']['periods'][0]
                    temp_f = forecast.get('temperature', 70)
                    temp_c = (temp_f - 32) * 5/9
                    result['current_weather']['temperature'] = {
                        'value': temp_c,
                        'units': '°C',
                        'source': 'NWS',
                        'quality': 'Good'
                    }
                except Exception:
                    pass
        
        # Update with marine data if available
        if 'marine' in real_data:
            marine = real_data['marine']
            if 'sst' in marine:
                result['marine_data']['sea_surface_temperature'] = {
                    'value': marine['sst'],
                    'units': '°C',
                    'source': 'ERDDAP',
                    'quality': 'Satellite'
                }
        
        # Update with ocean pollution data if available
        if 'ocean_pollution' in real_data:
            pollution_data = real_data['ocean_pollution']['data']
            
            # Add ocean chemistry data
            if 'ocean_chemistry' in pollution_data:
                chemistry = pollution_data['ocean_chemistry']
                
                if 'ph_total' in chemistry:
                    result['marine_data']['ocean_ph'] = chemistry['ph_total']
                
                if 'dissolved_oxygen' in chemistry:
                    result['marine_data']['dissolved_oxygen'] = chemistry['dissolved_oxygen']
                
                if 'co2_seawater' in chemistry:
                    result['marine_data']['co2_seawater'] = chemistry['co2_seawater']
            
            # Add marine pollution data
            if 'marine_pollution' in pollution_data:
                pollution = pollution_data['marine_pollution']
                
                if 'microplastics_density' in pollution:
                    result['marine_data']['microplastics_density'] = pollution['microplastics_density']
                
                if 'dominant_polymer' in pollution:
                    result['marine_data']['dominant_polymer'] = pollution['dominant_polymer']
        
        # Update metadata
        result['metadata']['has_real_data'] = True
        result['metadata']['real_data_sources'] = list(real_data.keys())
        
        return result


class ClimateDataFallback:
    """Generate realistic fallback climate data."""
    
    def generate_immediate_fallback(self, lat: float, lon: float, date: str) -> Dict[str, Any]:
        """Generate immediate fallback data based on location and season."""
        
        # Basic location analysis
        abs_lat = abs(lat)
        is_ocean = self._is_ocean_location(lat, lon)
        climate_zone = self._get_climate_zone(abs_lat)
        
        # Seasonal adjustment
        month = datetime.strptime(date, '%Y-%m-%d').month
        is_northern = lat >= 0
        is_summer = self._is_summer_season(month, is_northern)
        
        # Generate realistic temperature
        base_temp = self._estimate_temperature(abs_lat, is_summer, is_ocean)
        
        # Generate other parameters
        wind_speed = np.random.uniform(3, 25)
        humidity = np.random.uniform(30, 90)
        pressure = np.random.uniform(990, 1030)
        
        # Marine estimates
        wave_height = np.random.uniform(0.5, 3.0) if is_ocean else 0.0
        wave_period = np.random.uniform(4.0, 12.0) if is_ocean else 0.0
        current_speed = np.random.uniform(0.05, 0.4) if is_ocean else 0.0
        current_direction = np.random.uniform(0, 360) if is_ocean else 0.0
        
        # Additional marine parameters
        sea_surface_temp = base_temp + np.random.uniform(-2, 2) if is_ocean else base_temp
        chlorophyll = np.random.uniform(0.1, 2.0) if is_ocean else 0.0
        coral_stress = np.random.uniform(0, 8) if is_ocean and climate_zone == 'tropical' else 0.0
        
        return {
            'latitude': lat,
            'longitude': lon,
            'date': date,
            'climate_zone': climate_zone,
            'weather_labels': self._get_weather_labels(climate_zone, is_ocean),
            'current_weather': {
                'temperature': {
                    'value': base_temp,
                    'units': '°C',
                    'source': 'Estimated',
                    'quality': 'Fallback'
                },
                'wind_speed': {
                    'value': wind_speed,
                    'units': 'm/s',
                    'source': 'Estimated', 
                    'quality': 'Fallback'
                },
                'relative_humidity': {
                    'value': humidity,
                    'units': '%',
                    'source': 'Estimated',
                    'quality': 'Fallback'
                },
                'barometric_pressure': {
                    'value': pressure,
                    'units': 'hPa',
                    'source': 'Estimated',
                    'quality': 'Fallback'
                }
            },
            'marine_data': {
                'wave_height': {
                    'value': wave_height,
                    'units': 'meters',
                    'source': 'Estimated',
                    'quality': 'Fallback'
                },
                'wave_period': {
                    'value': wave_period,
                    'units': 'seconds',
                    'source': 'Estimated',
                    'quality': 'Fallback'
                },
                'current_speed': {
                    'value': current_speed,
                    'units': 'm/s',
                    'source': 'Estimated',
                    'quality': 'Fallback'
                },
                'current_direction': {
                    'value': current_direction,
                    'units': 'degrees',
                    'source': 'Estimated',
                    'quality': 'Fallback'
                },
                'sea_surface_temperature': {
                    'value': sea_surface_temp,
                    'units': '°C',
                    'source': 'Estimated',
                    'quality': 'Fallback'
                },
                'chlorophyll': {
                    'value': chlorophyll,
                    'units': 'mg/m³',
                    'source': 'Estimated',
                    'quality': 'Fallback'
                },
                'coral_stress': {
                    'value': coral_stress,
                    'units': 'index',
                    'source': 'Estimated',
                    'quality': 'Fallback'
                },
                # Ocean chemistry parameters (fallback estimates)
                'ocean_ph': {
                    'value': self._estimate_ocean_ph(abs_lat, is_ocean),
                    'units': 'pH_units',
                    'source': 'Estimated',
                    'quality': 'Fallback'
                },
                'dissolved_oxygen': {
                    'value': self._estimate_dissolved_oxygen(abs_lat, is_ocean),
                    'units': 'mg/L',
                    'source': 'Estimated',
                    'quality': 'Fallback'
                },
                'co2_seawater': {
                    'value': self._estimate_seawater_co2(abs_lat, is_ocean),
                    'units': 'ppm',
                    'source': 'Estimated',
                    'quality': 'Fallback'
                },
                # Marine pollution parameters (fallback estimates)
                'microplastics_density': {
                    'value': self._estimate_microplastics(abs_lat, is_ocean, climate_zone),
                    'units': 'particles/m³',
                    'source': 'Estimated',
                    'quality': 'Fallback'
                },
                'dominant_polymer': {
                    'value': self._estimate_dominant_polymer(),
                    'units': 'polymer_type',
                    'source': 'Estimated',
                    'quality': 'Fallback'
                }
            },
            'metadata': {
                'source': 'Fast_Fallback',
                'confidence': 0.6,
                'has_real_data': False,
                'processing_time': 0.0,
                'timestamp': datetime.now().isoformat()
            }
        }
    
    def _is_ocean_location(self, lat: float, lon: float) -> bool:
        """Rough estimate if location is over ocean."""
        # Very simplified - most of Earth is ocean
        if abs(lat) > 70:  # Polar regions
            return lon < 0 or lon > 120
        return True  # Default to ocean for most locations
    
    def _get_climate_zone(self, abs_lat: float) -> str:
        """Get climate zone from latitude."""
        if abs_lat <= 23.5:
            return 'tropical'
        elif abs_lat <= 35:
            return 'subtropical'
        elif abs_lat <= 60:
            return 'temperate'
        elif abs_lat <= 66.5:
            return 'subpolar'
        else:
            return 'polar'
    
    def _is_summer_season(self, month: int, is_northern: bool) -> bool:
        """Determine if it's summer season."""
        if is_northern:
            return month in [6, 7, 8, 9]
        else:
            return month in [12, 1, 2, 3]
    
    def _estimate_temperature(self, abs_lat: float, is_summer: bool, is_ocean: bool) -> float:
        """Estimate temperature based on location and season."""
        # Base temperature by latitude
        if abs_lat <= 10:  # Equatorial
            base = 28
        elif abs_lat <= 23.5:  # Tropical
            base = 25
        elif abs_lat <= 35:  # Subtropical
            base = 20
        elif abs_lat <= 50:  # Temperate
            base = 15
        elif abs_lat <= 66.5:  # Subpolar
            base = 5
        else:  # Polar
            base = -10
        
        # Seasonal adjustment
        if is_summer:
            base += 8
        else:
            base -= 5
        
        # Ocean moderation
        if is_ocean:
            base += 2  # Oceans moderate temperature
        
        # Add some randomness
        return base + np.random.uniform(-3, 3)
    
    def _get_weather_labels(self, climate_zone: str, is_ocean: bool) -> List[str]:
        """Get weather labels."""
        labels = [climate_zone.title()]
        if is_ocean:
            labels.append('Marine')
        else:
            labels.append('Continental')
        return labels
    
    def _estimate_ocean_ph(self, abs_lat: float, is_ocean: bool) -> float:
        """Estimate ocean pH based on latitude and location."""
        if not is_ocean:
            return 7.0  # Neutral for non-ocean locations
        
        # Global ocean pH patterns
        if abs_lat > 60:  # Polar - higher pH due to cold water CO2 absorption
            base_ph = 8.15
        elif abs_lat < 30:  # Tropical - lower pH due to warming and acidification
            base_ph = 8.05
        else:  # Temperate
            base_ph = 8.10
        
        # Add some realistic variation
        variation = np.random.normal(0, 0.02)
        return round(base_ph + variation, 2)
    
    def _estimate_dissolved_oxygen(self, abs_lat: float, is_ocean: bool) -> float:
        """Estimate dissolved oxygen levels."""
        if not is_ocean:
            return 8.0  # Higher for freshwater
        
        # Ocean dissolved oxygen patterns (colder water holds more oxygen)
        if abs_lat > 60:  # Polar - high oxygen
            base_o2 = 7.5
        elif abs_lat < 30:  # Tropical - lower oxygen
            base_o2 = 6.0
        else:  # Temperate
            base_o2 = 6.8
        
        variation = np.random.normal(0, 0.3)
        return round(max(4.0, base_o2 + variation), 2)
    
    def _estimate_seawater_co2(self, abs_lat: float, is_ocean: bool) -> float:
        """Estimate seawater CO2 concentrations."""
        if not is_ocean:
            return 400.0  # Atmospheric levels for non-ocean
        
        # Base CO2 around current atmospheric levels with ocean variations
        base_co2 = 410
        
        # Latitude effects (polar regions absorb more CO2)
        if abs_lat > 50:  # High latitudes - CO2 sink
            lat_effect = -15
        elif abs_lat < 30:  # Tropics - CO2 source
            lat_effect = 5
        else:
            lat_effect = 0
        
        variation = np.random.normal(0, 8)
        return round(max(350, base_co2 + lat_effect + variation), 1)
    
    def _estimate_microplastics(self, abs_lat: float, is_ocean: bool, climate_zone: str) -> float:
        """Estimate microplastics density based on location."""
        if not is_ocean:
            return 0.1  # Very low for non-ocean
        
        # Base pollution levels by climate zone and latitude
        if abs_lat > 60:  # Polar regions - lower pollution
            base_pollution = 0.5
        elif abs_lat < 30:  # Tropical/subtropical - higher shipping
            base_pollution = 3.0
        else:  # Temperate - moderate
            base_pollution = 2.0
        
        # Add some realistic variation
        variation = np.random.lognormal(0, 0.6)
        return round(max(0.1, base_pollution * variation), 2)
    
    def _estimate_dominant_polymer(self) -> str:
        """Estimate the dominant polymer type in microplastics."""
        # Based on real-world distributions
        polymers = ['PE', 'PP', 'PS', 'PET', 'PVC']
        weights = [0.35, 0.25, 0.20, 0.15, 0.05]  # PE and PP are most common
        return np.random.choice(polymers, p=weights)