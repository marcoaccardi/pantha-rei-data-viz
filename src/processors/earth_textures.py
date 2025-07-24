#!/usr/bin/env python3
"""
Earth Texture Processor - Professional NASA Earth texture system.
Downloads and processes real NASA Earth textures for globe visualization.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from PIL import Image

from ..utils.api_client import APIClient
from ..utils.file_ops import FileOperations
from ..utils.validation import TextureValidator
from ..models.texture_specs import ValidationResult
import config

class EarthTextureProcessor:
    """Professional Earth texture processing system."""
    
    def __init__(self):
        """Initialize Earth texture processor."""
        self.api_client = APIClient()
        self.file_ops = FileOperations()
        self.validator = TextureValidator()
        self.specs = config.TEXTURE_SPECS
        
        print("🌍 Earth Texture Processor initialized")
        print("🎯 Sources: NASA Blue Marble + High-resolution Earth imagery")
        print(f"📐 Target resolution: {self.specs['target_width']}x{self.specs['target_height']}")
    
    def download_earth_base_texture(self, resolution: str = "high", output_dir: Optional[Path] = None, force: bool = False) -> Optional[Path]:
        """
        Download high-quality NASA Earth base texture.
        
        Args:
            resolution: Resolution preference ("high", "medium", "low")
            output_dir: Output directory (uses config default if None)
            
        Returns:
            Path to downloaded texture or None if failed
        """
        if output_dir is None:
            output_dir = config.PATHS['earth_textures_dir']
        
        self.file_ops.ensure_directory(output_dir)
        
        # Try sources in order of preference (all equirectangular)
        sources_to_try = [
            ('world_topo_bathy', 'nasa_world_topo_bathy.jpg'),
            ('natural_earth_1', 'natural_earth_equirectangular.jpg'),
            ('usgs_earth', 'usgs_earth_equirectangular.jpg')
        ]
        
        for source_key, filename in sources_to_try:
            output_path = output_dir / filename
            
            # Check if file already exists and is valid (unless force=True)
            if output_path.exists() and not force:
                validation = self.validator.validate_texture(str(output_path))
                if validation.suitable_for_globe:
                    file_size = output_path.stat().st_size
                    print(f"✅ Earth texture already exists: {filename} ({file_size/1024/1024:.1f}MB)")
                    print("🚀 Skipping download (use --force to re-download)")
                    return output_path
                else:
                    print(f"⚠️ Existing texture invalid, re-downloading: {filename}")
            
            # Try to download from this source
            try:
                print(f"🌍 Downloading Earth texture from {source_key}...")
                
                if self.api_client.download_earth_texture(source_key, output_dir):
                    # Rename to expected filename
                    downloaded_path = output_dir / f"{source_key}_earth_texture.jpg"
                    if downloaded_path.exists():
                        self.file_ops.move_file_safe(downloaded_path, output_path)
                    
                    # Validate download
                    validation = self._validate_earth_texture(output_path)
                    if validation.suitable_for_globe:
                        print(f"✅ Downloaded: {filename}")
                        return output_path
                    else:
                        print(f"❌ Downloaded texture invalid: {filename}")
                        self.file_ops.delete_file_safe(output_path)
                        continue
                        
            except Exception as e:
                print(f"❌ Failed to download from {source_key}: {e}")
                if output_path.exists():
                    self.file_ops.delete_file_safe(output_path)
                continue
        
        # If all sources failed, create fallback
        print("❌ All Earth texture sources failed")
        return self._create_fallback_earth_texture(output_dir)
    
    def _validate_earth_texture(self, texture_path: Path) -> ValidationResult:
        """Validate Earth texture meets requirements."""
        validation = self.validator.validate_texture(str(texture_path))
        
        # Additional Earth-specific validation
        if validation.file_exists:
            try:
                with Image.open(texture_path) as img:
                    width, height = img.size
                    aspect_ratio = width / height
                    
                    print(f"📐 Dimensions: {width}x{height}")
                    print(f"📊 Aspect ratio: {aspect_ratio:.3f}")
                    
                    if abs(aspect_ratio - 2.0) > 0.1:
                        validation.add_warning(f"Aspect ratio {aspect_ratio:.3f} is not ideal for globe")
                    
            except Exception as e:
                validation.add_error(f"Failed to analyze texture: {e}")
        
        return validation
    
    def _create_fallback_earth_texture(self, output_dir: Path) -> Optional[Path]:
        """Create fallback Earth texture using cartopy."""
        try:
            print("🔄 Creating fallback Earth texture with accurate geography...")
            
            import matplotlib.pyplot as plt
            import cartopy.crs as ccrs
            import cartopy.feature as cfeature
            
            # Create figure with exact 2:1 aspect ratio
            fig = plt.figure(figsize=(24, 12), dpi=300)
            ax = plt.axes(projection=ccrs.PlateCarree())
            
            # Set global extent
            ax.set_global()
            ax.set_extent([-180, 180, -90, 90], ccrs.PlateCarree())
            
            # Remove all decorations
            ax.axis('off')
            plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
            
            # Add high-quality geographic features
            ax.add_feature(cfeature.OCEAN, color='#4682B4', alpha=1.0)
            ax.add_feature(cfeature.LAND, color='#8FBC8F', alpha=1.0)
            ax.add_feature(cfeature.COASTLINE, color='#696969', linewidth=0.5)
            ax.add_feature(cfeature.BORDERS, color='#A0A0A0', linewidth=0.3)
            ax.add_feature(cfeature.LAKES, color='#87CEEB', alpha=1.0)
            
            # Save fallback texture
            output_path = output_dir / 'fallback_earth_texture.png'
            plt.savefig(
                output_path,
                format='png',
                dpi=300,
                bbox_inches='tight',
                pad_inches=0,
                facecolor='none',
                edgecolor='none'
            )
            plt.close()
            
            # Validate result
            validation = self.validator.validate_texture(str(output_path))
            if validation.suitable_for_globe:
                print(f"✅ Fallback Earth texture created: {output_path.name}")
                return output_path
            else:
                print(f"❌ Fallback texture creation failed validation")
                return None
            
        except Exception as e:
            print(f"❌ Fallback texture creation failed: {e}")
            return None
    
    def process_multiple_sources(self, sources: List[str], output_dir: Optional[Path] = None) -> Dict[str, Optional[Path]]:
        """
        Process multiple Earth texture sources.
        
        Args:
            sources: List of source names to process
            output_dir: Output directory
            
        Returns:
            Dictionary mapping source names to output paths
        """
        if output_dir is None:
            output_dir = config.PATHS['earth_textures_dir']
        
        results = {}
        
        for source in sources:
            print(f"\n🌍 Processing source: {source}")
            try:
                downloaded_path = self.api_client.download_earth_texture(source, output_dir)
                if downloaded_path:
                    validation = self.validator.validate_texture(str(downloaded_path))
                    if validation.suitable_for_globe:
                        results[source] = downloaded_path
                        print(f"✅ {source}: Ready for globe")
                    else:
                        results[source] = None
                        print(f"❌ {source}: Validation failed")
                else:
                    results[source] = None
                    print(f"❌ {source}: Download failed")
                    
            except Exception as e:
                print(f"❌ {source}: Processing error - {e}")
                results[source] = None
        
        return results
    
    def get_best_texture(self, output_dir: Optional[Path] = None) -> Optional[Path]:
        """
        Get the best available Earth texture.
        
        Args:
            output_dir: Directory to check for textures
            
        Returns:
            Path to best texture or None if none found
        """
        if output_dir is None:
            output_dir = config.PATHS['earth_textures_dir']
        
        # Find all texture files
        texture_files = self.file_ops.find_files(output_dir, "*.{jpg,jpeg,png}")
        
        if not texture_files:
            return None
        
        best_texture = None
        best_score = 0
        
        for texture_file in texture_files:
            validation = self.validator.validate_texture(str(texture_file))
            
            # Calculate quality score
            score = 0
            
            if validation.suitable_for_globe:
                score += 100
            
            if validation.dimensions:
                width, height = validation.dimensions
                # Prefer higher resolution
                score += (width * height) / 1000000  # Megapixels
            
            # Prefer smaller file sizes (more efficient)
            if validation.file_size_mb > 0:
                score += max(0, 10 - validation.file_size_mb)
            
            # Prefer PNG for quality
            if validation.format == 'PNG':
                score += 5
            
            if score > best_score:
                best_score = score
                best_texture = texture_file
        
        return best_texture
    
    def cleanup_old_textures(self, output_dir: Optional[Path] = None, keep_best: int = 2) -> int:
        """
        Clean up old or low-quality textures.
        
        Args:
            output_dir: Directory to clean
            keep_best: Number of best textures to keep
            
        Returns:
            Number of files cleaned up
        """
        if output_dir is None:
            output_dir = config.PATHS['earth_textures_dir']
        
        texture_files = self.file_ops.find_files(output_dir, "*.{jpg,jpeg,png}")
        
        if len(texture_files) <= keep_best:
            return 0
        
        # Score all textures
        scored_textures = []
        for texture_file in texture_files:
            validation = self.validator.validate_texture(str(texture_file))
            score = 0
            
            if validation.suitable_for_globe:
                score += 100
            if validation.dimensions:
                width, height = validation.dimensions
                score += (width * height) / 1000000
            
            scored_textures.append((score, texture_file))
        
        # Sort by score (highest first)
        scored_textures.sort(reverse=True)
        
        # Remove low-scoring textures
        cleaned_count = 0
        for score, texture_file in scored_textures[keep_best:]:
            if self.file_ops.delete_file_safe(texture_file):
                cleaned_count += 1
                print(f"🗑️ Removed low-quality texture: {texture_file.name}")
        
        return cleaned_count
    
    def close(self):
        """Clean up resources."""
        self.api_client.close()