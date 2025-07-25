#!/usr/bin/env python3
"""
OBIS (Ocean Biodiversity Information System) API client.
Provides reliable global marine biodiversity data with API access.
"""

import requests
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
from pathlib import Path

from .base_client import BaseAPIClient

class OBISClient(BaseAPIClient):
    """
    Client for OBIS (Ocean Biodiversity Information System) API.
    
    Features:
    - Global marine biodiversity data
    - 45+ million observations of 120,000+ species
    - Real API access (not research-dependent)
    - Standardized taxonomic data
    - Geographic and temporal filtering
    """
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize OBIS API client."""
        super().__init__(
            api_name="OBIS (Ocean Biodiversity Information System)",
            base_url="https://api.obis.org",
            cache_dir=cache_dir
        )
        
        # Set coverage information
        self.coverage_info = {
            'spatial_bounds': {
                'lat_min': -90, 'lat_max': 90,
                'lon_min': -180, 'lon_max': 180
            },
            'temporal_bounds': {
                'start': '1972-01-01',  # Based on historical data
                'end': datetime.now().strftime('%Y-%m-%d')
            },
            'available_parameters': [
                'species_occurrence', 'taxonomic_classification', 
                'abundance', 'biomass', 'environmental_data'
            ],
            'datasets': {},
            'last_updated': datetime.now().isoformat()
        }
        
        self.logger.info("OBIS client initialized successfully")
    
    def query_data(self, lat: float, lon: float, start_date: str, end_date: str,
                  parameters: List[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Query marine biodiversity data from OBIS API.
        
        Args:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            parameters: Not used (OBIS returns standard occurrence data)
            **kwargs: Additional parameters (radius, taxon, etc.)
            
        Returns:
            Dictionary with biodiversity data
        """
        self.logger.info(f"Querying OBIS biodiversity data for {lat:.4f}, {lon:.4f}")
        
        # Validate coordinates
        if not self.validate_coordinates(lat, lon):
            raise ValueError(f"Invalid coordinates: {lat}, {lon}")
        
        if not self.validate_time_range(start_date, end_date):
            raise ValueError(f"Invalid time range: {start_date} to {end_date}")
        
        try:
            # Set search radius (default 50km)
            radius = kwargs.get('radius', 50)  # km
            
            # Build API request parameters
            params = {
                'geometry': f'POINT({lon} {lat})',
                'radius': radius * 1000,  # Convert to meters
                'startdate': start_date,
                'enddate': end_date,
                'size': kwargs.get('limit', 100),  # Limit results
                'offset': kwargs.get('offset', 0)
            }
            
            # Add taxon filter if specified
            if 'taxon' in kwargs:
                params['taxon'] = kwargs['taxon']
            
            # Make API request
            cache_key = self._generate_cache_key('occurrence', params)
            cached_data = self._load_cached_response(cache_key, max_age_hours=24)
            
            if cached_data:
                self.logger.info(f"Using cached OBIS data for {lat}, {lon}")
                return self._format_response(cached_data, lat, lon, cached=True)
            
            # Query OBIS API
            response = self._make_request(f"{self.base_url}/occurrence", params=params)
            data = response.json()
            
            # Cache successful response
            self._cache_response(cache_key, data)
            
            return self._format_response(data, lat, lon, cached=False)
            
        except Exception as e:
            self.logger.error(f"Error querying OBIS data: {e}")
            return {
                'api_name': self.api_name,
                'status': 'error',
                'error': str(e),
                'coordinates': {'lat': lat, 'lon': lon},
                'message': 'OBIS API query failed'
            }
    
    def _format_response(self, data: Dict[str, Any], lat: float, lon: float, 
                        cached: bool = False) -> Dict[str, Any]:
        """Format OBIS API response for consistency."""
        
        # Extract key information
        results = data.get('results', [])
        total_count = data.get('total', len(results))
        
        # Process species data
        species_summary = {}
        unique_species = set()
        phylum_counts = {}
        
        for record in results:
            # Extract species information
            species_name = record.get('species')
            phylum = record.get('phylum', 'Unknown')
            
            if species_name:
                unique_species.add(species_name)
                
                # Count by phylum
                phylum_counts[phylum] = phylum_counts.get(phylum, 0) + 1
                
                # Store species details
                if species_name not in species_summary:
                    species_summary[species_name] = {
                        'scientific_name': species_name,
                        'common_name': record.get('vernacularName'),
                        'phylum': phylum,
                        'class': record.get('class'),
                        'family': record.get('family'),
                        'genus': record.get('genus'),
                        'occurrences': 0,
                        'depth_range': [],
                        'date_range': []
                    }
                
                species_summary[species_name]['occurrences'] += 1
                
                # Add depth information
                if record.get('minimumDepthInMeters'):
                    species_summary[species_name]['depth_range'].append(
                        float(record['minimumDepthInMeters'])
                    )
                
                # Add date information
                if record.get('eventDate'):
                    species_summary[species_name]['date_range'].append(
                        record['eventDate']
                    )
        
        # Calculate diversity metrics
        diversity_metrics = {
            'total_species': len(unique_species),
            'total_occurrences': total_count,
            'phylum_diversity': len(phylum_counts),
            'dominant_phyla': sorted(phylum_counts.items(), 
                                   key=lambda x: x[1], reverse=True)[:5]
        }
        
        # Format final response
        return {
            'api_name': self.api_name,
            'status': 'success',
            'coordinates': {'lat': lat, 'lon': lon},
            'query_timestamp': datetime.now().isoformat(),
            'cached': cached,
            'data': {
                'diversity_metrics': diversity_metrics,
                'species_summary': list(species_summary.values())[:20],  # Top 20 species
                'phylum_distribution': phylum_counts,
                'raw_occurrence_count': total_count,
                'search_radius_km': 50
            },
            'data_source': 'OBIS API - 45M+ observations from 500+ institutions',
            'coverage': 'Global ocean coverage with standardized taxonomy',
            'message': f'Found {len(unique_species)} species in {total_count} occurrences'
        }
    
    def get_taxon_info(self, taxon_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific taxon."""
        try:
            params = {'taxon': taxon_name}
            response = self._make_request(f"{self.base_url}/taxon", params=params)
            return {
                'status': 'success',
                'taxon': taxon_name,
                'data': response.json()
            }
        except Exception as e:
            return {
                'status': 'error',
                'taxon': taxon_name,
                'error': str(e)
            }
    
    def discover_coverage(self) -> Dict[str, Any]:
        """Discover OBIS data coverage."""
        self.logger.info("Discovering OBIS coverage...")
        
        try:
            # Get basic statistics
            stats_response = self._make_request(f"{self.base_url}/statistics")
            stats = stats_response.json()
            
            coverage_data = {
                'api_name': self.api_name,
                'discovery_timestamp': datetime.now().isoformat(),
                'global_coverage': self.coverage_info['spatial_bounds'],
                'temporal_coverage': self.coverage_info['temporal_bounds'],
                'statistics': stats,
                'connection_status': {'status': 'connected', 'authenticated': True},
                'data_quality': {
                    'source': 'OBIS Network - 30+ regional nodes',
                    'institutions': '500+ contributing institutions',
                    'countries': '56 countries',
                    'observations': '45+ million',
                    'species': '120,000+ marine species',
                    'data_standards': 'Darwin Core compliance'
                }
            }
            
            return coverage_data
            
        except Exception as e:
            self.logger.error(f"OBIS coverage discovery failed: {e}")
            return {
                'api_name': self.api_name,
                'status': 'error',
                'error': str(e),
                'connection_status': {'status': 'error'}
            }
    
    def get_available_datasets(self) -> List[Dict[str, Any]]:
        """Get list of available OBIS datasets."""
        try:
            response = self._make_request(f"{self.base_url}/dataset")
            datasets = response.json().get('results', [])
            
            formatted_datasets = []
            for dataset in datasets[:20]:  # Limit to first 20
                formatted_datasets.append({
                    'key': dataset.get('id'),
                    'dataset_id': dataset.get('id'),
                    'name': dataset.get('title', 'Unknown'),
                    'description': dataset.get('abstract', ''),
                    'institution': dataset.get('institutionName', ''),
                    'records': dataset.get('records', 0),
                    'api_name': self.api_name
                })
            
            return formatted_datasets
            
        except Exception as e:
            self.logger.error(f"Error getting OBIS datasets: {e}")
            return []