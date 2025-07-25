#!/usr/bin/env python3
"""
Acidity data processor for converting biogeochemistry data to unified coordinate system.
Processes pH and dissolved inorganic carbon (DIC) data from CMEMS.
"""

import xarray as xr
import numpy as np
from pathlib import Path
from typing import Union, Optional, Dict, Any
import logging
from datetime import date
from .coordinate_harmonizer import CoordinateHarmonizer

class AcidityProcessor:
    """Handles processing of ocean acidity/biogeochemistry data."""
    
    def __init__(self):
        """Initialize acidity processor."""
        self.logger = logging.getLogger(__name__)
        self.harmonizer = CoordinateHarmonizer()
    
    def validate_acidity_data(self, ds: xr.Dataset) -> Dict[str, Any]:
        """
        Validate acidity dataset for expected variables and ranges.
        
        Args:
            ds: Input xarray Dataset
            
        Returns:
            Dictionary with validation results
        """
        validation = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'variables_found': [],
            'data_ranges': {}
        }
        
        # Expected variables for biogeochemistry data
        expected_vars = {
            'ph': {'min': 6.0, 'max': 9.0, 'description': 'pH'},
            'dissic': {'min': 0.0, 'max': 5.0, 'description': 'Dissolved Inorganic Carbon (mol/m³)'},
            'dic': {'min': 0.0, 'max': 5.0, 'description': 'Dissolved Inorganic Carbon (mol/m³)'},
            'talk': {'min': 0.0, 'max': 3.0, 'description': 'Total Alkalinity (mol/m³)'},
            'o2': {'min': 0.0, 'max': 500.0, 'description': 'Dissolved Oxygen (mmol/m³)'},
            'no3': {'min': 0.0, 'max': 50.0, 'description': 'Nitrate (mmol/m³)'},
            'po4': {'min': 0.0, 'max': 5.0, 'description': 'Phosphate (mmol/m³)'},
            'si': {'min': 0.0, 'max': 200.0, 'description': 'Silicate (mmol/m³)'}
        }
        
        # Check for available variables
        for var_name, var_info in expected_vars.items():
            if var_name in ds.data_vars:
                validation['variables_found'].append(var_name)
                
                # Check data ranges
                var_data = ds[var_name]
                var_min = float(var_data.min())
                var_max = float(var_data.max())
                
                validation['data_ranges'][var_name] = {
                    'min': var_min,
                    'max': var_max,
                    'description': var_info['description']
                }
                
                # Validate ranges
                if var_min < var_info['min'] or var_max > var_info['max']:
                    validation['warnings'].append(
                        f"{var_info['description']} values ({var_min:.3f} - {var_max:.3f}) "
                        f"outside expected range ({var_info['min']} - {var_info['max']})"
                    )
        
        # Check if we have at least one key biogeochemistry variable
        key_vars = ['ph', 'dissic', 'dic', 'talk']
        found_key_vars = [var for var in key_vars if var in validation['variables_found']]
        
        if not found_key_vars:
            validation['errors'].append(
                f"No key biogeochemistry variables found. Expected one of: {key_vars}"
            )
            validation['valid'] = False
        
        # Validate coordinate system
        coord_validation = self.harmonizer.validate_geographic_bounds(ds)
        if not coord_validation['valid']:
            validation['errors'].extend(coord_validation['errors'])
            validation['valid'] = False
        
        validation['warnings'].extend(coord_validation['warnings'])
        
        return validation
    
    def select_surface_layer(self, ds: xr.Dataset, depth_threshold: float = 5.0) -> xr.Dataset:
        """
        Select surface layer data from 3D biogeochemistry dataset.
        
        Args:
            ds: Input xarray Dataset with depth dimension
            depth_threshold: Maximum depth to include (meters)
            
        Returns:
            Dataset with surface layer data
        """
        # Find depth coordinate
        depth_names = ['depth', 'lev', 'z', 'level']
        depth_coord = None
        depth_name = None
        
        for name in depth_names:
            if name in ds.dims:
                depth_coord = ds[name]
                depth_name = name
                break
        
        if depth_coord is None:
            self.logger.warning("No depth coordinate found, assuming surface data")
            return ds
        
        # Select surface points (within depth threshold)
        surface_mask = depth_coord <= depth_threshold
        
        if not surface_mask.any():
            # If no points within threshold, take the shallowest level
            self.logger.warning(f"No depths <= {depth_threshold}m found, using shallowest level")
            surface_idx = depth_coord.argmin()
            ds_surface = ds.isel({depth_name: surface_idx})
        else:
            # Take the shallowest level within threshold
            valid_depths = depth_coord.where(surface_mask)
            surface_idx = valid_depths.argmin()
            ds_surface = ds.isel({depth_name: surface_idx})
        
        # Add metadata about depth selection
        selected_depth = float(ds_surface[depth_name])
        ds_surface.attrs.update({
            'surface_selection_method': f'Selected depth <= {depth_threshold}m',
            'selected_depth': f'{selected_depth:.2f}m',
            'original_depth_range': f'{float(depth_coord.min()):.2f}m to {float(depth_coord.max()):.2f}m'
        })
        
        return ds_surface
    
    def process_acidity_variables(self, ds: xr.Dataset) -> xr.Dataset:
        """
        Process and standardize acidity variables.
        
        Args:
            ds: Input dataset with acidity variables
            
        Returns:
            Dataset with processed variables
        """
        ds_processed = ds.copy()
        
        # Process pH data
        if 'ph' in ds_processed.data_vars:
            ph_data = ds_processed['ph']
            
            # Add standard attributes
            ph_data.attrs.update({
                'standard_name': 'sea_water_ph_reported_on_total_scale',
                'long_name': 'pH of seawater (total scale)',
                'units': '1',
                'valid_range': [6.0, 9.0],
                'description': 'pH of seawater on the total scale at in situ temperature and pressure'
            })
            
            # Quality control: mask extreme values
            ph_masked = ph_data.where((ph_data >= 6.0) & (ph_data <= 9.0))
            ds_processed['ph'] = ph_masked
        
        # Process DIC data
        if 'dic' in ds_processed.data_vars:
            dic_data = ds_processed['dic']
            
            # Add standard attributes
            dic_data.attrs.update({
                'standard_name': 'mole_concentration_of_dissolved_inorganic_carbon_in_sea_water',
                'long_name': 'Dissolved inorganic carbon concentration',
                'units': 'mol m-3',
                'valid_range': [0.0, 5.0],
                'description': 'Concentration of dissolved inorganic carbon in seawater'
            })
            
            # Quality control: mask negative values
            dic_masked = dic_data.where(dic_data >= 0.0)
            ds_processed['dic'] = dic_masked
            
        # Process DISSIC data (alternative DIC variable name)
        if 'dissic' in ds_processed.data_vars:
            dissic_data = ds_processed['dissic']
            
            # Add standard attributes
            dissic_data.attrs.update({
                'standard_name': 'mole_concentration_of_dissolved_inorganic_carbon_in_sea_water',
                'long_name': 'Dissolved inorganic carbon concentration',
                'units': 'mol m-3',
                'valid_range': [0.0, 5.0],
                'description': 'Concentration of dissolved inorganic carbon in seawater'
            })
            
            # Quality control: mask negative values
            dissic_masked = dissic_data.where(dissic_data >= 0.0)
            ds_processed['dissic'] = dissic_masked
        
        # Process Total Alkalinity
        if 'talk' in ds_processed.data_vars:
            talk_data = ds_processed['talk']
            
            talk_data.attrs.update({
                'standard_name': 'sea_water_alkalinity_expressed_as_mole_equivalent',
                'long_name': 'Total alkalinity',
                'units': 'mol m-3',
                'valid_range': [0.0, 3.0],
                'description': 'Total alkalinity of seawater'
            })
            
            # Quality control: mask negative values
            talk_masked = talk_data.where(talk_data >= 0.0)
            ds_processed['talk'] = talk_masked
        
        # Add processing metadata
        ds_processed.attrs.update({
            'acidity_processing_date': str(date.today()),
            'acidity_processing_note': 'Quality controlled and standardized biogeochemistry variables'
        })
        
        return ds_processed
    
    def harmonize_to_unified_coords(self, ds: xr.Dataset) -> xr.Dataset:
        """
        Convert dataset to unified coordinate system (-180 to 180 longitude).
        
        Args:
            ds: Input dataset
            
        Returns:
            Dataset with harmonized coordinates
        """
        # Use coordinate harmonizer to convert to -180-180 longitude
        ds_harmonized = self.harmonizer.harmonize_dataset(ds, target_convention='-180-180')
        
        # Ensure coordinate names are standardized
        coord_mapping = {}
        
        # Standardize latitude coordinate name
        if 'latitude' in ds_harmonized.dims:
            coord_mapping['latitude'] = 'lat'
        
        # Standardize longitude coordinate name  
        if 'longitude' in ds_harmonized.dims:
            coord_mapping['longitude'] = 'lon'
        
        if coord_mapping:
            ds_harmonized = ds_harmonized.rename(coord_mapping)
        
        return ds_harmonized
    
    def process_dataset(self, ds: xr.Dataset, surface_only: bool = True) -> xr.Dataset:
        """
        Complete processing pipeline for acidity dataset.
        
        Args:
            ds: Input dataset
            surface_only: Whether to extract surface layer only
            
        Returns:
            Fully processed dataset
        """
        # Validate input data
        validation = self.validate_acidity_data(ds)
        
        if not validation['valid']:
            raise ValueError(f"Input validation failed: {validation['errors']}")
        
        # Log warnings
        for warning in validation['warnings']:
            self.logger.warning(warning)
        
        # Select surface layer if requested and if depth dimension exists
        if surface_only:
            ds_processed = self.select_surface_layer(ds)
        else:
            ds_processed = ds.copy()
        
        # Process variables
        ds_processed = self.process_acidity_variables(ds_processed)
        
        # Harmonize coordinates
        ds_processed = self.harmonize_to_unified_coords(ds_processed)
        
        # Add final processing metadata
        ds_processed.attrs.update({
            'processing_pipeline': 'acidity_processor',
            'processing_version': '1.0',
            'variables_processed': str(validation['variables_found']),
            'unified_coordinate_system': 'latitude: -90 to 90, longitude: -180 to 180',
            'surface_only': str(surface_only)
        })
        
        return ds_processed
    
    def process_file(self, input_path: Union[str, Path], output_path: Union[str, Path],
                    surface_only: bool = True) -> bool:
        """
        Process a NetCDF file containing acidity data.
        
        Args:
            input_path: Path to input NetCDF file
            output_path: Path for output NetCDF file
            surface_only: Whether to extract surface layer only
            
        Returns:
            True if successful, False otherwise
        """
        try:
            input_path = Path(input_path)
            output_path = Path(output_path)
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Load, process, and save dataset
            with xr.open_dataset(input_path) as ds:
                ds_processed = self.process_dataset(ds, surface_only)
                
                # Save processed dataset
                ds_processed.to_netcdf(output_path, format='NETCDF4', engine='netcdf4')
                
                self.logger.info(f"Successfully processed acidity data: {input_path} -> {output_path}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error processing acidity file {input_path}: {e}")
            return False
    
    def batch_process_directory(self, input_dir: Union[str, Path], output_dir: Union[str, Path],
                               surface_only: bool = True, pattern: str = "*.nc") -> Dict[str, Any]:
        """
        Batch process all acidity NetCDF files in a directory.
        
        Args:
            input_dir: Directory containing input NetCDF files
            output_dir: Directory for output files
            surface_only: Whether to extract surface layer only
            pattern: File pattern to match
            
        Returns:
            Dictionary with processing results
        """
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)
        
        # Find all NetCDF files
        input_files = list(input_dir.rglob(pattern))
        
        results = {
            'total_files': len(input_files),
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        for input_file in input_files:
            # Construct output path maintaining directory structure
            relative_path = input_file.relative_to(input_dir)
            # Change filename to indicate processing
            output_filename = relative_path.stem.replace('acidity_bgc', 'acidity_harmonized') + '.nc'
            output_file = output_dir / relative_path.parent / output_filename
            
            try:
                success = self.process_file(input_file, output_file, surface_only)
                if success:
                    results['successful'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append(f"Failed to process {input_file}")
                    
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"Error processing {input_file}: {e}")
        
        self.logger.info(
            f"Batch acidity processing complete: {results['successful']} successful, "
            f"{results['failed']} failed out of {results['total_files']} files"
        )
        
        return results