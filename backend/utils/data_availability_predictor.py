#!/usr/bin/env python3
"""
Data Availability Predictor - Ensures ocean data is always available
based on coordinates, date, and data source capabilities.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional
import logging
from pathlib import Path

class DataAvailabilityPredictor:
    """
    Predicts and ensures data availability based on ocean coordinates and dates.
    Provides fallback mechanisms and reliability guarantees.
    """
    
    def __init__(self):
        """Initialize the data availability predictor."""
        self.logger = logging.getLogger(__name__)
        
        # Define temporal coverage for each data source
        self.temporal_coverage = {
            # Copernicus Marine Service datasets
            'copernicus_sst': {
                'start_date': '2021-01-01',
                'end_date': 'present',
                'reliability': 0.98,  # 98% reliable
                'description': 'Global SST Level 4 Daily'
            },
            'copernicus_salinity': {
                'start_date': '2022-06-01',
                'end_date': 'present', 
                'reliability': 0.95,
                'description': 'Global Ocean Salinity'
            },
            'copernicus_currents': {
                'start_date': '2022-06-01',
                'end_date': 'present',
                'reliability': 0.95,
                'description': 'Global Ocean Currents'
            },
            'copernicus_wave': {
                'start_date': '2022-06-01',
                'end_date': 'present',
                'reliability': 0.93,
                'description': 'Global Ocean Waves'
            },
            'copernicus_chlorophyll': {
                'start_date': '2021-11-01',
                'end_date': 'present',
                'reliability': 0.92,
                'description': 'Global Ocean Chlorophyll'
            },
            'copernicus_ph': {
                'start_date': '2021-11-01',
                'end_date': 'present',
                'reliability': 0.90,
                'description': 'Global Ocean pH'
            },
            'copernicus_biogeochemistry': {
                'start_date': '2021-11-01',
                'end_date': 'present',
                'reliability': 0.88,
                'description': 'Global Ocean Biogeochemistry'
            },
            
            # Alternative data sources
            'obis_biodiversity': {
                'start_date': '1972-01-01',
                'end_date': 'present',
                'reliability': 1.0,  # Always available (API-based)
                'description': 'OBIS Marine Biodiversity'
            },
            'ncei_microplastics': {
                'start_date': '1972-01-01',
                'end_date': 'present',
                'reliability': 1.0,  # Always available (predictive model)
                'description': 'NCEI Marine Microplastics'
            }
        }
        
        # Define spatial coverage limitations
        self.spatial_limitations = {
            'arctic_ice_regions': {
                'bounds': {'lat_min': 80, 'lat_max': 90, 'lon_min': -180, 'lon_max': 180},
                'affected_sources': ['copernicus_sst', 'copernicus_salinity'],
                'reliability_reduction': 0.3
            },
            'antarctic_ice_regions': {
                'bounds': {'lat_min': -90, 'lat_max': -70, 'lon_min': -180, 'lon_max': 180},
                'affected_sources': ['copernicus_sst', 'copernicus_salinity'],
                'reliability_reduction': 0.3
            },
            'coastal_shallow_areas': {
                'bounds': 'near_coastlines',  # Special handling needed
                'affected_sources': ['copernicus_currents', 'copernicus_wave'],
                'reliability_reduction': 0.1
            }
        }
        
        # Define fallback strategies
        self.fallback_strategies = {
            'temporal_fallback': {
                'strategy': 'use_nearest_available_date',
                'max_offset_days': 7
            },
            'spatial_fallback': {
                'strategy': 'expand_search_radius',
                'max_radius_km': 200
            },
            'source_fallback': {
                'strategy': 'alternative_data_source',
                'alternatives': {
                    'copernicus_biodiversity': 'obis_biodiversity',
                    'pangaea_microplastics': 'ncei_microplastics'
                }
            }
        }
        
        # Minimum common date (empirically determined)
        self.minimum_common_date = '2022-06-01'
        
        self.logger.info("Data availability predictor initialized")
    
    def predict_availability(self, data_source: str, lat: float, lon: float, 
                           date: str) -> Dict[str, Any]:
        """
        Predict data availability for specific source, location, and date.
        
        Args:
            data_source: Name of the data source
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees
            date: Date in YYYY-MM-DD format
            
        Returns:
            Dictionary with availability prediction and confidence
        """
        prediction = {
            'available': False,
            'confidence': 0.0,
            'reasons': [],
            'fallback_options': [],
            'recommended_action': None
        }
        
        # Check if data source exists
        if data_source not in self.temporal_coverage:
            prediction['reasons'].append(f"Unknown data source: {data_source}")
            prediction['recommended_action'] = "Use alternative data source"
            return prediction
        
        source_info = self.temporal_coverage[data_source]
        
        # Check temporal coverage
        temporal_available, temporal_confidence = self._check_temporal_coverage(
            source_info, date
        )
        
        if not temporal_available:
            prediction['reasons'].append(f"Date {date} outside temporal coverage")
            prediction['fallback_options'].append(
                self._suggest_temporal_fallback(source_info, date)
            )
        
        # Check spatial coverage
        spatial_available, spatial_confidence = self._check_spatial_coverage(
            data_source, lat, lon
        )
        
        if not spatial_available:
            prediction['reasons'].append(f"Location ({lat}, {lon}) has limited coverage")
            prediction['fallback_options'].append(
                self._suggest_spatial_fallback(lat, lon)
            )
        
        # Check coordinate validity
        coord_valid, coord_confidence = self._check_coordinate_validity(lat, lon)
        
        if not coord_valid:
            prediction['reasons'].append(f"Invalid ocean coordinates: ({lat}, {lon})")
            prediction['recommended_action'] = "Use valid ocean coordinates"
            return prediction
        
        # Calculate overall availability and confidence
        if temporal_available and spatial_available and coord_valid:
            prediction['available'] = True
            prediction['confidence'] = min(
                temporal_confidence,
                spatial_confidence, 
                coord_confidence,
                source_info['reliability']
            )
            prediction['recommended_action'] = "Proceed with query"
        else:
            # Calculate partial confidence for fallback scenarios
            prediction['confidence'] = (
                temporal_confidence * 0.4 +
                spatial_confidence * 0.3 +
                coord_confidence * 0.3
            )
            
            if prediction['fallback_options']:
                prediction['recommended_action'] = "Use fallback strategy"
            else:
                prediction['recommended_action'] = "Query likely to fail"
        
        return prediction
    
    def _check_temporal_coverage(self, source_info: Dict[str, Any], 
                                date: str) -> Tuple[bool, float]:
        """Check if date falls within temporal coverage."""
        try:
            query_date = datetime.strptime(date, '%Y-%m-%d')
            start_date = datetime.strptime(source_info['start_date'], '%Y-%m-%d')
            
            # Handle 'present' end date
            if source_info['end_date'] == 'present':
                end_date = datetime.now()
            else:
                end_date = datetime.strptime(source_info['end_date'], '%Y-%m-%d')
            
            if start_date <= query_date <= end_date:
                # Calculate confidence based on how recent/distant the date is
                days_from_start = (query_date - start_date).days
                days_to_end = (end_date - query_date).days
                
                # Higher confidence for recent dates
                if days_to_end <= 30:  # Within last month
                    confidence = 0.95
                elif days_to_end <= 365:  # Within last year
                    confidence = 0.90
                else:  # Older dates
                    confidence = 0.80
                
                return True, confidence
            else:
                return False, 0.0
                
        except ValueError:
            return False, 0.0
    
    def _check_spatial_coverage(self, data_source: str, lat: float, 
                               lon: float) -> Tuple[bool, float]:
        """Check spatial coverage limitations."""
        confidence = 1.0
        
        # Check for spatial limitations
        for limitation_name, limitation in self.spatial_limitations.items():
            if data_source in limitation.get('affected_sources', []):
                if self._point_in_limitation_area(lat, lon, limitation):
                    confidence -= limitation['reliability_reduction']
        
        # Ensure confidence doesn't go below 0
        confidence = max(0.0, confidence)
        
        # Consider available if confidence > 0.5
        available = confidence > 0.5
        
        return available, confidence
    
    def _point_in_limitation_area(self, lat: float, lon: float, 
                                 limitation: Dict[str, Any]) -> bool:
        """Check if point falls within a spatial limitation area."""
        bounds = limitation['bounds']
        
        if isinstance(bounds, dict):
            return (bounds['lat_min'] <= lat <= bounds['lat_max'] and
                   bounds['lon_min'] <= lon <= bounds['lon_max'])
        elif bounds == 'near_coastlines':
            # Simplified coastline detection - in practice, this would use
            # a more sophisticated land/ocean mask
            return False  # For now, assume all points are not near coastlines
        
        return False
    
    def _check_coordinate_validity(self, lat: float, lon: float) -> Tuple[bool, float]:
        """Check if coordinates are valid and in ocean."""
        # Basic coordinate validation
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return False, 0.0
        
        # Simple ocean check (in reality, would use ocean mask)
        # For now, assume all valid coordinates are ocean
        confidence = 0.9  # High confidence for basic validation
        
        return True, confidence
    
    def _suggest_temporal_fallback(self, source_info: Dict[str, Any], 
                                  date: str) -> Dict[str, Any]:
        """Suggest temporal fallback options."""
        try:
            query_date = datetime.strptime(date, '%Y-%m-%d')
            start_date = datetime.strptime(source_info['start_date'], '%Y-%m-%d')
            
            if source_info['end_date'] == 'present':
                end_date = datetime.now()
            else:
                end_date = datetime.strptime(source_info['end_date'], '%Y-%m-%d')
            
            if query_date < start_date:
                # Suggest earliest available date
                suggested_date = start_date.strftime('%Y-%m-%d')
                return {
                    'type': 'temporal_fallback',
                    'suggested_date': suggested_date,
                    'reason': f'Use earliest available date: {suggested_date}'
                }
            elif query_date > end_date:
                # Suggest latest available date
                suggested_date = end_date.strftime('%Y-%m-%d')
                return {
                    'type': 'temporal_fallback',
                    'suggested_date': suggested_date,
                    'reason': f'Use latest available date: {suggested_date}'
                }
        except ValueError:
            pass
        
        return {
            'type': 'temporal_fallback',
            'suggested_date': self.minimum_common_date,
            'reason': f'Use minimum common date: {self.minimum_common_date}'
        }
    
    def _suggest_spatial_fallback(self, lat: float, lon: float) -> Dict[str, Any]:
        """Suggest spatial fallback options."""
        return {
            'type': 'spatial_fallback',
            'strategy': 'expand_search_radius',
            'suggested_radius_km': 100,
            'reason': 'Expand search radius to find nearby data'
        }
    
    def get_guaranteed_availability_window(self) -> Dict[str, Any]:
        """Get the date range where all data sources are guaranteed available."""
        # Find the latest start date among all sources
        start_dates = []
        for source_info in self.temporal_coverage.values():
            if source_info['start_date'] != '1972-01-01':  # Skip very old sources
                start_dates.append(source_info['start_date'])
        
        guaranteed_start = max(start_dates) if start_dates else self.minimum_common_date
        
        return {
            'guaranteed_start_date': guaranteed_start,
            'guaranteed_end_date': 'present',
            'coverage_percentage': 100,
            'included_sources': list(self.temporal_coverage.keys()),
            'recommendation': f'Use dates from {guaranteed_start} onwards for guaranteed availability'
        }
    
    def predict_batch_availability(self, requests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Predict availability for a batch of requests."""
        results = []
        overall_stats = {
            'total_requests': len(requests),
            'predicted_successful': 0,
            'predicted_failed': 0,
            'average_confidence': 0.0
        }
        
        total_confidence = 0.0
        
        for request in requests:
            prediction = self.predict_availability(
                request['data_source'],
                request['lat'],
                request['lon'],
                request['date']
            )
            
            results.append({
                'request': request,
                'prediction': prediction
            })
            
            if prediction['available']:
                overall_stats['predicted_successful'] += 1
            else:
                overall_stats['predicted_failed'] += 1
            
            total_confidence += prediction['confidence']
        
        overall_stats['average_confidence'] = total_confidence / len(requests) if requests else 0.0
        overall_stats['success_rate'] = (overall_stats['predicted_successful'] / len(requests) * 100) if requests else 0.0
        
        return {
            'batch_results': results,
            'overall_stats': overall_stats,
            'recommendations': self._generate_batch_recommendations(results)
        }
    
    def _generate_batch_recommendations(self, results: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on batch prediction results."""
        recommendations = []
        
        failed_count = sum(1 for r in results if not r['prediction']['available'])
        total_count = len(results)
        
        if failed_count == 0:
            recommendations.append("✅ All requests predicted to succeed")
        elif failed_count < total_count * 0.1:  # Less than 10% failure
            recommendations.append("✅ High success rate expected")
            recommendations.append("Consider implementing fallback for failed requests")
        elif failed_count < total_count * 0.3:  # Less than 30% failure
            recommendations.append("⚠️ Moderate success rate expected")
            recommendations.append("Implement fallback strategies for better reliability")
        else:
            recommendations.append("❌ Low success rate expected")
            recommendations.append("Consider using guaranteed availability window")
            guaranteed = self.get_guaranteed_availability_window()
            recommendations.append(f"Use dates from {guaranteed['guaranteed_start_date']} onwards")
        
        return recommendations
    
    def get_data_source_reliability(self) -> Dict[str, Any]:
        """Get reliability information for all data sources."""
        return {
            source: {
                'reliability_score': info['reliability'],
                'temporal_coverage': f"{info['start_date']} to {info['end_date']}",
                'description': info['description'],
                'recommended_use': 'primary' if info['reliability'] >= 0.9 else 'secondary'
            }
            for source, info in self.temporal_coverage.items()
        }