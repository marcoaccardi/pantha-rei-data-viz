#!/usr/bin/env python3
"""
Base client class for ocean climate data APIs.
Provides common functionality for all API clients.
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from abc import ABC, abstractmethod
import logging
from pathlib import Path

class BaseAPIClient(ABC):
    """Base class for all API clients with common functionality."""
    
    def __init__(self, api_name: str, base_url: str, cache_dir: Optional[Path] = None):
        """
        Initialize base API client.
        
        Args:
            api_name: Name of the API service
            base_url: Base URL for the API
            cache_dir: Directory for caching responses (optional)
        """
        self.api_name = api_name
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.cache_dir = cache_dir
        
        # Set up logging
        self.logger = logging.getLogger(f"{api_name}_client")
        self.logger.setLevel(logging.INFO)
        
        # Default headers
        self.session.headers.update({
            'User-Agent': f'Ocean-Climate-Research/1.0 (panta-rhei-data-map)',
            'Accept': 'application/json'
        })
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Minimum seconds between requests
        
        # Coverage information (to be populated by subclasses)
        self.coverage_info = {
            'spatial_bounds': None,
            'temporal_bounds': None,
            'available_parameters': [],
            'datasets': {},
            'last_updated': None
        }
        
        self.logger.info(f"Initialized {api_name} client")
    
    def _make_request(self, url: str, params: Dict[str, Any] = None, 
                     timeout: int = 30, retries: int = 3) -> requests.Response:
        """
        Make HTTP request with rate limiting and error handling.
        
        Args:
            url: Request URL
            params: Query parameters
            timeout: Request timeout in seconds
            retries: Number of retry attempts
            
        Returns:
            Response object
        """
        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        
        # Retry logic
        last_exception = None
        for attempt in range(retries + 1):
            try:
                self.logger.debug(f"Request attempt {attempt + 1}: {url}")
                response = self.session.get(url, params=params, timeout=timeout)
                self.last_request_time = time.time()
                
                # Check for HTTP errors
                response.raise_for_status()
                return response
                
            except requests.exceptions.RequestException as e:
                last_exception = e
                self.logger.warning(f"Request attempt {attempt + 1} failed: {e}")
                if attempt < retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    time.sleep(wait_time)
                    
        # All retries failed
        self.logger.error(f"All {retries + 1} attempts failed for {url}")
        raise last_exception
    
    def _cache_response(self, cache_key: str, data: Any) -> None:
        """Cache API response to disk."""
        if not self.cache_dir:
            return
            
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        try:
            with open(cache_file, 'w') as f:
                json.dump({
                    'data': data,
                    'timestamp': datetime.now().isoformat(),
                    'api': self.api_name
                }, f, indent=2, default=str)
            self.logger.debug(f"Cached response: {cache_file}")
        except Exception as e:
            self.logger.warning(f"Failed to cache response: {e}")
    
    def _load_cached_response(self, cache_key: str, max_age_hours: int = 24) -> Optional[Any]:
        """Load cached API response if still valid."""
        if not self.cache_dir:
            return None
            
        cache_file = self.cache_dir / f"{cache_key}.json"
        if not cache_file.exists():
            return None
            
        try:
            with open(cache_file, 'r') as f:
                cached = json.load(f)
                
            # Check cache age
            cache_time = datetime.fromisoformat(cached['timestamp'])
            age_hours = (datetime.now() - cache_time).total_seconds() / 3600
            
            if age_hours <= max_age_hours:
                self.logger.debug(f"Using cached response: {cache_file}")
                return cached['data']
            else:
                self.logger.debug(f"Cache expired ({age_hours:.1f}h): {cache_file}")
                
        except Exception as e:
            self.logger.warning(f"Failed to load cached response: {e}")
            
        return None
    
    def _generate_cache_key(self, endpoint: str, params: Dict[str, Any]) -> str:
        """Generate unique cache key for request."""
        # Sort params for consistent key generation
        sorted_params = sorted(params.items()) if params else []
        param_str = "_".join([f"{k}={v}" for k, v in sorted_params])
        return f"{self.api_name}_{endpoint}_{hash(param_str) % 100000}"
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test API connection and return basic status.
        
        Returns:
            Dictionary with connection status information
        """
        try:
            # Try to access API root or health endpoint
            response = self._make_request(self.base_url, timeout=10)
            
            return {
                'api_name': self.api_name,
                'status': 'connected',
                'response_time_ms': response.elapsed.total_seconds() * 1000,
                'status_code': response.status_code,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'api_name': self.api_name,
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def validate_coordinates(self, lat: float, lon: float) -> bool:
        """
        Validate coordinates for this API.
        
        Args:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees
            
        Returns:
            True if coordinates are valid for this API
        """
        # Basic validation
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return False
            
        # Check against API spatial bounds if available
        if self.coverage_info['spatial_bounds']:
            bounds = self.coverage_info['spatial_bounds']
            if not (bounds['lat_min'] <= lat <= bounds['lat_max'] and
                   bounds['lon_min'] <= lon <= bounds['lon_max']):
                return False
                
        return True
    
    def validate_time_range(self, start_date: str, end_date: str) -> bool:
        """
        Validate time range for this API.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            True if time range is valid for this API
        """
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            # Basic validation - allow same day queries
            if start_dt > end_dt:
                return False
                
            # Check against API temporal bounds if available
            if self.coverage_info['temporal_bounds']:
                bounds = self.coverage_info['temporal_bounds']
                api_start = datetime.strptime(bounds['start'], '%Y-%m-%d')
                api_end = datetime.strptime(bounds['end'], '%Y-%m-%d')
                
                if start_dt < api_start or end_dt > api_end:
                    return False
                    
            return True
            
        except ValueError:
            return False
    
    @abstractmethod
    def discover_coverage(self) -> Dict[str, Any]:
        """
        Discover spatial and temporal coverage for this API.
        Must be implemented by subclasses.
        
        Returns:
            Dictionary with coverage information
        """
        pass
    
    @abstractmethod
    def get_available_datasets(self) -> List[Dict[str, Any]]:
        """
        Get list of available datasets from this API.
        Must be implemented by subclasses.
        
        Returns:
            List of dataset information dictionaries
        """
        pass
    
    @abstractmethod
    def query_data(self, lat: float, lon: float, start_date: str, end_date: str, 
                  parameters: List[str] = None) -> Dict[str, Any]:
        """
        Query data from the API for specific location and time range.
        Must be implemented by subclasses.
        
        Args:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees  
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            parameters: List of parameters to retrieve
            
        Returns:
            Dictionary with query results
        """
        pass
    
    def get_coverage_summary(self) -> Dict[str, Any]:
        """Get summary of API coverage information."""
        return {
            'api_name': self.api_name,
            'base_url': self.base_url,
            'coverage': self.coverage_info,
            'last_updated': self.coverage_info.get('last_updated'),
            'connection_status': self.test_connection()['status']
        }
    
    def close(self):
        """Clean up resources."""
        self.session.close()
        self.logger.info(f"Closed {self.api_name} client")