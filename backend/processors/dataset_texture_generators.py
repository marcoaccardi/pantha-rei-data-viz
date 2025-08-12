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


# Removed AcidityTextureGenerator and CurrentsTextureGenerator classes
# as these texture categories are no longer supported due to low data quality.


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