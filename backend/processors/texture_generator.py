#!/usr/bin/env python3
"""
Base texture generator for converting ocean data to PNG textures.
Provides common functionality for all dataset-specific texture generators.
"""

import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from PIL import Image
import cmocean
from pathlib import Path
from typing import Union, Dict, Any, Optional, Tuple
import logging
from datetime import datetime
import json

class TextureGenerator:
    """Base class for generating PNG textures from ocean data."""
    
    def __init__(self, output_base_path: Union[str, Path] = None):
        """
        Initialize texture generator.
        
        Args:
            output_base_path: Base path for texture output (defaults to ocean-data/textures)
        """
        self.logger = logging.getLogger(__name__)
        
        if output_base_path is None:
            self.output_base_path = Path("/Volumes/Backup/panta-rhei-data-map/ocean-data/textures")
        else:
            self.output_base_path = Path(output_base_path)
            
        # Standard resolution for medium textures (equirectangular projection)
        self.target_resolution = (360, 180)  # width x height
        
        # Disable matplotlib GUI backend for server environments
        plt.ioff()
        
    def get_scientific_colormap(self, data_type: str) -> str:
        """
        Get appropriate scientific colormap for data type.
        
        Args:
            data_type: Type of data ('temperature', 'velocity', 'ph', 'height', etc.)
            
        Returns:
            Colormap name
        """
        colormap_mapping = {
            'temperature': 'cmocean.thermal',  # Blue to red for temperature
            'sst': 'cmocean.thermal',
            'velocity': 'cmocean.balance',     # Diverging for currents
            'speed': 'cmocean.speed',          # Sequential for speed magnitude
            'ph': 'cmocean.matter',            # Sequential for pH/chemistry
            'acidity': 'cmocean.matter',
            'height': 'cmocean.amp',           # Sequential for wave height
            'waves': 'cmocean.amp',
            'concentration': 'cmocean.dense',   # Sequential for concentrations
            'microplastics': 'cmocean.dense',
            'default': 'viridis'
        }
        
        return colormap_mapping.get(data_type, colormap_mapping['default'])
        
    def normalize_data(self, data: np.ndarray, method: str = 'percentile', 
                      vmin: Optional[float] = None, vmax: Optional[float] = None) -> Tuple[np.ndarray, Dict[str, float]]:
        """
        Normalize data for color mapping.
        
        Args:
            data: Input data array
            method: Normalization method ('percentile', 'minmax', 'custom')
            vmin: Custom minimum value
            vmax: Custom maximum value
            
        Returns:
            Normalized data and normalization parameters
        """
        # Remove NaN values for statistics
        valid_data = data[~np.isnan(data)]
        
        if len(valid_data) == 0:
            self.logger.warning("All data is NaN, cannot normalize")
            return data, {'vmin': 0.0, 'vmax': 1.0, 'method': 'failed'}
            
        if method == 'percentile':
            # Use 2nd and 98th percentiles to avoid outliers
            vmin_calc = np.percentile(valid_data, 2)
            vmax_calc = np.percentile(valid_data, 98)
        elif method == 'minmax':
            vmin_calc = np.min(valid_data)
            vmax_calc = np.max(valid_data)
        elif method == 'custom' and vmin is not None and vmax is not None:
            vmin_calc = vmin
            vmax_calc = vmax
        else:
            # Fallback to percentile
            vmin_calc = np.percentile(valid_data, 2)
            vmax_calc = np.percentile(valid_data, 98)
            
        # Avoid division by zero
        if vmax_calc == vmin_calc:
            vmax_calc = vmin_calc + 1.0
            
        # Normalize to 0-1 range
        normalized = (data - vmin_calc) / (vmax_calc - vmin_calc)
        normalized = np.clip(normalized, 0, 1)
        
        norm_params = {
            'vmin': float(vmin_calc),
            'vmax': float(vmax_calc),
            'method': method
        }
        
        return normalized, norm_params
        
    def create_land_mask(self, lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
        """
        Create a simple land mask for continental boundaries.
        This is a placeholder - in production you'd use actual coastline data.
        
        Args:
            lon: Longitude array
            lat: Latitude array
            
        Returns:
            Boolean mask (True for ocean, False for land)
        """
        # Simple land mask based on major continental boundaries
        # This is very basic - production would use real coastline data
        lon_grid, lat_grid = np.meshgrid(lon, lat)
        
        # Start with all ocean
        ocean_mask = np.ones_like(lon_grid, dtype=bool)
        
        # Very basic continental masking (placeholder)
        # Major landmasses approximate boundaries
        land_regions = [
            # North America (very rough)
            (-170, -50, 15, 75),   # (lon_min, lon_max, lat_min, lat_max)
            # Europe
            (-10, 40, 35, 75),
            # Asia
            (25, 180, 10, 75),
            # Africa
            (-20, 55, -35, 40),
            # South America
            (-85, -30, -60, 15),
            # Australia
            (110, 155, -45, -10),
        ]
        
        for lon_min, lon_max, lat_min, lat_max in land_regions:
            mask = ((lon_grid >= lon_min) & (lon_grid <= lon_max) & 
                   (lat_grid >= lat_min) & (lat_grid <= lat_max))
            ocean_mask[mask] = False
            
        return ocean_mask
        
    def data_to_texture(self, data: np.ndarray, lon: np.ndarray, lat: np.ndarray,
                       colormap: str, normalize_method: str = 'percentile',
                       use_natural_land_mask: bool = True) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Convert data array to texture with color mapping using natural NaN patterns for land.
        
        Args:
            data: 2D data array (lat, lon)
            lon: Longitude coordinates
            lat: Latitude coordinates  
            colormap: Colormap name
            normalize_method: Data normalization method
            use_natural_land_mask: Whether to use natural NaN patterns for land transparency
            
        Returns:
            RGBA texture array and metadata
        """
        # Ensure data is 2D
        if data.ndim > 2:
            data = np.squeeze(data)
            
        # Normalize data (only valid ocean data, preserve NaN for land)
        norm_data, norm_params = self.normalize_data(data, method=normalize_method)
        
        # Get colormap
        try:
            if colormap.startswith('cmocean.'):
                cmap_name = colormap.split('.')[1]
                cmap = getattr(cmocean.cm, cmap_name)
            else:
                cmap = plt.get_cmap(colormap)
        except (AttributeError, ValueError):
            self.logger.warning(f"Colormap {colormap} not found, using viridis")
            cmap = plt.get_cmap('viridis')
            
        # Set NaN values (land areas) to be transparent
        if use_natural_land_mask:
            cmap = cmap.copy()  # Create a copy to avoid modifying the original
            cmap.set_bad(alpha=0.0)  # Make NaN values transparent
            
        # Apply colormap to normalized data (NaN values will be transparent)
        rgba_data = cmap(norm_data)
        
        # Convert to uint8
        texture = (rgba_data * 255).astype(np.uint8)
        
        # Flip texture vertically to correct orientation for globe mapping
        # (matplotlib origin is bottom-left, but texture mapping expects top-left)
        texture = np.flipud(texture)
        
        # Count valid ocean pixels (non-NaN)
        valid_pixels = int(np.sum(~np.isnan(data)))
        total_pixels = data.size
        ocean_coverage = (valid_pixels / total_pixels) * 100
        
        metadata = {
            'normalization': norm_params,
            'colormap': colormap,
            'shape': texture.shape,
            'data_range': {
                'original_min': float(np.nanmin(data)),
                'original_max': float(np.nanmax(data)),
                'valid_pixels': valid_pixels,
                'total_pixels': total_pixels,
                'ocean_coverage_percent': round(ocean_coverage, 1)
            },
            'natural_land_mask': use_natural_land_mask,
            'land_mask_method': 'natural_nan_transparency' if use_natural_land_mask else 'none'
        }
        
        return texture, metadata
        
    def save_texture(self, texture: np.ndarray, output_path: Union[str, Path],
                    metadata: Dict[str, Any]) -> bool:
        """
        Save texture as PNG file.
        
        Args:
            texture: RGBA texture array
            output_path: Output file path
            metadata: Texture metadata (for logging only)
            
        Returns:
            True if successful
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save PNG only
            img = Image.fromarray(texture, mode='RGBA')
            img.save(output_path, 'PNG')
                
            self.logger.info(f"Saved texture: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save texture {output_path}: {e}")
            return False
            
    def generate_filename(self, dataset: str, date_str: str, resolution: str = 'medium') -> str:
        """
        Generate standardized filename for texture.
        
        Args:
            dataset: Dataset name (sst, acidity, etc.)
            date_str: Date string in YYYYMMDD format
            resolution: Resolution identifier
            
        Returns:
            Filename string
        """
        return f"{dataset}_texture_{date_str}_{resolution}.png"
        
    def process_netcdf_to_texture(self, input_path: Union[str, Path], 
                                 variable_name: str, dataset_type: str,
                                 output_directory: Union[str, Path] = None) -> bool:
        """
        Process NetCDF file to texture (to be overridden by subclasses).
        
        Args:
            input_path: Path to input NetCDF file
            variable_name: Name of variable to visualize
            dataset_type: Type of dataset for colormap selection
            output_directory: Output directory (optional)
            
        Returns:
            True if successful
        """
        raise NotImplementedError("Subclasses must implement process_netcdf_to_texture")