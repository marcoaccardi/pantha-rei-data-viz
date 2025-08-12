#!/usr/bin/env python3
"""
High-quality SST texture downloader using PacIOOS ERDDAP transparentPng service.
Downloads professional-grade 5km resolution SST textures directly from ERDDAP,
matching the quality of the Corals project implementation.
"""

import requests
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional, Union
import tempfile
import shutil
from PIL import Image

class SSTERDDAPTextureDownloader:
    """Downloads high-quality SST textures from PacIOOS ERDDAP transparentPng service."""
    
    def __init__(self, output_base_path: Optional[Path] = None):
        """
        Initialize ERDDAP SST texture downloader.
        
        Args:
            output_base_path: Base path for texture output (defaults to frontend/public/textures)
        """
        self.logger = logging.getLogger(__name__)
        
        if output_base_path is None:
            # Output to ocean-data textures directory for proper organization
            self.output_base_path = Path("../ocean-data/textures/sst")
        else:
            self.output_base_path = Path(output_base_path)
            
        self.output_base_path.mkdir(parents=True, exist_ok=True)
        
        # ERDDAP service configuration (verified from Corals project)
        self.base_url = "https://pae-paha.pacioos.hawaii.edu/erddap/griddap/dhw_5km.transparentPng"
        self.dataset_name = "dhw_5km"
        self.variable_name = "CRW_SST"
        
        # Coverage: Global ocean with 5km resolution
        self.spatial_coverage = {
            'lat_min': -89.975,
            'lat_max': 89.975,
            'lon_min': -179.975,
            'lon_max': 179.975
        }
        
        # Temporal coverage (from Corals project)
        self.temporal_coverage = {
            'start': date(2003, 1, 1),
            'end': date.today() - timedelta(days=1)  # Yesterday (allow for processing delay)
        }
        
        # Request session for connection reuse
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Ocean-Climate-Research/1.0 (panta-rhei-data-map) SST-Texture-Downloader'
        })
        
        self.logger.info(f"Initialized ERDDAP SST texture downloader")
        self.logger.info(f"Output directory: {self.output_base_path}")
        self.logger.info(f"Coverage: {self.temporal_coverage['start']} to {self.temporal_coverage['end']}")
        
    def _generate_erddap_url(self, target_date: date) -> str:
        """
        Generate ERDDAP transparentPng URL for given date.
        Uses the exact same URL pattern as the Corals project.
        
        Args:
            target_date: Date to download texture for
            
        Returns:
            Complete ERDDAP URL
        """
        # Format date as ISO string with noon UTC time
        date_str = target_date.strftime("%Y-%m-%dT12:00:00Z")
        
        # Construct URL using verified Corals pattern
        url = (
            f"{self.base_url}?"
            f"{self.variable_name}%5B({date_str})%5D"
            f"%5B({self.spatial_coverage['lat_max']}):({self.spatial_coverage['lat_min']})%5D"
            f"%5B({self.spatial_coverage['lon_min']}):({self.spatial_coverage['lon_max']})%5D"
            f"&.draw=surface"
            f"&.vars=longitude%7Clatitude%7C{self.variable_name}"
            f"&.colorBar=%7C%7C%7C%7C%7C"
            f"&.bgColor=0xffccccff"
        )
        
        return url
        
    def _generate_filename(self, target_date: date) -> str:
        """Generate standardized filename for SST texture."""
        return f"SST_{target_date.strftime('%Y%m%d')}.png"
        
    def _validate_texture_image(self, image_path: Path) -> bool:
        """
        Validate downloaded texture image.
        
        Args:
            image_path: Path to downloaded image
            
        Returns:
            True if image is valid
        """
        try:
            with Image.open(image_path) as img:
                # Check image properties
                width, height = img.size
                
                # ERDDAP transparentPng should produce reasonably sized images
                if width < 50 or height < 50:
                    self.logger.error(f"Image too small: {width}x{height}")
                    return False
                    
                if width > 10000 or height > 10000:
                    self.logger.warning(f"Image very large: {width}x{height}")
                    
                # Check that image has RGBA channels (transparentPng)
                if img.mode not in ['RGBA', 'RGB', 'P']:
                    self.logger.warning(f"Unexpected image mode: {img.mode}")
                    
                self.logger.info(f"Valid texture image: {width}x{height}, mode: {img.mode}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error validating image {image_path}: {e}")
            return False
            
    def download_texture_for_date(self, target_date: date) -> bool:
        """
        Download high-quality SST texture for specific date.
        
        Args:
            target_date: Date to download texture for
            
        Returns:
            True if successful
        """
        # Check date range
        if target_date < self.temporal_coverage['start'] or target_date > self.temporal_coverage['end']:
            self.logger.warning(f"Date {target_date} outside available coverage")
            return False
            
        # Generate URL and filename
        url = self._generate_erddap_url(target_date)
        filename = self._generate_filename(target_date)
        
        # Create year subdirectory
        year_dir = self.output_base_path / str(target_date.year)
        year_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = year_dir / filename
        
        # Skip if file already exists and is valid
        if output_path.exists() and self._validate_texture_image(output_path):
            file_size_mb = output_path.stat().st_size / (1024 * 1024)
            self.logger.info(f"Texture already exists: {output_path} ({file_size_mb:.1f} MB)")
            return True
            
        try:
            self.logger.info(f"Downloading SST texture for {target_date}")
            self.logger.info(f"URL: {url}")
            
            # Download with streaming
            response = self.session.get(url, stream=True, timeout=300)  # 5 minute timeout
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '')
            if 'image' not in content_type:
                self.logger.error(f"Unexpected content type: {content_type}")
                return False
                
            # Save to temporary file first
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
                temp_path = Path(temp_file.name)
                
                # Download in chunks
                total_size = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        temp_file.write(chunk)
                        total_size += len(chunk)
                        
            # Validate downloaded image
            if not self._validate_texture_image(temp_path):
                self.logger.error(f"Downloaded texture failed validation")
                temp_path.unlink()
                return False
                
            # Move to final location
            shutil.move(str(temp_path), str(output_path))
            
            file_size_mb = total_size / (1024 * 1024)
            self.logger.info(f"Successfully downloaded: {output_path} ({file_size_mb:.1f} MB)")
            
            return True
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error downloading texture for {target_date}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error downloading texture for {target_date}: {e}")
            return False
            
    def download_date_range(self, start_date: date, end_date: date) -> dict:
        """
        Download SST textures for a date range.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            Dictionary with download results
        """
        results = {
            'total_requested': 0,
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        current_date = start_date
        while current_date <= end_date:
            results['total_requested'] += 1
            
            try:
                success = self.download_texture_for_date(current_date)
                if success:
                    results['successful'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append(f"Failed to download texture for {current_date}")
                    
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"Error processing {current_date}: {e}")
                
            # Move to next day
            current_date += timedelta(days=1)
            
        self.logger.info(
            f"Download batch complete: {results['successful']} successful, "
            f"{results['failed']} failed out of {results['total_requested']} requested"
        )
        
        return results
        
    def download_recent_textures(self, days: int = 30) -> dict:
        """
        Download textures for recent dates.
        
        Args:
            days: Number of recent days to download
            
        Returns:
            Download results dictionary
        """
        end_date = self.temporal_coverage['end']
        start_date = end_date - timedelta(days=days-1)
        
        self.logger.info(f"Downloading recent {days} days of SST textures: {start_date} to {end_date}")
        
        return self.download_date_range(start_date, end_date)
        
    def get_available_textures(self) -> dict:
        """
        Get information about available downloaded textures.
        
        Returns:
            Dictionary with texture availability info
        """
        texture_files = list(self.output_base_path.rglob("SST_*.png"))
        
        if not texture_files:
            return {
                'total_files': 0,
                'date_range': None,
                'years_available': [],
                'total_size_mb': 0
            }
            
        # Extract dates from filenames
        dates = []
        total_size = 0
        
        for file_path in texture_files:
            try:
                # Extract date from filename: SST_YYYYMMDD.png
                date_str = file_path.stem.split('_')[1]
                file_date = datetime.strptime(date_str, '%Y%m%d').date()
                dates.append(file_date)
                total_size += file_path.stat().st_size
            except (ValueError, IndexError):
                continue
                
        if not dates:
            return {
                'total_files': len(texture_files),
                'date_range': None,
                'years_available': [],
                'total_size_mb': 0
            }
            
        dates.sort()
        years_available = sorted(list(set(d.year for d in dates)))
        
        return {
            'total_files': len(dates),
            'date_range': {
                'start': dates[0].strftime('%Y-%m-%d'),
                'end': dates[-1].strftime('%Y-%m-%d')
            },
            'years_available': years_available,
            'total_size_mb': round(total_size / (1024 * 1024), 1)
        }
        
    def cleanup_old_textures(self, keep_days: int = 365) -> dict:
        """
        Remove old texture files to save space.
        
        Args:
            keep_days: Number of recent days to keep
            
        Returns:
            Cleanup results
        """
        cutoff_date = date.today() - timedelta(days=keep_days)
        
        texture_files = list(self.output_base_path.rglob("SST_*.png"))
        
        results = {
            'files_checked': len(texture_files),
            'files_removed': 0,
            'space_freed_mb': 0,
            'errors': []
        }
        
        for file_path in texture_files:
            try:
                # Extract date from filename
                date_str = file_path.stem.split('_')[1]
                file_date = datetime.strptime(date_str, '%Y%m%d').date()
                
                if file_date < cutoff_date:
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    
                    results['files_removed'] += 1
                    results['space_freed_mb'] += file_size / (1024 * 1024)
                    
            except Exception as e:
                results['errors'].append(f"Error processing {file_path}: {e}")
                
        results['space_freed_mb'] = round(results['space_freed_mb'], 1)
        
        self.logger.info(
            f"Cleanup complete: removed {results['files_removed']} files, "
            f"freed {results['space_freed_mb']} MB"
        )
        
        return results