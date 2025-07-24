#!/usr/bin/env python3
"""
ERDDAP SST Texture Processor - Direct download of pre-rendered SST textures.
Uses PacIOOS Hawaii ERDDAP server for high-quality SST texture downloads.
"""

import requests
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode, quote

from ..utils.api_client import APIClient
from ..utils.file_ops import FileOperations
from ..utils.validation import TextureValidator
import config

class ERDDAPSSTProcessor:
    """High-quality SST texture processor using ERDDAP pre-rendered images."""
    
    def __init__(self):
        """Initialize ERDDAP SST processor."""
        self.api_client = APIClient()
        self.file_ops = FileOperations()
        self.validator = TextureValidator()
        
        # ERDDAP endpoints - use PacIOOS Hawaii like the original script
        self.erddap_base = "https://pae-paha.pacioos.hawaii.edu/erddap/griddap"
        self.dataset_id = "dhw_5km"  # NOAA Coral Reef Watch SST dataset
        
        # Global coverage parameters with resolution options
        self.resolution_presets = {
            'high': {'stride': 1, 'desc': '7200x3600 (~11MB)', 'size': 'large'},
            'medium': {'stride': 2, 'desc': '3600x1800 (~3MB)', 'size': 'medium'},
            'low': {'stride': 4, 'desc': '1800x900 (~800KB)', 'size': 'small'},
            'preview': {'stride': 8, 'desc': '900x450 (~200KB)', 'size': 'tiny'}
        }
        
        # Default to medium resolution for better balance
        self.default_resolution = 'medium'
        
        self.global_coords = {
            'north': 89.975,
            'south': -89.975,
            'west': -179.975,
            'east': 179.975
        }
        
        print("🌊 ERDDAP SST Processor initialized")
        print("📡 Source: PacIOOS Hawaii ERDDAP (NOAA Coral Reef Watch)")
        print("🌍 Coverage: Global SST textures (pre-rendered)")
        print("📐 Format: PNG with perfect 2:1 aspect ratio for sphere mapping")
    
    def download_sst_texture(self, date: str, output_dir: Optional[Path] = None, force: bool = False, resolution: str = None) -> Optional[Path]:
        """
        Download pre-rendered SST texture for specific date.
        
        Args:
            date: Date string in YYYY-MM-DD format
            output_dir: Output directory for texture
            force: Force re-download even if file exists
            resolution: Resolution preset ('high', 'medium', 'low', 'preview')
            
        Returns:
            Path to downloaded texture or None if failed
        """
        if output_dir is None:
            output_dir = config.PATHS['sst_textures_dir']
        
        self.file_ops.ensure_directory(output_dir)
        
        # Set resolution if not provided
        if resolution is None:
            resolution = self.default_resolution
        
        # Validate resolution
        if resolution not in self.resolution_presets:
            print(f"⚠️ Invalid resolution '{resolution}', using '{self.default_resolution}'")
            resolution = self.default_resolution
        
        resolution_info = self.resolution_presets[resolution]
        
        try:
            # Parse and validate date
            target_date = datetime.strptime(date, '%Y-%m-%d')
            
            # Check if date is within available range (2003-present)
            earliest_date = datetime(2003, 1, 1)
            latest_date = datetime.now() - timedelta(days=7)  # ERDDAP has ~1 week delay
            
            if target_date < earliest_date:
                print(f"⚠️ Date {date} is before dataset start (2003-01-01), using earliest available")
                target_date = earliest_date
            elif target_date > latest_date:
                print(f"⚠️ Date {date} is too recent, using latest available: {latest_date.strftime('%Y-%m-%d')}")
                target_date = latest_date
            
            # Format date for ERDDAP
            iso_datetime = target_date.strftime('%Y-%m-%dT12:00:00Z')
            date_str = target_date.strftime('%Y%m%d')
            
            print(f"📅 Downloading SST texture for: {target_date.strftime('%Y-%m-%d')}")
            print(f"📐 Resolution: {resolution.upper()} ({resolution_info['desc']})")
            
            # Build ERDDAP URL with resolution
            url = self._build_global_erddap_url(iso_datetime, resolution_info['stride'])
            
            # Create filename with resolution suffix
            filename = f"erddap_sst_texture_{date_str}_{resolution}.png"
            output_path = output_dir / filename
            
            # Check if file already exists and is recent enough (unless force=True)
            if output_path.exists() and not force:
                file_size = output_path.stat().st_size
                if file_size > 1000:  # Valid file size
                    print(f"✅ SST texture already exists: {filename} ({file_size/1024/1024:.1f}MB)")
                    print("🚀 Skipping download (use --force to re-download)")
                    return output_path
            
            print(f"🌊 Fetching global SST texture from ERDDAP")
            print(f"📐 Full global coverage: 89.975°N to -89.975°S, -179.975°W to 179.975°E")
            
            # Download with progress
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        if total_size > 0:
                            progress = (downloaded_size / total_size) * 100
                            print(f"\r📥 Progress: {progress:.1f}% ({downloaded_size/1024/1024:.1f}MB)", end='')
            
            print()  # New line after progress
            
            # Validate downloaded texture
            file_size = output_path.stat().st_size
            print(f"✅ Downloaded: {filename} ({file_size/1024/1024:.1f}MB)")
            
            # Check if file is too small (likely an error)
            if file_size < 1000:
                print(f"⚠️ File too small ({file_size}B) - likely no data for this date")
                return None
            
            # Validate texture quality
            validation = self.validator.validate_texture(str(output_path))
            if validation.suitable_for_globe:
                print(f"✅ Texture validation passed - React Three Fiber ready")
                if validation.dimensions:
                    width, height = validation.dimensions
                    print(f"📐 Dimensions: {width}x{height} (aspect ratio: {validation.aspect_ratio:.3f})")
            else:
                print("⚠️ Texture validation warnings:")
                for warning in validation.validation_warnings:
                    print(f"   • {warning}")
            
            return output_path
            
        except requests.exceptions.RequestException as e:
            print(f"❌ ERDDAP download failed: {e}")
            return None
        except Exception as e:
            print(f"❌ SST texture processing failed: {e}")
            return None
    
    def download_latest_sst_texture(self, output_dir: Optional[Path] = None, force: bool = False, resolution: str = None) -> Optional[Path]:
        """Download the latest available SST texture."""
        
        # Try dates from most recent backwards until successful
        for days_back in range(7, 14):  # ERDDAP typically has 1-2 week delay
            try_date = datetime.now() - timedelta(days=days_back)
            date_str = try_date.strftime('%Y-%m-%d')
            
            print(f"🔍 Trying date: {date_str}")
            result = self.download_sst_texture(date_str, output_dir, force, resolution)
            
            if result:
                print(f"✅ Successfully downloaded latest SST texture for {date_str}")
                return result
            else:
                print(f"⚠️ No data available for {date_str}, trying earlier date...")
                time.sleep(1)  # Brief pause between attempts
        
        print(f"❌ Could not find recent SST data - ERDDAP may be unavailable")
        return None
    
    def download_sst_time_series(self, start_date: str, end_date: str, 
                                output_dir: Optional[Path] = None) -> List[Path]:
        """
        Download SST textures for a date range.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            output_dir: Output directory
            
        Returns:
            List of successfully downloaded texture paths
        """
        if output_dir is None:
            output_dir = config.PATHS['sst_textures_dir']
        
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            if start_dt > end_dt:
                raise ValueError("Start date must be before end date")
            
            print(f"📅 Downloading SST time series: {start_date} to {end_date}")
            
            downloaded_files = []
            current_dt = start_dt
            
            while current_dt <= end_dt:
                date_str = current_dt.strftime('%Y-%m-%d')
                
                result = self.download_sst_texture(date_str, output_dir)
                if result:
                    downloaded_files.append(result)
                    print(f"✅ Downloaded {len(downloaded_files)}: {result.name}")
                else:
                    print(f"⚠️ Skipped {date_str} (data not available)")
                
                current_dt += timedelta(days=1)
                time.sleep(0.5)  # Be respectful to ERDDAP server
            
            print(f"📊 Time series complete: {len(downloaded_files)} textures downloaded")
            return downloaded_files
            
        except Exception as e:
            print(f"❌ Time series download failed: {e}")
            return []
    
    def _build_erddap_url(self, iso_datetime: str, region: Optional[Dict] = None) -> str:
        """Build ERDDAP URL for SST texture download."""
        
        # Use regional coordinates if provided, otherwise fall back to smaller global region
        if region:
            coords = region
        else:
            # Use a smaller test region that we know works well
            coords = {
                'north': 60.0,
                'south': 20.0, 
                'west': -100.0,
                'east': -50.0,
                'stride': 1
            }
        
        # ERDDAP query parameters (variable name depends on dataset)
        stride = coords.get('stride', 1)
        if 'jplMURSST' in self.dataset_id:
            sst_var = 'analysed_sst'  # JPL MUR SST variable name
        else:
            sst_var = 'CRW_SST'  # Coral Reef Watch variable name
            
        params = {
            sst_var: f'[({iso_datetime})][({coords["north"]}):{stride}:({coords["south"]})][({coords["west"]}):{stride}:({coords["east"]})]',
            '.draw': 'surface',
            '.vars': f'longitude|latitude|{sst_var}',
            '.colorBar': '||||', # Use default colorbar
            '.bgColor': '0xffccccff'  # Transparent background
        }
        
        # Build URL
        base_url = f"{self.erddap_base}/{self.dataset_id}.transparentPng"
        query_string = urlencode(params, quote_via=quote)
        
        return f"{base_url}?{query_string}"
    
    def _build_global_erddap_url(self, iso_datetime: str, stride: int = 2) -> str:
        """Build ERDDAP URL for global SST texture with resolution control."""
        
        base_url = f"{self.erddap_base}/{self.dataset_id}.transparentPng"
        
        # Build query string with stride parameter for resolution control
        # Format: CRW_SST[(time)][(north):(stride):(south)][(west):(stride):(east)]
        query_params = [
            f"CRW_SST%5B({iso_datetime})%5D%5B(89.975):{stride}:(-89.975)%5D%5B(-179.975):{stride}:(179.975)%5D",
            ".draw=surface",
            ".vars=longitude%7Clatitude%7CCRW_SST",
            ".colorBar=%7C%7C%7C%7C%7C",
            ".bgColor=0xffccccff"
        ]
        
        query_string = "&".join(query_params)
        
        return f"{base_url}?{query_string}"
    
    
    def get_available_date_range(self) -> Dict[str, str]:
        """Get the available date range for the dataset."""
        
        try:
            # Query ERDDAP metadata to get actual date range
            info_url = f"{self.erddap_base}/{self.dataset_id}.info"
            
            response = requests.get(info_url, timeout=10)
            response.raise_for_status()
            
            # Parse response to extract date range (simplified)
            # In production, would parse the CSV response properly
            
            return {
                'start_date': '2003-01-01',
                'end_date': (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
                'note': 'Approximate range - ERDDAP has ~1 week processing delay'
            }
            
        except Exception as e:
            print(f"⚠️ Could not query date range: {e}")
            return {
                'start_date': '2003-01-01',
                'end_date': (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
                'note': 'Default range - could not query ERDDAP metadata'
            }
    
    def generate_sst_report(self, texture_files: List[Path]) -> str:
        """Generate report for downloaded SST textures."""
        
        report = []
        report.append("🌊 ERDDAP SST TEXTURE DOWNLOAD REPORT")
        report.append("=" * 50)
        
        if not texture_files:
            report.append("❌ No SST textures found")
            return "\n".join(report)
        
        # Analyze downloaded textures
        total_size = sum(f.stat().st_size for f in texture_files if f.exists())
        valid_textures = 0
        
        report.append(f"📁 Downloaded Files: {len(texture_files)}")
        report.append(f"💾 Total Size: {total_size/1024/1024:.1f}MB")
        
        # Sample validation
        for i, texture_file in enumerate(texture_files[:3]):  # Validate first 3
            if texture_file.exists():
                validation = self.validator.validate_texture(str(texture_file))
                if validation.suitable_for_globe:
                    valid_textures += 1
                
                if validation.dimensions:
                    width, height = validation.dimensions
                    report.append(f"📐 {texture_file.name}: {width}x{height} ({'✅' if validation.suitable_for_globe else '⚠️'})")
        
        report.append(f"\n✅ React Three Fiber Ready: {valid_textures}/{min(len(texture_files), 3)} validated")
        
        # Data source info
        report.append(f"\n📡 Data Source: NOAA Coral Reef Watch via PacIOOS ERDDAP")
        report.append(f"🌍 Coverage: Global (89.975°N to 89.975°S)")
        report.append(f"📊 Resolution: ~5km (0.05°)")
        report.append(f"🎨 Format: PNG with transparent background")
        report.append(f"🌐 Projection: Equirectangular (perfect for sphere mapping)")
        
        # Usage notes
        report.append(f"\n💡 Usage Notes:")
        report.append(f"   • Load with THREE.TextureLoader() in React Three Fiber")
        report.append(f"   • Apply as texture to sphere geometry")
        report.append(f"   • Transparent background allows layering")
        report.append(f"   • Scientific-grade SST data from NOAA")
        
        return "\n".join(report)
    
    def get_processor_data(self, lat: float, lon: float, date: str) -> Dict[str, Any]:
        """
        Standard interface method for dynamic coordinate system compatibility.
        For SST processor, this returns texture download status and metadata.
        """
        try:
            # Attempt to download SST texture for the given date
            texture_paths = self.download_sst_texture(date, resolution='medium')
            
            if texture_paths:
                return {
                    'data': {
                        'texture_paths': texture_paths,
                        'sst_available': True,
                        'texture_date': date
                    },
                    'metadata': {
                        'source': 'NOAA Coral Reef Watch (PacIOOS ERDDAP)',
                        'data_type': 'sst_texture',
                        'coordinates': {'lat': lat, 'lon': lon},
                        'date': date,
                        'confidence': 0.95,
                        'note': f'SST texture downloaded for {date}'
                    }
                }
            else:
                return {
                    'data': {
                        'texture_paths': [],
                        'sst_available': False,
                        'texture_date': date
                    },
                    'metadata': {
                        'source': 'NOAA Coral Reef Watch (PacIOOS ERDDAP)',
                        'data_type': 'sst_texture',
                        'coordinates': {'lat': lat, 'lon': lon},
                        'date': date,
                        'confidence': 0.0,
                        'note': f'SST texture unavailable for {date}'
                    }
                }
        except Exception as e:
            return {
                'data': {
                    'texture_paths': [],
                    'sst_available': False,
                    'error': str(e)
                },
                'metadata': {
                    'source': 'NOAA Coral Reef Watch (PacIOOS ERDDAP)',
                    'data_type': 'sst_texture',
                    'coordinates': {'lat': lat, 'lon': lon},
                    'date': date,
                    'confidence': 0.0,
                    'note': f'SST texture processing failed: {e}'
                }
            }
    
    def close(self):
        """Clean up resources."""
        self.api_client.close()