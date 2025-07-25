#!/usr/bin/env python3
"""
Coverage mapping utilities for ocean climate data APIs.
Creates comprehensive coverage maps showing spatial/temporal availability.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import logging

class CoverageMapper:
    """Creates coverage maps for ocean climate data APIs."""
    
    def __init__(self, output_dir: Path):
        """
        Initialize coverage mapper.
        
        Args:
            output_dir: Directory to save coverage maps
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger('coverage_mapper')
        self.logger.setLevel(logging.INFO)
        
        # Coverage map structure
        self.coverage_template = {
            'metadata': {
                'created_at': None,
                'version': '1.0',
                'description': 'API coverage information for ocean climate data',
                'coordinate_system': 'WGS84'
            },
            'spatial_coverage': {},
            'temporal_coverage': {},
            'parameter_coverage': {},
            'api_specific_info': {},
            'quality_assessment': {},
            'integration_notes': {}
        }
        
        self.logger.info(f"Coverage mapper initialized, output dir: {output_dir}")
    
    def create_comprehensive_coverage_map(self, api_clients: List[Any]) -> Dict[str, Any]:
        """
        Create comprehensive coverage map from multiple API clients.
        
        Args:
            api_clients: List of initialized API client objects
            
        Returns:
            Dictionary with comprehensive coverage information
        """
        self.logger.info("Creating comprehensive coverage map...")
        
        # Initialize comprehensive map
        comprehensive_map = {
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'version': '1.0',
                'description': 'Comprehensive ocean climate data API coverage',
                'apis_analyzed': len(api_clients),
                'coordinate_system': 'WGS84'
            },
            'apis': {},
            'global_coverage': {
                'spatial_bounds': {'lat_min': 90, 'lat_max': -90, 'lon_min': 180, 'lon_max': -180},
                'temporal_bounds': {'earliest': None, 'latest': None},
                'parameters': set(),
                'overlapping_coverage': {},
                'data_gaps': {}
            },
            'integration_matrix': {},
            'recommendations': {}
        }
        
        # Analyze each API
        for client in api_clients:
            try:
                self.logger.info(f"Analyzing coverage for {client.api_name}...")
                
                # Get coverage information
                coverage_info = client.discover_coverage()
                api_key = client.api_name.lower().replace(' ', '_').replace('-', '_')
                
                # Store API-specific coverage
                comprehensive_map['apis'][api_key] = self._process_api_coverage(coverage_info)
                
                # Update global coverage
                self._update_global_coverage(comprehensive_map['global_coverage'], coverage_info)
                
                # Analyze parameter overlap
                self._analyze_parameter_overlap(comprehensive_map, api_key, coverage_info)
                
            except Exception as e:
                self.logger.error(f"Failed to analyze {client.api_name}: {e}")
                comprehensive_map['apis'][api_key] = {'error': str(e), 'status': 'failed'}
        
        # Convert sets to lists for JSON serialization
        comprehensive_map['global_coverage']['parameters'] = sorted(list(comprehensive_map['global_coverage']['parameters']))
        
        # Generate integration recommendations
        comprehensive_map['recommendations'] = self._generate_integration_recommendations(comprehensive_map)
        
        # Save comprehensive map
        self._save_coverage_map(comprehensive_map, 'comprehensive_coverage_map.json')
        
        self.logger.info("Comprehensive coverage map created successfully")
        return comprehensive_map
    
    def _process_api_coverage(self, coverage_info: Dict[str, Any]) -> Dict[str, Any]:
        """Process coverage information from a single API."""
        
        processed = {
            'api_name': coverage_info.get('api_name', 'Unknown'),
            'status': coverage_info.get('connection_status', {}).get('status', 'unknown'),
            'discovery_timestamp': coverage_info.get('discovery_timestamp'),
            'spatial_coverage': self._extract_spatial_coverage(coverage_info),
            'temporal_coverage': self._extract_temporal_coverage(coverage_info),
            'parameter_coverage': self._extract_parameter_coverage(coverage_info),
            'data_access': self._extract_access_info(coverage_info),
            'quality_indicators': self._assess_data_quality(coverage_info),
            'strengths': [],
            'limitations': []
        }
        
        # Add API-specific strengths and limitations
        processed['strengths'], processed['limitations'] = self._assess_api_capabilities(coverage_info)
        
        return processed
    
    def _extract_spatial_coverage(self, coverage_info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract spatial coverage information."""
        
        spatial = {
            'global_coverage': False,
            'regional_coverage': [],
            'bounds': {'lat_min': None, 'lat_max': None, 'lon_min': None, 'lon_max': None},
            'resolution': 'unknown',
            'coverage_type': 'unknown'
        }
        
        # Look for spatial bounds in various locations
        if 'global_coverage' in coverage_info:
            spatial['global_coverage'] = coverage_info['global_coverage'].get('available', False)
            if 'spatial_bounds' in coverage_info['global_coverage']:
                spatial['bounds'] = coverage_info['global_coverage']['spatial_bounds']
        
        if 'regional_coverage' in coverage_info:
            spatial['regional_coverage'] = coverage_info['regional_coverage'].get('regions', [])
        
        if 'geographic_coverage' in coverage_info:
            geo_cov = coverage_info['geographic_coverage']
            if 'spatial_bounds' in geo_cov:
                spatial['bounds'] = geo_cov['spatial_bounds']
        
        return spatial
    
    def _extract_temporal_coverage(self, coverage_info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract temporal coverage information."""
        
        temporal = {
            'historical_data': False,
            'real_time_data': False,
            'earliest_date': None,
            'latest_date': None,
            'update_frequency': 'unknown',
            'temporal_resolution': 'unknown',
            'data_latency': 'unknown'
        }
        
        # Look for temporal information
        if 'temporal_coverage' in coverage_info:
            temp_cov = coverage_info['temporal_coverage']
            temporal.update({
                'historical_data': temp_cov.get('historical_archive', False),
                'real_time_data': temp_cov.get('real_time_availability', False),
                'earliest_date': temp_cov.get('earliest_data'),
                'latest_date': temp_cov.get('latest_data'),
                'data_latency': temp_cov.get('real_time_lag', 'unknown')
            })
        
        return temporal
    
    def _extract_parameter_coverage(self, coverage_info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract parameter coverage information."""
        
        parameters = {
            'total_parameters': 0,
            'parameter_list': [],
            'parameter_categories': {},
            'data_quality': 'unknown'
        }
        
        # Extract parameters from various locations
        if 'parameter_availability' in coverage_info:
            param_avail = coverage_info['parameter_availability']
            if isinstance(param_avail, dict):
                parameters['parameter_list'] = list(param_avail.keys())
                parameters['total_parameters'] = len(param_avail)
                if 'parameters_by_category' in param_avail:
                    parameters['parameter_categories'] = param_avail['parameters_by_category']
        
        if 'research_areas' in coverage_info:
            # PANGAEA-style parameter organization
            for area_name, area_data in coverage_info['research_areas'].items():
                if 'parameters' in area_data:
                    parameters['parameter_categories'][area_name] = area_data['parameters']
                    parameters['parameter_list'].extend(area_data['parameters'])
            
            parameters['parameter_list'] = list(set(parameters['parameter_list']))
            parameters['total_parameters'] = len(parameters['parameter_list'])
        
        return parameters
    
    def _extract_access_info(self, coverage_info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract data access information."""
        
        access = {
            'access_methods': [],
            'authentication_required': False,
            'rate_limits': 'unknown',
            'data_formats': [],
            'api_endpoints': []
        }
        
        if 'access_methods' in coverage_info:
            access['access_methods'] = coverage_info['access_methods']
        
        return access
    
    def _assess_data_quality(self, coverage_info: Dict[str, Any]) -> Dict[str, Any]:
        """Assess data quality indicators."""
        
        quality = {
            'peer_reviewed': False,
            'real_time_qc': False,
            'uncertainty_info': False,
            'metadata_completeness': 'unknown',
            'traceability': 'unknown'
        }
        
        # Look for quality indicators in coverage info
        api_name = coverage_info.get('api_name', '').lower()
        
        if 'pangaea' in api_name:
            quality.update({
                'peer_reviewed': True,
                'metadata_completeness': 'high',
                'traceability': 'doi_based'
            })
        elif 'copernicus' in api_name:
            quality.update({
                'real_time_qc': True,
                'metadata_completeness': 'high',
                'traceability': 'operational'
            })
        elif 'noaa' in api_name:
            quality.update({
                'real_time_qc': True,
                'uncertainty_info': True,
                'traceability': 'governmental'
            })
        
        return quality
    
    def _assess_api_capabilities(self, coverage_info: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Assess API strengths and limitations."""
        
        api_name = coverage_info.get('api_name', '').lower()
        strengths = []
        limitations = []
        
        if 'copernicus' in api_name:
            strengths.extend([
                'Global ocean coverage',
                'No download required (API subset)',
                'Pre-calculated climate indicators',
                'Multiple data products',
                'High spatial resolution'
            ])
            limitations.extend([
                'Authentication required',
                'Complex dataset structure',
                'Learning curve for new users'
            ])
        
        elif 'noaa' in api_name and 'co-ops' in api_name:
            strengths.extend([
                'Real-time coastal data',
                'Long historical records',
                'Built-in trend analysis',
                'No authentication required',
                'Simple API structure'
            ])
            limitations.extend([
                'Limited to US coastal areas',
                'Station-based (not continuous coverage)',
                'Limited open ocean data'
            ])
        
        elif 'pangaea' in api_name:
            strengths.extend([
                'Peer-reviewed research data',
                'Comprehensive microplastics data',
                'DOI-based citations',
                'High data quality',
                'Long-term datasets'
            ])
            limitations.extend([
                'Dataset discovery required',
                'Download-based access',
                'Variable data formats',
                'Research focus (less operational data)'
            ])
        
        return strengths, limitations
    
    def _update_global_coverage(self, global_coverage: Dict[str, Any], coverage_info: Dict[str, Any]):
        """Update global coverage information with data from an API."""
        
        # Update spatial bounds
        spatial_bounds = None
        if 'global_coverage' in coverage_info and 'spatial_bounds' in coverage_info['global_coverage']:
            spatial_bounds = coverage_info['global_coverage']['spatial_bounds']
        elif 'geographic_coverage' in coverage_info and 'spatial_bounds' in coverage_info['geographic_coverage']:
            spatial_bounds = coverage_info['geographic_coverage']['spatial_bounds']
        
        if spatial_bounds:
            bounds = global_coverage['spatial_bounds']
            bounds['lat_min'] = min(bounds.get('lat_min', 90), spatial_bounds.get('lat_min', 90))
            bounds['lat_max'] = max(bounds.get('lat_max', -90), spatial_bounds.get('lat_max', -90))
            bounds['lon_min'] = min(bounds.get('lon_min', 180), spatial_bounds.get('lon_min', 180))
            bounds['lon_max'] = max(bounds.get('lon_max', -180), spatial_bounds.get('lon_max', -180))
        
        # Update temporal bounds
        temporal_bounds = None
        if 'temporal_coverage' in coverage_info:
            temp_cov = coverage_info['temporal_coverage']
            if 'earliest_data' in temp_cov:
                earliest = temp_cov['earliest_data']
                if not global_coverage['temporal_bounds']['earliest'] or earliest < global_coverage['temporal_bounds']['earliest']:
                    global_coverage['temporal_bounds']['earliest'] = earliest
            
            if 'latest_data' in temp_cov:
                latest = temp_cov['latest_data']
                if not global_coverage['temporal_bounds']['latest'] or latest > global_coverage['temporal_bounds']['latest']:
                    global_coverage['temporal_bounds']['latest'] = latest
        
        # Update parameters
        if 'parameter_availability' in coverage_info:
            param_avail = coverage_info['parameter_availability']
            if isinstance(param_avail, dict):
                global_coverage['parameters'].update(param_avail.keys())
            elif 'unique_parameters' in param_avail:
                global_coverage['parameters'].update(param_avail['unique_parameters'])
    
    def _analyze_parameter_overlap(self, comprehensive_map: Dict[str, Any], api_key: str, coverage_info: Dict[str, Any]):
        """Analyze parameter overlap between APIs."""
        
        if 'overlapping_coverage' not in comprehensive_map['global_coverage']:
            comprehensive_map['global_coverage']['overlapping_coverage'] = {}
        
        # Extract parameters for this API
        api_parameters = set()
        if 'parameter_availability' in coverage_info:
            param_avail = coverage_info['parameter_availability']
            if isinstance(param_avail, dict):
                api_parameters.update(param_avail.keys())
            elif 'unique_parameters' in param_avail:
                api_parameters.update(param_avail['unique_parameters'])
        
        # Compare with existing APIs
        overlap_info = comprehensive_map['global_coverage']['overlapping_coverage']
        for existing_api, existing_data in comprehensive_map['apis'].items():
            if existing_api == api_key:
                continue
            
            existing_params = set(existing_data.get('parameter_coverage', {}).get('parameter_list', []))
            
            common_params = api_parameters.intersection(existing_params)
            if common_params:
                pair_key = f"{min(api_key, existing_api)}_{max(api_key, existing_api)}"
                overlap_info[pair_key] = {
                    'apis': [api_key, existing_api],
                    'common_parameters': sorted(list(common_params)),
                    'overlap_count': len(common_params),
                    'complementary_potential': len(common_params) > 5
                }
    
    def _generate_integration_recommendations(self, comprehensive_map: Dict[str, Any]) -> Dict[str, Any]:
        """Generate recommendations for API integration."""
        
        recommendations = {
            'primary_apis': [],
            'complementary_combinations': [],
            'data_type_recommendations': {},
            'coverage_gaps': [],
            'integration_strategies': []
        }
        
        # Analyze API capabilities
        api_scores = {}
        for api_key, api_data in comprehensive_map['apis'].items():
            if api_data.get('status') != 'failed':
                score = self._calculate_api_score(api_data)
                api_scores[api_key] = score
        
        # Rank primary APIs
        sorted_apis = sorted(api_scores.items(), key=lambda x: x[1], reverse=True)
        recommendations['primary_apis'] = [
            {'api': api, 'score': score, 'strengths': comprehensive_map['apis'][api].get('strengths', [])}
            for api, score in sorted_apis[:3]
        ]
        
        # Identify complementary combinations
        overlap_info = comprehensive_map['global_coverage'].get('overlapping_coverage', {})
        for overlap_key, overlap_data in overlap_info.items():
            if overlap_data['complementary_potential']:
                recommendations['complementary_combinations'].append({
                    'apis': overlap_data['apis'],
                    'common_parameters': len(overlap_data['common_parameters']),
                    'integration_benefit': 'cross_validation_and_gap_filling'
                })
        
        # Data type recommendations
        recommendations['data_type_recommendations'] = {
            'real_time_monitoring': self._get_best_apis_for_capability(comprehensive_map, 'real_time_data'),
            'historical_analysis': self._get_best_apis_for_capability(comprehensive_map, 'historical_data'),
            'global_coverage': self._get_best_apis_for_capability(comprehensive_map, 'global_coverage'),
            'research_quality': self._get_best_apis_for_capability(comprehensive_map, 'peer_reviewed')
        }
        
        return recommendations
    
    def _calculate_api_score(self, api_data: Dict[str, Any]) -> float:
        """Calculate overall score for an API based on capabilities."""
        
        score = 0.0
        
        # Spatial coverage score
        if api_data.get('spatial_coverage', {}).get('global_coverage'):
            score += 3.0
        elif api_data.get('spatial_coverage', {}).get('regional_coverage'):
            score += 2.0
        else:
            score += 1.0
        
        # Parameter coverage score
        param_count = api_data.get('parameter_coverage', {}).get('total_parameters', 0)
        if param_count > 10:
            score += 3.0
        elif param_count > 5:
            score += 2.0
        else:
            score += 1.0
        
        # Data quality score
        quality = api_data.get('quality_indicators', {})
        if quality.get('peer_reviewed'):
            score += 2.0
        if quality.get('real_time_qc'):
            score += 1.0
        if quality.get('uncertainty_info'):
            score += 1.0
        
        # Temporal coverage score
        temporal = api_data.get('temporal_coverage', {})
        if temporal.get('real_time_data'):
            score += 1.0
        if temporal.get('historical_data'):
            score += 1.0
        
        return score
    
    def _get_best_apis_for_capability(self, comprehensive_map: Dict[str, Any], capability: str) -> List[str]:
        """Get APIs that are best for a specific capability."""
        
        best_apis = []
        
        for api_key, api_data in comprehensive_map['apis'].items():
            if api_data.get('status') == 'failed':
                continue
            
            if capability == 'real_time_data':
                if api_data.get('temporal_coverage', {}).get('real_time_data'):
                    best_apis.append(api_key)
            elif capability == 'historical_data':
                if api_data.get('temporal_coverage', {}).get('historical_data'):
                    best_apis.append(api_key)
            elif capability == 'global_coverage':
                if api_data.get('spatial_coverage', {}).get('global_coverage'):
                    best_apis.append(api_key)
            elif capability == 'peer_reviewed':
                if api_data.get('quality_indicators', {}).get('peer_reviewed'):
                    best_apis.append(api_key)
        
        return best_apis
    
    def _save_coverage_map(self, coverage_map: Dict[str, Any], filename: str):
        """Save coverage map to file."""
        
        output_file = self.output_dir / filename
        
        try:
            with open(output_file, 'w') as f:
                json.dump(coverage_map, f, indent=2, default=str)
            
            self.logger.info(f"Coverage map saved: {output_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save coverage map: {e}")
    
    def create_api_specific_map(self, api_client: Any) -> Dict[str, Any]:
        """Create detailed coverage map for a specific API."""
        
        self.logger.info(f"Creating API-specific coverage map for {api_client.api_name}")
        
        coverage_info = api_client.discover_coverage()
        api_map = self._process_api_coverage(coverage_info)
        
        # Add detailed API-specific information
        api_map['detailed_info'] = coverage_info
        api_map['metadata'] = {
            'created_at': datetime.now().isoformat(),
            'api_name': api_client.api_name,
            'version': '1.0'
        }
        
        # Save API-specific map
        filename = f"{api_client.api_name.lower().replace(' ', '_').replace('-', '_')}_coverage.json"
        self._save_coverage_map(api_map, filename)
        
        return api_map