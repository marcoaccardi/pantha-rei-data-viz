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
            'height': 'cmocean.amp',           # Sequential for height data
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
        Handles different coordinate ranges (e.g., limited coverage -80°/80° vs SST -90°/90°).
        
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
            
        # Check coordinate ranges
        lat_min, lat_max = float(lat.min()), float(lat.max())
        lon_min, lon_max = float(lon.min()), float(lon.max())
        
        # Determine if we need to expand to full global coverage
        is_limited_coverage = lat_min > -85 or lat_max < 85
        
        if is_limited_coverage:
            # For limited coverage data (like -80°/80° range), expand to global texture
            texture, metadata = self._create_expanded_global_texture(
                data, lon, lat, colormap, normalize_method, use_natural_land_mask
            )
        else:
            # Standard processing for full global coverage
            texture, metadata = self._create_standard_texture(
                data, lon, lat, colormap, normalize_method, use_natural_land_mask
            )
        
        return texture, metadata
    
    def _create_standard_texture(self, data: np.ndarray, lon: np.ndarray, lat: np.ndarray,
                                colormap: str, normalize_method: str, use_natural_land_mask: bool) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Create texture for full global coverage data (like SST)."""
        # Normalize data (only valid ocean data, preserve NaN for land)
        norm_data, norm_params = self.normalize_data(data, method=normalize_method)
        
        # Get colormap
        cmap = self._get_colormap(colormap)
            
        # Set NaN values (land areas) to be transparent white
        if use_natural_land_mask:
            cmap = cmap.copy()
            cmap.set_bad(color='white', alpha=0.0)
            
        # Apply colormap to normalized data
        rgba_data = cmap(norm_data)
        
        # Convert to uint8
        texture = (rgba_data * 255).astype(np.uint8)
        
        # Flip texture vertically to correct orientation for globe mapping
        texture = np.flipud(texture)
        
        # VALIDATE TEXTURE COORDINATE ALIGNMENT for debugging
        self._validate_texture_alignment(data, lon, lat, texture)
        
        # Create metadata
        valid_pixels = int(np.sum(~np.isnan(data)))
        total_pixels = data.size
        ocean_coverage = (valid_pixels / total_pixels) * 100
        
        metadata = {
            'normalization': norm_params,
            'colormap': colormap,
            'shape': texture.shape,
            'coordinate_range': {
                'lat_min': float(lat.min()),
                'lat_max': float(lat.max()),
                'lon_min': float(lon.min()),
                'lon_max': float(lon.max())
            },
            'data_range': {
                'original_min': float(np.nanmin(data)),
                'original_max': float(np.nanmax(data)),
                'valid_pixels': valid_pixels,
                'total_pixels': total_pixels,
                'ocean_coverage_percent': round(ocean_coverage, 1)
            },
            'natural_land_mask': use_natural_land_mask,
            'land_mask_method': 'natural_nan_transparency' if use_natural_land_mask else 'none',
            'texture_type': 'standard_global'
        }
        
        return texture, metadata
    
    def _create_expanded_global_texture(self, data: np.ndarray, lon: np.ndarray, lat: np.ndarray,
                                       colormap: str, normalize_method: str, use_natural_land_mask: bool) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Create texture for limited coverage data expanded to global range."""
        from scipy.interpolate import RegularGridInterpolator
        
        # Define target global grid (180x360 for consistency with SST)
        target_lat = np.linspace(-89.5, 89.5, 180)
        target_lon = np.linspace(-179.5, 179.5, 360)
        
        # Initialize global data array with NaN (for areas outside source coverage)
        global_data = np.full((180, 360), np.nan)
        
        # Get source coordinate ranges
        lat_min, lat_max = float(lat.min()), float(lat.max())
        lon_min, lon_max = float(lon.min()), float(lon.max())
        
        # Use proper interpolation for data within coverage area
        # Create interpolator for valid (non-NaN) data only
        valid_mask = ~np.isnan(data)
        
        if np.any(valid_mask):
            # Create interpolator using RegularGridInterpolator
            # Enhanced: Use cubic interpolation for better quality when expanding coverage
            # Calculate expansion ratio to choose optimal method
            source_pixels = data.shape[0] * data.shape[1]
            target_pixels = 180 * 360
            expansion_ratio = target_pixels / source_pixels
            
            if expansion_ratio > 2:
                method = 'cubic'
                self.logger.info(f"Using cubic interpolation for global expansion (ratio: {expansion_ratio:.1f}x)")
            else:
                method = 'linear'
                self.logger.info(f"Using linear interpolation for global expansion (ratio: {expansion_ratio:.1f}x)")
            
            # The coordinate order must match the data array dimensions: (lat, lon)
            interpolator = RegularGridInterpolator(
                (lat, lon), data, 
                method=method,
                bounds_error=False, 
                fill_value=np.nan
            )
            
            # Create target coordinate grids - IMPORTANT: Use exact SST grid alignment
            target_lon_grid, target_lat_grid = np.meshgrid(target_lon, target_lat)
            
            # Only interpolate within the source data coverage area with buffer
            # Add small buffer to avoid edge effects
            lat_buffer = 0.1
            lon_buffer = 0.1
            coverage_mask = ((target_lat_grid >= (lat_min + lat_buffer)) & (target_lat_grid <= (lat_max - lat_buffer)) &
                           (target_lon_grid >= (lon_min + lon_buffer)) & (target_lon_grid <= (lon_max - lon_buffer)))
            
            # CRITICAL FIX: Ensure coordinate point order matches interpolator expectation
            # RegularGridInterpolator expects points as (lat, lon) to match the (lat, lon) coordinate order
            target_points = np.column_stack([
                target_lat_grid[coverage_mask].ravel(),
                target_lon_grid[coverage_mask].ravel()  
            ])
            
            # Interpolate data
            interpolated_values = interpolator(target_points)
            
            # Place interpolated values back into global grid
            global_data[coverage_mask] = interpolated_values.reshape(-1)
        
        # For areas outside source coverage (polar regions), keep as NaN (will appear as white/transparent)
        
        # Normalize the expanded data
        norm_data, norm_params = self.normalize_data(global_data, method=normalize_method)
        
        # Get colormap
        cmap = self._get_colormap(colormap)
            
        # Set NaN values to be transparent white
        if use_natural_land_mask:
            cmap = cmap.copy()
            cmap.set_bad(color='white', alpha=0.0)
            
        # Apply colormap
        rgba_data = cmap(norm_data)
        
        # Convert to uint8
        texture = (rgba_data * 255).astype(np.uint8)
        
        # Flip texture vertically to correct orientation for globe mapping
        texture = np.flipud(texture)
        
        # VALIDATE TEXTURE COORDINATE ALIGNMENT for debugging
        self._validate_texture_alignment(global_data, target_lon, target_lat, texture)
        
        # Create metadata
        valid_pixels = int(np.sum(~np.isnan(global_data)))
        total_pixels = global_data.size
        ocean_coverage = (valid_pixels / total_pixels) * 100
        
        metadata = {
            'normalization': norm_params,
            'colormap': colormap,
            'shape': texture.shape,
            'source_coordinate_range': {
                'lat_min': float(lat.min()),
                'lat_max': float(lat.max()),
                'lon_min': float(lon.min()),
                'lon_max': float(lon.max())
            },
            'target_coordinate_range': {
                'lat_min': -89.5,
                'lat_max': 89.5,
                'lon_min': -179.5,
                'lon_max': 179.5
            },
            'data_range': {
                'original_min': float(np.nanmin(data)),
                'original_max': float(np.nanmax(data)),
                'valid_pixels': valid_pixels,
                'total_pixels': total_pixels,
                'ocean_coverage_percent': round(ocean_coverage, 1)
            },
            'natural_land_mask': use_natural_land_mask,
            'land_mask_method': 'natural_nan_transparency' if use_natural_land_mask else 'none',
            'texture_type': 'expanded_global',
            'expansion_note': 'Limited coverage data expanded to global 180x360 grid'
        }
        
        return texture, metadata
    
    def _get_colormap(self, colormap: str):
        """Get matplotlib colormap object."""
        try:
            if colormap.startswith('cmocean.'):
                cmap_name = colormap.split('.')[1]
                cmap = getattr(cmocean.cm, cmap_name)
            else:
                cmap = plt.get_cmap(colormap)
        except (AttributeError, ValueError):
            self.logger.warning(f"Colormap {colormap} not found, using viridis")
            cmap = plt.get_cmap('viridis')
        return cmap
        
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
            
    def resample_to_sst_grid(self, data: np.ndarray, source_lon: np.ndarray, source_lat: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Resample data to high-resolution SST-aligned coordinate grid (720x1440 with 0.25° resolution).
        This ensures all datasets have identical coordinate systems for proper 3D globe alignment
        while maintaining high image quality.
        
        Args:
            data: Source data array (lat, lon)
            source_lon: Source longitude coordinates
            source_lat: Source latitude coordinates
            
        Returns:
            Tuple of (resampled_data, target_lon, target_lat)
        """
        from scipy.interpolate import RegularGridInterpolator
        
        # Define high-resolution target grid with SST-aligned coordinate system
        # Use 0.25° resolution (4x higher than original SST) while maintaining half-degree alignment
        target_lat = np.linspace(-89.625, 89.625, 720)  # High-res latitude grid with half-degree alignment
        target_lon = np.linspace(-179.625, 179.625, 1440)  # High-res longitude grid with half-degree alignment
        
        self.logger.info(f"Resampling from {data.shape} to high-resolution SST-aligned grid (720, 1440)")
        self.logger.info(f"Source: lat {source_lat.min():.1f}°-{source_lat.max():.1f}°, lon {source_lon.min():.1f}°-{source_lon.max():.1f}°")
        self.logger.info(f"Target: lat -89.6°-89.6°, lon -179.6°-179.6° (0.25° resolution)")
        
        # Create interpolator with source data - use cubic for better quality
        # Calculate upsampling ratio to choose optimal method
        source_pixels = data.shape[0] * data.shape[1]
        target_pixels = 720 * 1440
        upsampling_ratio = target_pixels / source_pixels
        
        if upsampling_ratio > 4:
            method = 'cubic'
            self.logger.info(f"Using cubic interpolation for SST grid resampling (ratio: {upsampling_ratio:.1f}x)")
        else:
            method = 'linear'
            self.logger.info(f"Using linear interpolation for SST grid resampling (ratio: {upsampling_ratio:.1f}x)")
        
        interpolator = RegularGridInterpolator(
            (source_lat, source_lon), data,
            method=method,
            bounds_error=False,
            fill_value=np.nan
        )
        
        # Create target coordinate grids
        target_lon_grid, target_lat_grid = np.meshgrid(target_lon, target_lat)
        
        # Prepare interpolation points
        target_points = np.column_stack([
            target_lat_grid.ravel(),
            target_lon_grid.ravel()
        ])
        
        # Interpolate data to target grid
        resampled_flat = interpolator(target_points)
        resampled_data = resampled_flat.reshape(720, 1440)
        
        # Count valid pixels
        source_valid = np.sum(~np.isnan(data))
        target_valid = np.sum(~np.isnan(resampled_data))
        self.logger.info(f"Resampling: {source_valid} → {target_valid} valid pixels")
        
        return resampled_data, target_lon, target_lat
        
    def resample_to_ultra_resolution(self, data: np.ndarray, source_lon: np.ndarray, source_lat: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Resample data to ultra-high resolution grid (4320x2041 pixels).
        This provides maximum detail for all datasets while maintaining coordinate alignment.
        
        Args:
            data: Source data array (lat, lon)
            source_lon: Source longitude coordinates
            source_lat: Source latitude coordinates
            
        Returns:
            Tuple of (resampled_data, target_lon, target_lat)
        """
        from scipy.interpolate import RegularGridInterpolator
        
        # Define target grid based on source data resolution
        # For 0.25° data (720x1440), use native or modest upsampling
        if data.shape == (720, 1440):  # 0.25° NOAA OISST
            # Use 2x upsampling for smooth rendering while preserving data integrity
            target_lat = np.linspace(-89.875, 89.875, 1440)  # 2x upsampling
            target_lon = np.linspace(-179.875, 179.875, 2880)  # 2x upsampling
        else:
            # For other resolutions, use ultra-high resolution grid
            target_lat = np.linspace(-89.958, 89.958, 2041)  # Ultra-high res latitude
            target_lon = np.linspace(-179.958, 179.958, 4320)  # Ultra-high res longitude
        
        target_shape = (len(target_lat), len(target_lon))
        self.logger.info(f"Resampling: {data.shape} → {target_shape}")
        self.logger.info(f"Source: lat {source_lat.min():.1f}°-{source_lat.max():.1f}°, lon {source_lon.min():.1f}°-{source_lon.max():.1f}°")
        self.logger.info(f"Target: lat {target_lat.min():.3f}°-{target_lat.max():.3f}°, lon {target_lon.min():.3f}°-{target_lon.max():.3f}°")
        
        # Check if we're already at or near target resolution
        source_pixels = data.shape[0] * data.shape[1]
        target_pixels = len(target_lat) * len(target_lon)
        upsampling_ratio = target_pixels / source_pixels
        
        if upsampling_ratio > 100:
            self.logger.warning(f"High upsampling ratio: {upsampling_ratio:.1f}x - quality may be limited")
        elif upsampling_ratio < 1.1:
            self.logger.info(f"Source data is already ultra-high resolution: {upsampling_ratio:.1f}x")
        else:
            self.logger.info(f"Reasonable upsampling ratio: {upsampling_ratio:.1f}x")
        
        # Create interpolator with optimal method based on upsampling ratio
        if upsampling_ratio > 20:
            # For heavy upsampling, use cubic for smoother results
            method = 'cubic'
            self.logger.info("Using cubic interpolation for heavy upsampling")
        elif upsampling_ratio > 2:
            # For moderate upsampling, use linear
            method = 'linear'
            self.logger.info("Using linear interpolation for moderate upsampling")
        else:
            # For minimal upsampling or downsampling, use linear
            method = 'linear'
            self.logger.info("Using linear interpolation for minimal resampling")
            
        interpolator = RegularGridInterpolator(
            (source_lat, source_lon), data,
            method=method,
            bounds_error=False,
            fill_value=np.nan
        )
        
        # Create target coordinate grids
        target_lon_grid, target_lat_grid = np.meshgrid(target_lon, target_lat)
        
        # Prepare interpolation points
        target_points = np.column_stack([
            target_lat_grid.ravel(),
            target_lon_grid.ravel()
        ])
        
        # Interpolate data to ultra-high resolution grid
        self.logger.info("Performing interpolation... (this may take a moment)")
        resampled_flat = interpolator(target_points)
        resampled_data = resampled_flat.reshape(len(target_lat), len(target_lon))
        
        # Count valid pixels
        source_valid = np.sum(~np.isnan(data))
        target_valid = np.sum(~np.isnan(resampled_data))
        self.logger.info(f"Ultra-resolution result: {source_valid:,} → {target_valid:,} valid pixels")
        
        return resampled_data, target_lon, target_lat
        
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
    
    def _validate_texture_alignment(self, data: np.ndarray, lon: np.ndarray, lat: np.ndarray, texture: np.ndarray) -> None:
        """
        Validate texture coordinate alignment for debugging alignment issues.
        
        Args:
            data: Original data array (lat, lon)
            lon: Longitude coordinates
            lat: Latitude coordinates  
            texture: Generated texture array (height, width, channels)
        """
        try:
            # Log coordinate system info for debugging
            self.logger.info(f"TEXTURE ALIGNMENT VALIDATION:")
            self.logger.info(f"  Data shape: {data.shape} (lat={data.shape[0]}, lon={data.shape[1]})")
            self.logger.info(f"  Coordinate arrays: lat={len(lat)}, lon={len(lon)}")
            self.logger.info(f"  Texture shape: {texture.shape} (height={texture.shape[0]}, width={texture.shape[1]})")
            self.logger.info(f"  Latitude range: {lat.min():.3f}° to {lat.max():.3f}°")
            self.logger.info(f"  Longitude range: {lon.min():.3f}° to {lon.max():.3f}°")
            
            # Validate that coordinate ranges match expected global values
            expected_lat_range = (-89.958, 89.958)  # Ultra-resolution target
            expected_lon_range = (-179.958, 179.958)  # Ultra-resolution target
            
            lat_range_diff = abs(lat.min() - expected_lat_range[0]) + abs(lat.max() - expected_lat_range[1])
            lon_range_diff = abs(lon.min() - expected_lon_range[0]) + abs(lon.max() - expected_lon_range[1])
            
            if lat_range_diff < 0.1 and lon_range_diff < 0.1:
                self.logger.info("  ✅ Coordinate ranges match expected global ultra-resolution grid")
            else:
                self.logger.warning(f"  ⚠️ Coordinate ranges differ from expected: lat_diff={lat_range_diff:.3f}, lon_diff={lon_range_diff:.3f}")
            
            # Validate texture dimensions match data dimensions
            expected_texture_shape = (data.shape[0], data.shape[1], 4)  # (height, width, RGBA channels)
            if texture.shape == expected_texture_shape:
                self.logger.info(f"  ✅ Texture dimensions match expected resolution ({data.shape[0]}×{data.shape[1]}×4)")
            else:
                self.logger.warning(f"  ⚠️ Texture dimensions {texture.shape} differ from expected {expected_texture_shape}")
            
            # Check coordinate ordering (latitude should be increasing from -90 to +90 after standardization)
            lat_increasing = np.all(np.diff(lat) > 0)
            lon_increasing = np.all(np.diff(lon) > 0)  
            
            self.logger.info(f"  Coordinate ordering: lat_increasing={lat_increasing}, lon_increasing={lon_increasing}")
            if lat_increasing and lon_increasing:
                self.logger.info("  ✅ Coordinate arrays are properly ordered")
            else:
                self.logger.warning("  ⚠️ Coordinate arrays may have ordering issues")
                
        except Exception as e:
            self.logger.warning(f"Texture alignment validation failed: {e}")