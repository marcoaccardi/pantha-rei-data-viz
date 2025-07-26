#!/usr/bin/env python3
"""
Dataset-specific texture generators for ocean data visualization.
Each generator handles the specific requirements of different ocean datasets.
"""

import numpy as np
import xarray as xr
from pathlib import Path
from typing import Union, Dict, Any, Optional
import logging
from datetime import datetime
import re

from .texture_generator import TextureGenerator

class SSTTextureGenerator(TextureGenerator):
    """Generator for Sea Surface Temperature textures."""
    
    def __init__(self, output_base_path: Union[str, Path] = None):
        super().__init__(output_base_path)
        self.dataset_name = 'sst'
        
    def process_netcdf_to_texture(self, input_path: Union[str, Path], 
                                 output_directory: Union[str, Path] = None) -> bool:
        """
        Process SST NetCDF file to thermal texture using high-resolution raw data.
        
        Args:
            input_path: Path to SST NetCDF file (uses corresponding raw file for higher resolution)
            output_directory: Output directory (optional)
            
        Returns:
            True if successful
        """
        try:
            input_path = Path(input_path)
            
            # Extract date from filename
            date_match = re.search(r'(\d{8})', input_path.name)
            if not date_match:
                self.logger.error(f"Cannot extract date from filename: {input_path.name}")
                return False
            date_str = date_match.group(1)
            
            # Set output directory
            if output_directory is None:
                output_directory = self.output_base_path / self.dataset_name / date_str[:4]
            else:
                output_directory = Path(output_directory)
                
            # Try to find corresponding high-resolution raw file first
            raw_sst_path = Path(f"/Volumes/Backup/panta-rhei-data-map/ocean-data/raw/sst/{date_str[:4]}/{date_str[4:6]}/oisst-avhrr-v02r01.{date_str}.nc")
            
            if raw_sst_path.exists():
                self.logger.info(f"Using high-resolution raw SST data: {raw_sst_path}")
                data_file = raw_sst_path
            else:
                self.logger.warning(f"Raw SST file not found, falling back to processed file: {input_path}")
                data_file = input_path
                
            # Load data
            with xr.open_dataset(data_file) as ds:
                # Get SST variable (try different possible names)
                sst_var = None
                for var_name in ['sst', 'analysed_sst', 'sea_surface_temperature']:
                    if var_name in ds.data_vars:
                        sst_var = var_name
                        break
                        
                if sst_var is None:
                    self.logger.error(f"No SST variable found in {data_file}")
                    return False
                    
                sst_data = ds[sst_var].values
                lat = ds.lat.values if 'lat' in ds.coords else ds.latitude.values
                lon = ds.lon.values if 'lon' in ds.coords else ds.longitude.values
                
                # Remove time dimension if present
                if sst_data.ndim > 2:
                    sst_data = np.squeeze(sst_data)
                    
                # Handle coordinate transformation if using raw data (0-360° to -180-180°)
                if data_file == raw_sst_path and lon.max() > 180:
                    self.logger.info("Converting longitude coordinates from 0-360° to -180-180°")
                    # Reorder longitude and corresponding data
                    lon_adjusted = np.where(lon > 180, lon - 360, lon)
                    # Sort by longitude
                    lon_sort_idx = np.argsort(lon_adjusted)
                    lon = lon_adjusted[lon_sort_idx]
                    sst_data = sst_data[:, lon_sort_idx] if sst_data.ndim == 2 else sst_data[lon_sort_idx]
                    
                # Convert from Kelvin to Celsius if needed
                if np.nanmean(sst_data) > 100:  # Likely in Kelvin
                    sst_data = sst_data - 273.15
                
                self.logger.info(f"Original SST data shape: {sst_data.shape}, coverage: {lat.min():.1f}° to {lat.max():.1f}°")
                self.logger.info(f"Using {'raw' if data_file == raw_sst_path else 'processed'} SST data")
                
                # COORDINATE VALIDATION: Ensure data dimensions match coordinate array lengths
                if len(lat) != sst_data.shape[0] or len(lon) != sst_data.shape[1]:
                    self.logger.warning(f"SST dimension mismatch: data {sst_data.shape} vs coords (lat:{len(lat)}, lon:{len(lon)})")
                    # Check if data needs to be transposed
                    if len(lat) == sst_data.shape[1] and len(lon) == sst_data.shape[0]:
                        self.logger.info("Transposing SST data to match coordinate dimensions")
                        sst_data = sst_data.T
                    else:
                        self.logger.error(f"Cannot resolve SST dimension mismatch: data {sst_data.shape} vs coords (lat:{len(lat)}, lon:{len(lon)})")
                        return False
                
                # STANDARDIZED COORDINATE SYSTEM: Resample SST to ultra-resolution grid (4320x2041)
                sst_data_ultra, lon_ultra, lat_ultra = self.resample_to_ultra_resolution(sst_data, lon, lat)
                self.logger.info(f"Ultra-resolution SST shape: {sst_data_ultra.shape}")
                    
                # Generate texture with natural land masking using ultra-resolution grid
                colormap = self.get_scientific_colormap('temperature')
                texture, metadata = self._create_standard_texture(
                    sst_data_ultra, lon_ultra, lat_ultra, colormap, 'percentile', True
                )
                
                # Add SST-specific metadata
                metadata.update({
                    'dataset': 'sea_surface_temperature',
                    'variable': sst_var,
                    'units': 'degrees_celsius',
                    'date': date_str,
                    'data_source': 'NOAA OISST',
                    'coordinate_resampling': f'Ultra-resolution resampling to 4320×2041 grid using {"raw" if data_file == raw_sst_path else "processed"} data',
                    'source_resolution': f'{sst_data.shape[1]}×{sst_data.shape[0]}',
                    'target_resolution': '4320×2041'
                })
                
                # Save texture
                filename = self.generate_filename(self.dataset_name, date_str)
                output_path = output_directory / filename
                
                return self.save_texture(texture, output_path, metadata)
                
        except Exception as e:
            self.logger.error(f"Failed to process SST file {input_path}: {e}")
            return False

class AcidityTextureGenerator(TextureGenerator):
    """Generator for Ocean Acidity (pH) textures."""
    
    def __init__(self, output_base_path: Union[str, Path] = None):
        super().__init__(output_base_path)
        self.dataset_name = 'acidity'
        
    def _enhance_land_masking(self, data: np.ndarray, lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
        """
        Apply enhanced land masking for high-resolution acidity data to remove coastal artifacts.
        
        Args:
            data: pH data array
            lon: Longitude coordinates
            lat: Latitude coordinates
            
        Returns:
            Enhanced masked data array
        """
        enhanced_data = data.copy()
        
        # Create coordinate grids
        lon_grid, lat_grid = np.meshgrid(lon, lat)
        
        # Remove invalid pH values (should be between 6.0 and 9.0 for ocean)
        invalid_ph = (data < 6.0) | (data > 9.0)
        enhanced_data[invalid_ph] = np.nan
        
        # Enhanced coastal masking for major inland areas that may have pH data
        # These represent inland seas, large lakes, or coastal artifacts that should be masked
        inland_regions = [
            # Great Lakes region (North America)
            (-90, -75, 40, 50),
            # Caspian Sea region
            (45, 55, 35, 50),
            # Aral Sea region  
            (55, 65, 40, 50),
            # Large inland areas in Siberia/Russia that may have artifacts
            (60, 180, 60, 80),
            # Sahara region artifacts (if any ocean data appears over North Africa)
            (-10, 40, 15, 35),
            # Australian inland (if any ocean data appears over central Australia)
            (120, 145, -30, -15),
            # Greenland interior (remove any artifacts over ice sheet)
            (-45, -10, 70, 85),
        ]
        
        for lon_min, lon_max, lat_min, lat_max in inland_regions:
            mask = ((lon_grid >= lon_min) & (lon_grid <= lon_max) & 
                   (lat_grid >= lat_min) & (lat_grid <= lat_max))
            
            # For these regions, be very conservative - only keep values if they're clearly oceanic
            # (high confidence ocean areas near coastlines)
            region_data = enhanced_data[mask]
            if np.any(~np.isnan(region_data)):
                # Count valid neighbors - if a pixel has few valid ocean neighbors, mask it
                from scipy import ndimage
                valid_mask = ~np.isnan(enhanced_data)
                
                # Apply morphological erosion to remove isolated coastal pixels
                kernel = np.ones((3, 3))  # 3x3 kernel for neighbor check
                eroded_mask = ndimage.binary_erosion(valid_mask, kernel)
                
                # Mask pixels in inland regions that don't have enough valid neighbors
                inland_to_mask = mask & ~eroded_mask
                enhanced_data[inland_to_mask] = np.nan
        
        pixels_removed = np.sum(~np.isnan(data)) - np.sum(~np.isnan(enhanced_data))
        if pixels_removed > 0:
            self.logger.info(f"Enhanced land masking removed {pixels_removed} coastal/inland artifacts")
        
        return enhanced_data
        
    def process_netcdf_to_texture(self, input_path: Union[str, Path], 
                                 output_directory: Union[str, Path] = None) -> bool:
        """
        Process acidity NetCDF file to pH texture with standardized resolution.
        
        Args:
            input_path: Path to acidity NetCDF file
            output_directory: Output directory (optional)
            
        Returns:
            True if successful
        """
        try:
            input_path = Path(input_path)
            
            # Extract date from filename
            date_match = re.search(r'(\d{8})', input_path.name)
            if not date_match:
                self.logger.error(f"Cannot extract date from filename: {input_path.name}")
                return False
            date_str = date_match.group(1)
            
            # Set output directory
            if output_directory is None:
                output_directory = self.output_base_path / self.dataset_name / date_str[:4]
            else:
                output_directory = Path(output_directory)
                
            # Load data
            with xr.open_dataset(input_path) as ds:
                # Get pH variable
                if 'ph' not in ds.data_vars:
                    self.logger.error(f"No pH variable found in {input_path}")
                    return False
                    
                ph_data = ds['ph'].values
                lat = ds.lat.values if 'lat' in ds.coords else ds.latitude.values
                lon = ds.lon.values if 'lon' in ds.coords else ds.longitude.values
                
                # Remove time dimension if present
                if ph_data.ndim > 2:
                    ph_data = np.squeeze(ph_data)
                
                self.logger.info(f"Original acidity data shape: {ph_data.shape}, coverage: {lat.min():.1f}° to {lat.max():.1f}°")
                
                # COORDINATE VALIDATION: Ensure data dimensions match coordinate array lengths
                if len(lat) != ph_data.shape[0] or len(lon) != ph_data.shape[1]:
                    self.logger.warning(f"Acidity dimension mismatch: data {ph_data.shape} vs coords (lat:{len(lat)}, lon:{len(lon)})")
                    # Check if data needs to be transposed
                    if len(lat) == ph_data.shape[1] and len(lon) == ph_data.shape[0]:
                        self.logger.info("Transposing acidity data to match coordinate dimensions")
                        ph_data = ph_data.T
                    else:
                        self.logger.error(f"Cannot resolve acidity dimension mismatch: data {ph_data.shape} vs coords (lat:{len(lat)}, lon:{len(lon)})")
                        return False
                
                # Apply additional land masking for coastal artifacts after coordinate validation
                ph_data = self._enhance_land_masking(ph_data, lon, lat)
                
                # STANDARDIZED COORDINATE SYSTEM: Resample to ultra-resolution grid (4320x2041)
                ph_data_ultra, lon_ultra, lat_ultra = self.resample_to_ultra_resolution(ph_data, lon, lat)
                self.logger.info(f"Ultra-resolution acidity shape: {ph_data_ultra.shape}")
                    
                # Generate texture with pH-appropriate colormap using ultra-resolution grid
                colormap = self.get_scientific_colormap('ph')
                texture, metadata = self._create_standard_texture(
                    ph_data_ultra, lon_ultra, lat_ultra, colormap, 'custom', True
                )
                
                # Add acidity-specific metadata
                metadata.update({
                    'dataset': 'ocean_acidity',
                    'variable': 'ph',
                    'units': 'pH_scale',
                    'date': date_str,
                    'data_source': 'CMEMS Biogeochemistry',
                    'ph_range': [7.0, 8.5],  # Typical ocean pH range
                    'resolution_note': 'Enhanced land masking applied for coastal accuracy',
                    'coordinate_resampling': 'Ultra-resolution resampling to 4320×2041 grid for maximum detail',
                    'source_resolution': f'{ph_data.shape[1]}×{ph_data.shape[0]}',
                    'target_resolution': '4320×2041'
                })
                
                # Save texture
                filename = self.generate_filename(self.dataset_name, date_str)
                output_path = output_directory / filename
                
                return self.save_texture(texture, output_path, metadata)
                
        except Exception as e:
            self.logger.error(f"Failed to process acidity file {input_path}: {e}")
            return False

class CurrentsTextureGenerator(TextureGenerator):
    """Generator for Ocean Currents textures."""
    
    def __init__(self, output_base_path: Union[str, Path] = None):
        super().__init__(output_base_path)
        self.dataset_name = 'currents'
        
    def process_netcdf_to_texture(self, input_path: Union[str, Path], 
                                 output_directory: Union[str, Path] = None) -> bool:
        """
        Process currents NetCDF file to current speed texture with corrected coordinate alignment.
        
        CRITICAL FIXES APPLIED:
        - Validates coordinate-data dimension alignment
        - Removes ultra-resolution shortcut that skipped coordinate harmonization
        - Forces standardized coordinate system for perfect alignment with other datasets
        - Applies coordinate validation and correction
        
        Args:
            input_path: Path to currents NetCDF file
            output_directory: Output directory (optional)
            
        Returns:
            True if successful
        """
        try:
            input_path = Path(input_path)
            
            # Extract date from filename
            date_match = re.search(r'(\d{8})', input_path.name)
            if not date_match:
                self.logger.error(f"Cannot extract date from filename: {input_path.name}")
                return False
            date_str = date_match.group(1)
            
            # Set output directory
            if output_directory is None:
                output_directory = self.output_base_path / self.dataset_name / date_str[:4]
            else:
                output_directory = Path(output_directory)
                
            # Load data
            with xr.open_dataset(input_path) as ds:
                # Prefer current_speed if available, otherwise calculate from u/v
                if 'current_speed' in ds.data_vars:
                    speed_data = ds['current_speed'].values
                elif 'uo' in ds.data_vars and 'vo' in ds.data_vars:
                    u_data = ds['uo'].values
                    v_data = ds['vo'].values
                    # Calculate speed magnitude
                    speed_data = np.sqrt(u_data**2 + v_data**2)
                else:
                    self.logger.error(f"No current velocity data found in {input_path}")
                    return False
                    
                lat = ds.lat.values if 'lat' in ds.coords else ds.latitude.values
                lon = ds.lon.values if 'lon' in ds.coords else ds.longitude.values
                
                # Remove time dimension if present - Enhanced handling for multiple dimensions
                self.logger.info(f"Raw currents data shape: {speed_data.shape}")
                
                # Handle multiple dimensions properly
                if speed_data.ndim > 2:
                    self.logger.info(f"Reducing {speed_data.ndim}D data to 2D")
                    if speed_data.ndim == 3:
                        # Could be (time, lat, lon) or (depth, lat, lon) - take first slice
                        speed_data = speed_data[0, :, :]
                        self.logger.info("Extracted first slice from 3D data (time/depth=0)")
                    elif speed_data.ndim == 4:
                        # Could be (time, depth, lat, lon) - take first time and depth
                        speed_data = speed_data[0, 0, :, :]
                        self.logger.info("Extracted first slice from 4D data (time=0, depth=0)")
                    else:
                        # For higher dimensions, squeeze and take first 2D slice
                        speed_data = np.squeeze(speed_data)
                        if speed_data.ndim > 2:
                            speed_data = speed_data[0, :, :] if speed_data.ndim == 3 else speed_data[0, 0, :, :]
                        self.logger.info(f"Squeezed and extracted 2D data, final shape: {speed_data.shape}")
                
                self.logger.info(f"Processed currents data shape: {speed_data.shape}, coverage: {lat.min():.1f}° to {lat.max():.1f}°")
                self.logger.info(f"Coordinate ranges - Lat: {lat.min():.3f}° to {lat.max():.3f}°, Lon: {lon.min():.3f}° to {lon.max():.3f}°")
                
                # CRITICAL FIX: Validate and correct coordinate-data alignment
                # Ensure data dimensions match coordinate array lengths
                if len(lat) != speed_data.shape[0] or len(lon) != speed_data.shape[1]:
                    self.logger.warning(f"Dimension mismatch detected: data {speed_data.shape} vs coords (lat:{len(lat)}, lon:{len(lon)})")
                    # Check if data needs to be transposed
                    if len(lat) == speed_data.shape[1] and len(lon) == speed_data.shape[0]:
                        self.logger.info("Transposing data to match coordinate dimensions")
                        speed_data = speed_data.T
                    else:
                        self.logger.error(f"Cannot resolve dimension mismatch: data {speed_data.shape} vs coords (lat:{len(lat)}, lon:{len(lon)})")
                        return False
                
                # STANDARDIZED COORDINATE SYSTEM: Always resample to global standard grid
                # This ensures perfect alignment with other datasets (SST, acidity, etc.)
                self.logger.info("Applying standardized coordinate system harmonization for alignment")
                
                # Resample to ultra-resolution grid with EXACT SST alignment
                speed_data_ultra, lon_ultra, lat_ultra = self.resample_to_ultra_resolution(speed_data, lon, lat)
                self.logger.info(f"Standardized currents shape: {speed_data_ultra.shape}")
                self.logger.info(f"Standardized coordinate ranges - Lat: {lat_ultra.min():.3f}° to {lat_ultra.max():.3f}°, Lon: {lon_ultra.min():.3f}° to {lon_ultra.max():.3f}°")
                    
                # Generate texture with speed-appropriate colormap using standardized grid
                colormap = self.get_scientific_colormap('speed')
                texture, metadata = self._create_standard_texture(
                    speed_data_ultra, lon_ultra, lat_ultra, colormap, 'percentile', True
                )
                
                # Add currents-specific metadata with coordinate alignment info
                metadata.update({
                    'dataset': 'ocean_currents',
                    'variable': 'current_speed',
                    'units': 'm/s',
                    'date': date_str,
                    'data_source': 'CMEMS Ocean Physics',
                    'coordinate_alignment': 'Standardized to global grid for perfect alignment with other datasets',
                    'coordinate_resampling': 'Ultra-resolution resampling to 4320×2041 grid with coordinate validation',
                    'source_resolution': f'{speed_data.shape[1]}×{speed_data.shape[0]}',
                    'target_resolution': '4320×2041',
                    'coordinate_validation': 'Applied dimension validation and correction',
                    'alignment_note': 'Fixed coordinate system alignment issue for proper globe visualization'
                })
                
                # Save texture
                filename = self.generate_filename(self.dataset_name, date_str)
                output_path = output_directory / filename
                
                return self.save_texture(texture, output_path, metadata)
                
        except Exception as e:
            self.logger.error(f"Failed to process currents file {input_path}: {e}")
            return False


class MicroplasticsTextureGenerator(TextureGenerator):
    """Generator for Microplastics concentration textures."""
    
    def __init__(self, output_base_path: Union[str, Path] = None):
        super().__init__(output_base_path)
        self.dataset_name = 'microplastics'
        
    def process_netcdf_to_texture(self, input_path: Union[str, Path], 
                                 output_directory: Union[str, Path] = None) -> bool:
        """
        Process microplastics NetCDF file to concentration texture.
        
        Args:
            input_path: Path to microplastics NetCDF file
            output_directory: Output directory (optional)
            
        Returns:
            True if successful
        """
        try:
            input_path = Path(input_path)
            
            # Extract date from filename (might be different format for microplastics)
            date_match = re.search(r'(\d{8})', input_path.name)
            if not date_match:
                # Try other date formats if needed
                self.logger.warning(f"Cannot extract date from filename: {input_path.name}")
                date_str = "unknown"
            else:
                date_str = date_match.group(1)
            
            # Set output directory
            if output_directory is None:
                output_directory = self.output_base_path / self.dataset_name / date_str[:4] if date_str != "unknown" else self.output_base_path / self.dataset_name / "2024"
            else:
                output_directory = Path(output_directory)
                
            # Load data
            with xr.open_dataset(input_path) as ds:
                # Try to find concentration variable (name may vary)
                concentration_var = None
                possible_vars = ['concentration', 'microplastic_concentration', 'particles_per_km2', 'density']
                
                for var_name in possible_vars:
                    if var_name in ds.data_vars:
                        concentration_var = var_name
                        break
                        
                if concentration_var is None:
                    # Use first data variable if none match expected names
                    if len(ds.data_vars) > 0:
                        concentration_var = list(ds.data_vars.keys())[0]
                        self.logger.warning(f"Using variable '{concentration_var}' for microplastics concentration")
                    else:
                        self.logger.error(f"No data variables found in {input_path}")
                        return False
                    
                conc_data = ds[concentration_var].values
                lat = ds.lat.values if 'lat' in ds.coords else ds.latitude.values
                lon = ds.lon.values if 'lon' in ds.coords else ds.longitude.values
                
                # Remove time dimension if present
                if conc_data.ndim > 2:
                    conc_data = np.squeeze(conc_data)
                    
                # Generate texture with concentration colormap and natural land masking
                colormap = self.get_scientific_colormap('concentration')
                texture, metadata = self.data_to_texture(
                    conc_data, lon, lat, colormap,
                    normalize_method='percentile',
                    use_natural_land_mask=True
                )
                
                # Add microplastics-specific metadata
                metadata.update({
                    'dataset': 'microplastics',
                    'variable': concentration_var,
                    'units': 'particles/km²',  # Common unit for microplastics
                    'date': date_str,
                    'data_source': 'NCEI Microplastics Database'
                })
                
                # Save texture
                filename = self.generate_filename(self.dataset_name, date_str)
                output_path = output_directory / filename
                
                return self.save_texture(texture, output_path, metadata)
                
        except Exception as e:
            self.logger.error(f"Failed to process microplastics file {input_path}: {e}")
            return False