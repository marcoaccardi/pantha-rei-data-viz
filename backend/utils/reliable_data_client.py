#!/usr/bin/env python3
"""
Reliable Data Client - Wrapper that ensures ocean data is always available
with fallback mechanisms and error handling.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
import logging
from pathlib import Path

from .data_availability_predictor import DataAvailabilityPredictor

class ReliableDataClient:
    """
    Wrapper client that ensures reliable data access with fallback mechanisms.
    Guarantees data availability based on ocean coordinates and dates.
    """
    
    def __init__(self, copernicus_client=None, obis_client=None, ncei_client=None):
        """Initialize the reliable data client with fallback capabilities."""
        self.logger = logging.getLogger(__name__)
        
        # Store client instances
        self.copernicus_client = copernicus_client
        self.obis_client = obis_client
        self.ncei_client = ncei_client
        
        # Initialize availability predictor
        self.predictor = DataAvailabilityPredictor()
        
        # Define data source mappings
        self.source_mappings = {
            # Copernicus datasets
            'sst_global_l4': {
                'client': 'copernicus',
                'predictor_key': 'copernicus_sst',
                'fallback': None
            },
            'salinity_global': {
                'client': 'copernicus',
                'predictor_key': 'copernicus_salinity',
                'fallback': None
            },
            'currents_global': {
                'client': 'copernicus',
                'predictor_key': 'copernicus_currents',
                'fallback': None
            },
            'wave_global': {
                'client': 'copernicus',
                'predictor_key': 'copernicus_wave',
                'fallback': None
            },
            'chlorophyll_global': {
                'client': 'copernicus',
                'predictor_key': 'copernicus_chlorophyll',
                'fallback': None
            },
            'ph_global': {
                'client': 'copernicus',
                'predictor_key': 'copernicus_ph',
                'fallback': None
            },
            'biogeochemistry_global': {
                'client': 'copernicus',
                'predictor_key': 'copernicus_biogeochemistry',
                'fallback': None
            },
            
            # Alternative data sources
            'biodiversity': {
                'client': 'obis',
                'predictor_key': 'obis_biodiversity',
                'fallback': None
            },
            'microplastics': {
                'client': 'ncei',
                'predictor_key': 'ncei_microplastics',
                'fallback': None
            }
        }
        
        self.logger.info("Reliable data client initialized")
    
    def query_data_reliably(self, data_source: str, lat: float, lon: float,
                           start_date: str, end_date: str, **kwargs) -> Dict[str, Any]:
        """
        Query data with reliability guarantees and fallback mechanisms.
        
        Args:
            data_source: Name of the data source
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with reliable query results
        """
        self.logger.info(f"Reliable query: {data_source} at {lat}, {lon} from {start_date} to {end_date}")
        
        # Step 1: Predict availability
        prediction = self.predictor.predict_availability(
            self.source_mappings.get(data_source, {}).get('predictor_key', data_source),
            lat, lon, start_date
        )
        
        self.logger.info(f"Availability prediction: {prediction['confidence']:.2f} confidence")
        
        # Step 2: Try primary query
        primary_result = self._execute_primary_query(
            data_source, lat, lon, start_date, end_date, **kwargs
        )
        
        if primary_result.get('status') == 'success':
            # Success - add reliability metadata
            primary_result['reliability'] = {
                'prediction': prediction,
                'fallback_used': False,
                'confidence': prediction['confidence'],
                'data_quality': 'primary_source'
            }
            return primary_result
        
        # Step 3: Primary failed - try fallback strategies
        self.logger.warning(f"Primary query failed: {primary_result.get('error', 'Unknown error')}")
        
        if prediction['fallback_options']:
            fallback_result = self._execute_fallback_strategies(
                data_source, lat, lon, start_date, end_date, 
                prediction['fallback_options'], **kwargs
            )
            
            if fallback_result.get('status') == 'success':
                fallback_result['reliability'] = {
                    'prediction': prediction,
                    'fallback_used': True,
                    'confidence': prediction['confidence'] * 0.8,  # Reduced confidence for fallback
                    'data_quality': 'fallback_source',
                    'fallback_strategy': fallback_result.get('fallback_strategy')
                }
                return fallback_result
        
        # Step 4: All strategies failed - return graceful error
        return self._create_graceful_error_response(
            data_source, lat, lon, start_date, end_date, 
            primary_result, prediction
        )
    
    def _execute_primary_query(self, data_source: str, lat: float, lon: float,
                              start_date: str, end_date: str, **kwargs) -> Dict[str, Any]:
        """Execute the primary data query."""
        source_info = self.source_mappings.get(data_source)
        
        if not source_info:
            return {
                'status': 'error',
                'error': f'Unknown data source: {data_source}',
                'api_name': 'ReliableDataClient'
            }
        
        try:
            client_name = source_info['client']
            
            if client_name == 'copernicus' and self.copernicus_client:
                return self.copernicus_client.query_data(
                    lat=lat, lon=lon,
                    start_date=start_date, end_date=end_date,
                    dataset_key=data_source, **kwargs
                )
            elif client_name == 'obis' and self.obis_client:
                return self.obis_client.query_data(
                    lat=lat, lon=lon,
                    start_date=start_date, end_date=end_date,
                    **kwargs
                )
            elif client_name == 'ncei' and self.ncei_client:
                return self.ncei_client.query_data(
                    lat=lat, lon=lon,
                    start_date=start_date, end_date=end_date,
                    **kwargs
                )
            else:
                return {
                    'status': 'error',
                    'error': f'Client not available: {client_name}',
                    'api_name': 'ReliableDataClient'
                }
                
        except Exception as e:
            self.logger.error(f"Primary query exception: {e}")
            return {
                'status': 'error',
                'error': f'Primary query failed: {str(e)}',
                'api_name': 'ReliableDataClient'
            }
    
    def _execute_fallback_strategies(self, data_source: str, lat: float, lon: float,
                                   start_date: str, end_date: str,
                                   fallback_options: List[Dict[str, Any]], 
                                   **kwargs) -> Dict[str, Any]:
        """Execute fallback strategies when primary query fails."""
        
        for fallback in fallback_options:
            self.logger.info(f"Trying fallback strategy: {fallback['type']}")
            
            if fallback['type'] == 'temporal_fallback':
                # Try with suggested date
                suggested_date = fallback.get('suggested_date', start_date)
                result = self._execute_primary_query(
                    data_source, lat, lon, suggested_date, suggested_date, **kwargs
                )
                
                if result.get('status') == 'success':
                    result['fallback_strategy'] = {
                        'type': 'temporal_fallback',
                        'original_date': start_date,
                        'used_date': suggested_date,
                        'reason': fallback.get('reason')
                    }
                    return result
            
            elif fallback['type'] == 'spatial_fallback':
                # Try with expanded search radius
                expanded_kwargs = kwargs.copy()
                expanded_kwargs['radius'] = fallback.get('suggested_radius_km', 100)
                
                result = self._execute_primary_query(
                    data_source, lat, lon, start_date, end_date, **expanded_kwargs
                )
                
                if result.get('status') == 'success':
                    result['fallback_strategy'] = {
                        'type': 'spatial_fallback',
                        'expanded_radius_km': expanded_kwargs['radius'],
                        'reason': fallback.get('reason')
                    }
                    return result
        
        # No fallback strategies worked
        return {
            'status': 'error',
            'error': 'All fallback strategies failed',
            'api_name': 'ReliableDataClient'
        }
    
    def _create_graceful_error_response(self, data_source: str, lat: float, lon: float,
                                      start_date: str, end_date: str,
                                      primary_result: Dict[str, Any],
                                      prediction: Dict[str, Any]) -> Dict[str, Any]:
        """Create a graceful error response with helpful information."""
        
        # Get guaranteed availability window
        guaranteed = self.predictor.get_guaranteed_availability_window()
        
        error_response = {
            'api_name': 'ReliableDataClient',
            'status': 'error',
            'error': 'Data not available for specified parameters',
            'coordinates': {'lat': lat, 'lon': lon},
            'requested_date_range': {'start': start_date, 'end': end_date},
            'data_source': data_source,
            'timestamp': datetime.now().isoformat(),
            
            # Diagnostic information
            'diagnostics': {
                'primary_error': primary_result.get('error', 'Unknown error'),
                'availability_prediction': prediction,
                'confidence_score': prediction['confidence']
            },
            
            # Helpful suggestions
            'suggestions': {
                'guaranteed_date_range': {
                    'start': guaranteed['guaranteed_start_date'],
                    'end': guaranteed['guaranteed_end_date'],
                    'recommendation': guaranteed['recommendation']
                },
                'alternative_coordinates': self._suggest_alternative_coordinates(lat, lon),
                'alternative_data_sources': self._suggest_alternative_sources(data_source)
            },
            
            # User-friendly message
            'message': self._generate_user_friendly_error_message(
                data_source, lat, lon, start_date, prediction
            )
        }
        
        return error_response
    
    def _suggest_alternative_coordinates(self, lat: float, lon: float) -> Dict[str, Any]:
        """Suggest alternative coordinates with better data coverage."""
        # Simple suggestions based on major ocean basins
        suggestions = []
        
        # If in polar regions, suggest temperate waters
        if lat > 70:
            suggestions.append({
                'lat': 60.0, 'lon': lon,
                'reason': 'North Atlantic with reliable coverage',
                'distance_km': abs(lat - 60.0) * 111  # Rough km conversion
            })
        elif lat < -70:
            suggestions.append({
                'lat': -45.0, 'lon': lon,
                'reason': 'Southern Ocean with better coverage',
                'distance_km': abs(lat - (-45.0)) * 111
            })
        
        # Always suggest Mediterranean as a reliable test point
        suggestions.append({
            'lat': 40.0, 'lon': 15.0,
            'reason': 'Mediterranean Sea - well-covered test location',
            'distance_km': ((lat - 40.0)**2 + (lon - 15.0)**2)**0.5 * 111
        })
        
        return {
            'available': len(suggestions) > 0,
            'suggestions': suggestions[:3]  # Limit to 3 suggestions
        }
    
    def _suggest_alternative_sources(self, data_source: str) -> Dict[str, Any]:
        """Suggest alternative data sources."""
        alternatives = []
        
        # Define source alternatives
        source_alternatives = {
            'biodiversity': ['obis_biodiversity', 'pangaea_research'],
            'microplastics': ['ncei_microplastics', 'pangaea_research'],
            'sst_global_l4': ['copernicus_temperature_global'],
            'currents_global': ['copernicus_physics_analysis']
        }
        
        if data_source in source_alternatives:
            for alt_source in source_alternatives[data_source]:
                alternatives.append({
                    'source': alt_source,
                    'reason': f'Alternative to {data_source}',
                    'reliability': self.predictor.temporal_coverage.get(alt_source, {}).get('reliability', 0.8)
                })
        
        return {
            'available': len(alternatives) > 0,
            'alternatives': alternatives
        }
    
    def _generate_user_friendly_error_message(self, data_source: str, lat: float, 
                                            lon: float, date: str, 
                                            prediction: Dict[str, Any]) -> str:
        """Generate a user-friendly error message."""
        
        reasons = prediction.get('reasons', [])
        
        if any('time dimension exceed' in reason or 'outside temporal coverage' in reason for reason in reasons):
            guaranteed = self.predictor.get_guaranteed_availability_window()
            return (f"Data for {data_source} is not available for {date}. "
                   f"Try using dates from {guaranteed['guaranteed_start_date']} onwards "
                   f"for guaranteed availability.")
        
        elif any('Invalid coordinates' in reason or 'land' in reason.lower() for reason in reasons):
            return (f"The coordinates ({lat}, {lon}) appear to be on land or invalid. "
                   f"Please use ocean coordinates for marine data queries.")
        
        elif any('limited coverage' in reason.lower() for reason in reasons):
            return (f"Limited data coverage at ({lat}, {lon}). "
                   f"Consider expanding the search radius or using nearby ocean locations.")
        
        else:
            return (f"Data temporarily unavailable for {data_source} at ({lat}, {lon}) on {date}. "
                   f"This may be due to temporary server issues or data processing delays.")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status and reliability information."""
        
        # Test basic connectivity
        connectivity_status = {}
        
        if self.copernicus_client:
            try:
                # Quick test query
                test_result = self.copernicus_client.query_data(
                    lat=40.0, lon=15.0,
                    start_date='2024-01-01', end_date='2024-01-01',
                    dataset_key='sst_global_l4'
                )
                connectivity_status['copernicus'] = test_result.get('status') == 'success'
            except:
                connectivity_status['copernicus'] = False
        
        if self.obis_client:
            connectivity_status['obis'] = True  # OBIS is always available (mock/API)
        
        if self.ncei_client:
            connectivity_status['ncei'] = True  # NCEI is always available (mock)
        
        # Get reliability information
        reliability_info = self.predictor.get_data_source_reliability()
        guaranteed_window = self.predictor.get_guaranteed_availability_window()
        
        return {
            'system_status': 'operational' if any(connectivity_status.values()) else 'degraded',
            'connectivity': connectivity_status,
            'data_source_reliability': reliability_info,
            'guaranteed_availability': guaranteed_window,
            'last_updated': datetime.now().isoformat(),
            'total_data_sources': len(self.source_mappings),
            'operational_sources': sum(1 for status in connectivity_status.values() if status)
        }
    
    def validate_query_parameters(self, data_source: str, lat: float, lon: float,
                                 start_date: str, end_date: str) -> Dict[str, Any]:
        """Validate query parameters before executing."""
        
        validation = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'suggestions': []
        }
        
        # Validate data source
        if data_source not in self.source_mappings:
            validation['valid'] = False
            validation['errors'].append(f"Unknown data source: {data_source}")
        
        # Validate coordinates
        if not (-90 <= lat <= 90):
            validation['valid'] = False
            validation['errors'].append(f"Invalid latitude: {lat} (must be between -90 and 90)")
        
        if not (-180 <= lon <= 180):
            validation['valid'] = False
            validation['errors'].append(f"Invalid longitude: {lon} (must be between -180 and 180)")
        
        # Validate dates
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            if start_dt > end_dt:
                validation['valid'] = False
                validation['errors'].append(f"Start date {start_date} is after end date {end_date}")
            
            # Check if dates are too far in the future
            if start_dt > datetime.now() + timedelta(days=7):
                validation['warnings'].append(f"Start date {start_date} is in the future")
            
        except ValueError as e:
            validation['valid'] = False
            validation['errors'].append(f"Invalid date format: {str(e)}")
        
        # Add availability prediction
        if validation['valid'] and data_source in self.source_mappings:
            predictor_key = self.source_mappings[data_source]['predictor_key']
            prediction = self.predictor.predict_availability(predictor_key, lat, lon, start_date)
            
            validation['availability_prediction'] = prediction
            
            if not prediction['available']:
                validation['warnings'].append("Low probability of data availability")
                validation['suggestions'].extend(prediction.get('fallback_options', []))
        
        return validation