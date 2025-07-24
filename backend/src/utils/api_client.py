#!/usr/bin/env python3
"""
API client utilities for NOAA Climate Data System.
"""

import requests
import time
from typing import Optional, Dict, Any, Union
from pathlib import Path
import tempfile

try:
    import requests_cache
    REQUESTS_CACHE_AVAILABLE = True
except ImportError:
    REQUESTS_CACHE_AVAILABLE = False

import config

class APIClient:
    """Handle API requests and data downloads."""
    
    def __init__(self, use_cache: bool = True):
        """
        Initialize API client.
        
        Args:
            use_cache: Whether to use request caching
        """
        self.config = config.API_CONFIG
        
        # Setup session with caching if available
        if use_cache and REQUESTS_CACHE_AVAILABLE:
            self.session = requests_cache.CachedSession(
                cache_name='noaa_api_cache',
                expire_after=self.config['cache_expire_hours'] * 3600
            )
        else:
            self.session = requests.Session()
        
        # Set headers
        self.session.headers.update({
            'User-Agent': self.config['user_agent'],
            'Accept': 'application/json, application/netcdf, application/octet-stream, image/jpeg, image/png'
        })
    
    def get_with_retry(self, url: str, **kwargs) -> Optional[requests.Response]:
        """
        GET request with retry logic.
        
        Args:
            url: URL to request
            **kwargs: Additional request parameters
            
        Returns:
            Response object or None if failed
        """
        max_retries = kwargs.pop('max_retries', self.config['max_retries'])
        timeout = kwargs.pop('timeout', self.config['timeout'])
        
        for attempt in range(max_retries + 1):
            try:
                response = self.session.get(url, timeout=timeout, **kwargs)
                response.raise_for_status()
                return response
                
            except requests.exceptions.RequestException as e:
                if attempt == max_retries:
                    print(f"❌ Failed to fetch {url} after {max_retries + 1} attempts: {e}")
                    return None
                else:
                    wait_time = 2 ** attempt  # Exponential backoff
                    print(f"⚠️ Attempt {attempt + 1} failed, retrying in {wait_time}s...")
                    time.sleep(wait_time)
        
        return None
    
    def download_file(self, url: str, output_path: Path, **kwargs) -> bool:
        """
        Download file from URL.
        
        Args:
            url: URL to download from
            output_path: Where to save the file
            **kwargs: Additional request parameters
            
        Returns:
            True if download successful
        """
        try:
            print(f"📥 Downloading from: {url}")
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download with streaming
            response = self.get_with_retry(url, stream=True, **kwargs)
            if not response:
                return False
            
            # Get file size for progress tracking
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Progress indicator for large files
                        if total_size > 0 and downloaded % (1024 * 1024) == 0:
                            progress = (downloaded / total_size) * 100
                            print(f"   📥 Progress: {progress:.1f}% ({downloaded/1024/1024:.1f}MB)")
            
            print(f"✅ Downloaded: {output_path.name} ({downloaded/1024/1024:.1f}MB)")
            return True
            
        except Exception as e:
            print(f"❌ Download failed: {e}")
            # Clean up partial file
            if output_path.exists():
                output_path.unlink()
            return False
    
    def check_url_availability(self, url: str) -> bool:
        """
        Check if URL is accessible.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL is accessible
        """
        try:
            response = self.session.head(url, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def get_json(self, url: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Get JSON data from URL.
        
        Args:
            url: URL to request
            **kwargs: Additional request parameters
            
        Returns:
            JSON data or None if failed
        """
        try:
            response = self.get_with_retry(url, **kwargs)
            if response:
                return response.json()
            return None
        except Exception as e:
            print(f"❌ Failed to get JSON from {url}: {e}")
            return None
    
    def download_oisst_data(self, date_str: str, output_dir: Path) -> Optional[Path]:
        """
        Download OISST NetCDF data for specific date.
        
        Args:
            date_str: Date in YYYYMMDD format
            output_dir: Directory to save data
            
        Returns:
            Path to downloaded file or None if failed
        """
        try:
            # Parse date
            year = date_str[:4]
            month = date_str[4:6]
            
            # Construct OISST URL
            filename = f"oisst-avhrr-v02r01.{date_str}.nc"
            url = f"{config.DATA_SOURCES['oisst_base_url']}/{year}{month}/{filename}"
            
            output_path = output_dir / filename
            
            # Download file
            if self.download_file(url, output_path):
                return output_path
            else:
                return None
                
        except Exception as e:
            print(f"❌ Failed to download OISST data for {date_str}: {e}")
            return None
    
    def find_latest_oisst_date(self, days_back: int = 30) -> Optional[str]:
        """
        Find the latest available OISST date.
        
        Args:
            days_back: How many days back to search
            
        Returns:
            Date string in YYYYMMDD format or None if not found
        """
        from datetime import datetime, timedelta
        
        base_url = config.DATA_SOURCES['oisst_base_url']
        
        for days in range(7, days_back):  # Start from 1 week back
            test_date = datetime.now() - timedelta(days=days)
            date_str = test_date.strftime('%Y%m%d')
            year = test_date.strftime('%Y')
            month = test_date.strftime('%m')
            
            filename = f"oisst-avhrr-v02r01.{date_str}.nc"
            url = f"{base_url}/{year}{month}/{filename}"
            
            if self.check_url_availability(url):
                print(f"✅ Found OISST data for: {date_str}")
                return date_str
        
        print(f"❌ No OISST data found in last {days_back} days")
        return None
    
    def download_earth_texture(self, source_name: str, output_dir: Path) -> Optional[Path]:
        """
        Download Earth texture from configured sources.
        
        Args:
            source_name: Name of source from config
            output_dir: Directory to save texture
            
        Returns:
            Path to downloaded file or None if failed
        """
        nasa_urls = config.DATA_SOURCES['nasa_earth_urls']
        
        if source_name not in nasa_urls:
            print(f"❌ Unknown Earth texture source: {source_name}")
            return None
        
        url = nasa_urls[source_name]
        filename = f"{source_name}_earth_texture.jpg"
        output_path = output_dir / filename
        
        if self.download_file(url, output_path):
            return output_path
        else:
            return None
    
    def get_noaa_station_data(self, station_id: str, date: str, product: str = "water_temperature") -> Optional[Dict[str, Any]]:
        """
        Get NOAA station data from API.
        
        Args:
            station_id: NOAA station ID
            date: Date in YYYY-MM-DD format
            product: Data product to retrieve
            
        Returns:
            Station data or None if failed
        """
        try:
            base_url = config.DATA_SOURCES['noaa_stations_api']
            
            params = {
                'product': product,
                'application': 'NOAA_Climate_System',
                'begin_date': date,
                'end_date': date,
                'station': station_id,
                'time_zone': 'gmt',
                'units': 'metric',
                'format': 'json'
            }
            
            response = self.get_with_retry(base_url, params=params)
            if response:
                return response.json()
            return None
            
        except Exception as e:
            print(f"❌ Failed to get station data for {station_id}: {e}")
            return None
    
    def close(self):
        """Close the session."""
        self.session.close()