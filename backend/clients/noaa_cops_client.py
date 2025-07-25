#!/usr/bin/env python3
"""
NOAA CO-OPS API client.
#2 RECOMMENDED API for real-time coastal data and sea level trends.
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

from .base_client import BaseAPIClient

class NOAACOPSClient(BaseAPIClient):
    """
    Client for NOAA Center for Operational Oceanographic Products and Services (CO-OPS) API.
    
    Features:
    - Direct JSON/XML responses without file downloads
    - Long-term records (historical data back to 1800s for some stations)
    - Built-in trend analysis and extreme value statistics
    - Real-time coastal conditions
    """
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize NOAA CO-OPS client."""
        super().__init__(
            api_name="NOAA CO-OPS API",
            base_url="https://api.tidesandcurrents.noaa.gov/api/prod/datagetter",
            cache_dir=cache_dir
        )
        
        # NOAA CO-OPS specific endpoints
        self.stations_url = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json"
        self.metadata_url = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations"
        
        # Available data products
        self.data_products = {
            'water_level': {
                'product': 'water_level',
                'name': 'Water Level',
                'description': 'Preliminary or verified water levels',
                'units': 'meters',
                'frequency': '6_minute'
            },
            'hourly_height': {
                'product': 'hourly_height', 
                'name': 'Hourly Heights',
                'description': 'Hourly water level heights',
                'units': 'meters',
                'frequency': 'hourly'
            },
            'high_low': {
                'product': 'high_low',
                'name': 'High/Low Tide Predictions',
                'description': 'High and low tide predictions',
                'units': 'meters',
                'frequency': 'event_based'
            },
            'daily_mean': {
                'product': 'daily_mean',
                'name': 'Daily Mean Sea Level',
                'description': 'Daily mean water levels',
                'units': 'meters',
                'frequency': 'daily'
            },
            'monthly_mean': {
                'product': 'monthly_mean',
                'name': 'Monthly Mean Sea Level',
                'description': 'Monthly mean water levels for climate analysis',
                'units': 'meters',
                'frequency': 'monthly'
            },
            'water_temperature': {
                'product': 'water_temperature',
                'name': 'Water Temperature',
                'description': 'Water temperature measurements',
                'units': 'celsius',
                'frequency': '6_minute'
            },
            'air_temperature': {
                'product': 'air_temperature',
                'name': 'Air Temperature',
                'description': 'Air temperature measurements',
                'units': 'celsius',
                'frequency': '6_minute'
            },
            'wind': {
                'product': 'wind',
                'name': 'Wind Speed and Direction',
                'description': 'Wind measurements',
                'units': 'm/s_and_degrees',
                'frequency': '6_minute'
            },
            'air_pressure': {
                'product': 'air_pressure',
                'name': 'Barometric Pressure',
                'description': 'Atmospheric pressure measurements',
                'units': 'millibars',
                'frequency': '6_minute'
            }
        }
        
        # Station cache
        self._stations_cache = None
        self._stations_cache_time = None
        
        # Initialize coverage information
        self.coverage_info = {
            'spatial_bounds': {
                'lat_min': 7.0,    # Puerto Rico (southernmost US station)
                'lat_max': 70.0,   # Alaska (northernmost station)
                'lon_min': -180.0, # Pacific islands
                'lon_max': -50.0   # Atlantic coast
            },
            'temporal_bounds': {
                'start': '1854-01-01',  # Oldest station records
                'end': datetime.now().strftime('%Y-%m-%d'),
                'real_time_lag': 'minutes'
            },
            'available_parameters': list(self.data_products.keys()),
            'station_count': None,
            'last_updated': None
        }
        
        self.logger.info("NOAA CO-OPS client initialized")
        self.logger.info(f"Data products available: {len(self.data_products)}")
    
    def discover_coverage(self) -> Dict[str, Any]:
        """
        Discover spatial and temporal coverage from NOAA CO-OPS stations.
        
        Returns:
            Dictionary with comprehensive coverage information
        """
        self.logger.info("Discovering NOAA CO-OPS coverage...")
        
        coverage_data = {
            'api_name': self.api_name,
            'discovery_timestamp': datetime.now().isoformat(),
            'stations': {},
            'geographic_coverage': {},
            'parameter_availability': {},
            'temporal_coverage': {},
            'data_products': self.data_products
        }
        
        try:
            # Test connection
            connection_status = self.test_connection()
            coverage_data['connection_status'] = connection_status
            
            # Get all stations
            stations = self._get_all_stations()
            coverage_data['stations'] = {
                'total_count': len(stations),
                'active_count': len([s for s in stations if s.get('status') == 'active']),
                'station_list': stations[:50],  # First 50 for demo
                'geographic_distribution': self._analyze_station_distribution(stations)
            }
            
            # Analyze geographic coverage
            coverage_data['geographic_coverage'] = {
                'regions_covered': self._get_covered_regions(stations),
                'coastal_coverage': {
                    'atlantic_coast': len([s for s in stations if -85 < s.get('lng', 0) < -60]),
                    'pacific_coast': len([s for s in stations if -180 < s.get('lng', 0) < -110]),
                    'gulf_coast': len([s for s in stations if -100 < s.get('lng', 0) < -80 and s.get('lat', 0) < 35]),
                    'great_lakes': len([s for s in stations if -90 < s.get('lng', 0) < -75 and s.get('lat', 0) > 40]),
                    'alaska': len([s for s in stations if s.get('state') == 'AK']),
                    'hawaii_pacific': len([s for s in stations if s.get('state') in ['HI', 'GU', 'PR', 'VI']])
                },
                'spatial_bounds': self._calculate_actual_bounds(stations)
            }
            
            # Analyze parameter availability by station
            coverage_data['parameter_availability'] = self._analyze_parameter_availability(stations)
            
            # Temporal coverage analysis
            coverage_data['temporal_coverage'] = {
                'real_time_data': True,
                'historical_archive': True,
                'oldest_records': '1854 (some stations)',
                'update_frequency': 'every_6_minutes',
                'climate_records': 'monthly_means_available',
                'trend_analysis': 'built_in_statistics'
            }
            
            # Update internal coverage info  
            self.coverage_info['station_count'] = len(stations)
            self.coverage_info['spatial_bounds'] = coverage_data['geographic_coverage']['spatial_bounds']
            self.coverage_info['last_updated'] = datetime.now().isoformat()
            
            self.logger.info(f"Coverage discovery completed - found {len(stations)} stations")
            
            return coverage_data
            
        except Exception as e:
            self.logger.error(f"Coverage discovery failed: {e}")
            coverage_data['error'] = str(e)
            coverage_data['status'] = 'failed'
            return coverage_data
    
    def _get_all_stations(self) -> List[Dict[str, Any]]:
        """Get all NOAA CO-OPS stations."""
        
        # Check cache first
        if (self._stations_cache and self._stations_cache_time and 
            (datetime.now() - self._stations_cache_time).total_seconds() < 3600):
            return self._stations_cache
        
        try:
            response = self._make_request(self.stations_url)
            data = response.json()
            
            stations = data.get('stations', [])
            
            # Cache the result
            self._stations_cache = stations
            self._stations_cache_time = datetime.now()
            
            self.logger.info(f"Retrieved {len(stations)} stations from NOAA CO-OPS")
            return stations
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve stations: {e}")
            return []
    
    def _analyze_station_distribution(self, stations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze geographic distribution of stations."""
        
        if not stations:
            return {}
        
        # Group by state/region
        by_state = {}
        for station in stations:
            state = station.get('state', 'Unknown')
            if state not in by_state:
                by_state[state] = 0
            by_state[state] += 1
        
        return {
            'by_state': dict(sorted(by_state.items(), key=lambda x: x[1], reverse=True)),
            'total_states': len(by_state),
            'stations_per_state_avg': len(stations) / len(by_state) if by_state else 0
        }
    
    def _get_covered_regions(self, stations: List[Dict[str, Any]]) -> List[str]:
        """Get list of geographic regions with station coverage."""
        
        regions = set()
        
        for station in stations:
            lat = station.get('lat', 0)
            lon = station.get('lng', 0)
            state = station.get('state', '')
            
            # Classify by region
            if state in ['AK']:
                regions.add('Alaska')
            elif state in ['HI', 'GU', 'AS', 'MP']:
                regions.add('Pacific_Islands')
            elif state in ['PR', 'VI']:
                regions.add('Caribbean')
            elif lon > -85:
                regions.add('Atlantic_Coast')
            elif lon < -110:
                regions.add('Pacific_Coast')
            elif -100 < lon < -80 and lat < 35:
                regions.add('Gulf_Coast')
            elif -90 < lon < -75 and lat > 40:
                regions.add('Great_Lakes')
            else:
                regions.add('Other')
        
        return sorted(list(regions))
    
    def _calculate_actual_bounds(self, stations: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate actual spatial bounds from station locations."""
        
        if not stations:
            return self.coverage_info['spatial_bounds']
        
        lats = [s.get('lat', 0) for s in stations if s.get('lat')]
        lons = [s.get('lng', 0) for s in stations if s.get('lng')]
        
        if not lats or not lons:
            return self.coverage_info['spatial_bounds']
        
        return {
            'lat_min': min(lats),
            'lat_max': max(lats),
            'lon_min': min(lons),
            'lon_max': max(lons)
        }
    
    def _analyze_parameter_availability(self, stations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze which parameters are available at different stations."""
        
        # Note: This would require individual station metadata queries in a real implementation
        # For now, provide general availability information
        
        parameter_stats = {}
        
        for product_key, product_info in self.data_products.items():
            # Estimate availability based on product type
            if product_key in ['water_level', 'hourly_height', 'daily_mean', 'monthly_mean']:
                availability = 0.95  # Most stations have water level
            elif product_key in ['water_temperature', 'air_temperature']:
                availability = 0.70  # Many stations have temperature
            elif product_key in ['wind', 'air_pressure']:
                availability = 0.60  # Fewer stations have meteorological data
            else:
                availability = 0.50  # Other parameters less common
            
            parameter_stats[product_key] = {
                'name': product_info['name'],
                'estimated_station_coverage': availability,
                'estimated_stations_with_data': int(len(stations) * availability),
                'temporal_resolution': product_info['frequency'],
                'units': product_info['units']
            }
        
        return parameter_stats
    
    def get_available_datasets(self) -> List[Dict[str, Any]]:
        """
        Get list of available data products from NOAA CO-OPS.
        
        Returns:
            List of data product information dictionaries
        """
        datasets = []
        
        for product_key, product_info in self.data_products.items():
            datasets.append({
                'key': product_key,
                'product_id': product_info['product'],
                'name': product_info['name'],
                'description': product_info['description'],
                'units': product_info['units'],
                'temporal_resolution': product_info['frequency'],
                'spatial_coverage': 'coastal_stations',
                'api_name': self.api_name,
                'recommended_for': self._get_product_recommendations(product_key),
                'climate_relevance': self._get_climate_relevance(product_key)
            })
        
        return datasets
    
    def _get_product_recommendations(self, product_key: str) -> List[str]:
        """Get recommendations for what this data product is best used for."""
        
        recommendations = {
            'water_level': ['sea_level_dynamics', 'extreme_events', 'coastal_flooding'],
            'hourly_height': ['sea_level_dynamics', 'tidal_analysis', 'storm_surge'],
            'high_low': ['extreme_events', 'tidal_predictions', 'coastal_planning'],
            'daily_mean': ['sea_level_trends', 'climate_analysis', 'long_term_monitoring'],
            'monthly_mean': ['climate_trends', 'sea_level_rise', 'decadal_variability'],
            'water_temperature': ['temperature_heat', 'marine_heatwaves', 'coastal_climate'],
            'air_temperature': ['temperature_heat', 'coastal_meteorology', 'extreme_events'],
            'wind': ['extreme_events', 'storm_analysis', 'coastal_meteorology'],
            'air_pressure': ['extreme_events', 'storm_tracking', 'weather_analysis']
        }
        
        return recommendations.get(product_key, ['coastal_monitoring'])
    
    def _get_climate_relevance(self, product_key: str) -> str:
        """Get climate relevance rating for a data product."""
        
        climate_ratings = {
            'monthly_mean': 'high',
            'daily_mean': 'high', 
            'water_temperature': 'high',
            'water_level': 'medium',
            'hourly_height': 'medium',
            'air_temperature': 'medium',
            'wind': 'low',
            'air_pressure': 'low',
            'high_low': 'low'
        }
        
        return climate_ratings.get(product_key, 'medium')
    
    def find_nearest_stations(self, lat: float, lon: float, max_distance_km: float = 100,
                            max_stations: int = 5) -> List[Dict[str, Any]]:
        """
        Find nearest NOAA CO-OPS stations to given coordinates.
        
        Args:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees
            max_distance_km: Maximum distance to search (km)
            max_stations: Maximum number of stations to return
            
        Returns:
            List of nearest stations with distance information
        """
        stations = self._get_all_stations()
        if not stations:
            return []
        
        # Calculate distances
        station_distances = []
        for station in stations:
            station_lat = station.get('lat')
            station_lon = station.get('lng')
            
            if station_lat is None or station_lon is None:
                continue
            
            # Simple distance calculation (not great circle, but adequate for coastal areas)
            lat_diff = lat - station_lat
            lon_diff = lon - station_lon
            distance_km = ((lat_diff ** 2 + lon_diff ** 2) ** 0.5) * 111  # Rough km conversion
            
            if distance_km <= max_distance_km:
                station_info = station.copy()
                station_info['distance_km'] = distance_km
                station_distances.append(station_info)
        
        # Sort by distance and return top results
        station_distances.sort(key=lambda x: x['distance_km'])
        return station_distances[:max_stations]
    
    def query_data(self, lat: float, lon: float, start_date: str, end_date: str,
                  parameters: List[str] = None, station_id: str = None) -> Dict[str, Any]:
        """
        Query data from NOAA CO-OPS for specific location and time range.
        
        Args:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            parameters: List of parameters to retrieve
            station_id: Specific station ID (if not provided, finds nearest)
            
        Returns:
            Dictionary with query results
        """
        self.logger.info(f"Querying NOAA CO-OPS data for {lat:.4f}, {lon:.4f} from {start_date} to {end_date}")
        
        # Validate inputs
        if not self.validate_coordinates(lat, lon):
            raise ValueError(f"Invalid coordinates: {lat}, {lon}")
        
        if not self.validate_time_range(start_date, end_date):
            raise ValueError(f"Invalid time range: {start_date} to {end_date}")
        
        # Find station if not provided
        if not station_id:
            nearest_stations = self.find_nearest_stations(lat, lon)
            if not nearest_stations:
                return {
                    'api_name': self.api_name,
                    'status': 'no_stations',
                    'message': 'No NOAA CO-OPS stations found within search radius',
                    'coordinates': {'lat': lat, 'lon': lon},
                    'search_radius_km': 100
                }
            station_id = nearest_stations[0]['id']
            station_info = nearest_stations[0]
        else:
            station_info = {'id': station_id, 'distance_km': 0}
        
        # Default parameters
        if not parameters:
            parameters = ['monthly_mean', 'water_temperature']
        
        # Query each parameter
        query_results = []
        for param in parameters:
            if param not in self.data_products:
                self.logger.warning(f"Unknown parameter: {param}")
                continue
                
            try:
                param_result = self._query_station_parameter(
                    station_id, param, start_date, end_date
                )
                query_results.append(param_result)
            except Exception as e:
                self.logger.error(f"Failed to query {param} for station {station_id}: {e}")
                query_results.append({
                    'parameter': param,
                    'status': 'error',
                    'error': str(e)
                })
        
        return {
            'api_name': self.api_name,
            'station_info': station_info,
            'query_parameters': {
                'coordinates': {'lat': lat, 'lon': lon},
                'start_date': start_date,
                'end_date': end_date,
                'parameters': parameters
            },
            'results': query_results,
            'status': 'completed',
            'data_points_total': sum(r.get('data_points', 0) for r in query_results),
            'query_timestamp': datetime.now().isoformat()
        }
    
    def _query_station_parameter(self, station_id: str, parameter: str, 
                               start_date: str, end_date: str) -> Dict[str, Any]:
        """Query a specific parameter from a station."""
        
        product_info = self.data_products[parameter]
        
        # Build query parameters
        params = {
            'product': product_info['product'],
            'application': 'NOS.COOPS.TAC.WL',
            'station': station_id,
            'begin_date': start_date.replace('-', ''),
            'end_date': end_date.replace('-', ''),
            'datum': 'MSL',  # Mean Sea Level
            'units': 'metric',
            'time_zone': 'GMT',
            'format': 'json'
        }
        
        try:
            response = self._make_request(self.base_url, params)
            data = response.json()
            
            # Check for API errors
            if 'error' in data:
                return {
                    'parameter': parameter,  
                    'status': 'api_error',
                    'error': data['error']['message'],
                    'product': product_info['product']
                }
            
            # Extract data
            raw_data = data.get('data', [])
            
            return {
                'parameter': parameter,
                'product': product_info['product'],
                'station_id': station_id,
                'status': 'success',
                'data_points': len(raw_data),
                'units': product_info['units'],
                'temporal_resolution': product_info['frequency'],
                'sample_data': raw_data[:5] if raw_data else [],  # First 5 points
                'data_range': {
                    'start': raw_data[0] if raw_data else None,
                    'end': raw_data[-1] if raw_data else None
                },
                'query_url': f"{self.base_url}?{requests.compat.urlencode(params)}"
            }
            
        except Exception as e:
            return {
                'parameter': parameter,
                'status': 'query_error', 
                'error': str(e),
                'product': product_info['product']
            }