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
                    
                # Generate texture with natural land masking
                colormap = self.get_scientific_colormap('temperature')
                texture, metadata = self.data_to_texture(
                    sst_data, lon, lat, colormap, 
                    normalize_method='percentile',
                    use_natural_land_mask=True
                )
                
                # Add SST-specific metadata
                metadata.update({
                    'dataset': 'sea_surface_temperature',
                    'variable': sst_var,
                    'units': 'degrees_celsius',
                    'date': date_str,
                    'data_source': 'NOAA OISST'
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
        
    def process_netcdf_to_texture(self, input_path: Union[str, Path], 
                                 output_directory: Union[str, Path] = None) -> bool:
        """
        Process acidity NetCDF file to pH texture.
        
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
                    
                # Generate texture with pH-appropriate colormap and natural land masking
                colormap = self.get_scientific_colormap('ph')
                texture, metadata = self.data_to_texture(
                    ph_data, lon, lat, colormap,
                    normalize_method='custom',
                    use_natural_land_mask=True
                )
                
                # Add acidity-specific metadata
                metadata.update({
                    'dataset': 'ocean_acidity',
                    'variable': 'ph',
                    'units': 'pH_scale',
                    'date': date_str,
                    'data_source': 'CMEMS Biogeochemistry',
                    'ph_range': [7.0, 8.5]  # Typical ocean pH range
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
        Process currents NetCDF file to current speed texture.
        
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
                
                # Remove time dimension if present
                if speed_data.ndim > 2:
                    speed_data = np.squeeze(speed_data)
                    
                # Generate texture with speed-appropriate colormap and natural land masking
                colormap = self.get_scientific_colormap('speed')
                texture, metadata = self.data_to_texture(
                    speed_data, lon, lat, colormap,
                    normalize_method='percentile',
                    use_natural_land_mask=True
                )
                
                # Add currents-specific metadata
                metadata.update({
                    'dataset': 'ocean_currents',
                    'variable': 'current_speed',
                    'units': 'm/s',
                    'date': date_str,
                    'data_source': 'CMEMS Ocean Physics'
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