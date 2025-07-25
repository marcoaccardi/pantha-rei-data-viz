#!/usr/bin/env python3
"""
Currents data processor for converting ocean currents data to unified coordinate system.
Processes velocity components (u, v) and derived quantities from CMEMS.
"""

import xarray as xr
import numpy as np
from pathlib import Path
from typing import Union, Optional, Dict, Any
import logging
from datetime import date
from .coordinate_harmonizer import CoordinateHarmonizer

class CurrentsProcessor:
    """Handles processing of ocean currents data."""
    
    def __init__(self):
        """Initialize currents processor."""
        self.logger = logging.getLogger(__name__)
        self.harmonizer = CoordinateHarmonizer()
    
    def validate_currents_data(self, ds: xr.Dataset) -> Dict[str, Any]:
        """
        Validate currents dataset for expected variables and ranges.
        
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
        
        # Expected variables for currents data
        expected_vars = {
            'uo': {'min': -5.0, 'max': 5.0, 'description': 'Eastward velocity (m/s)'},
            'vo': {'min': -5.0, 'max': 5.0, 'description': 'Northward velocity (m/s)'},
            'u': {'min': -5.0, 'max': 5.0, 'description': 'Eastward velocity (m/s)'},
            'v': {'min': -5.0, 'max': 5.0, 'description': 'Northward velocity (m/s)'},
            'thetao': {'min': -5.0, 'max': 50.0, 'description': 'Sea water potential temperature (°C)'},
            'so': {'min': 0.0, 'max': 50.0, 'description': 'Sea water salinity (PSU)'}
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
                
                # Validate ranges (with more lenient bounds for extreme conditions)
                extended_min = var_info['min'] * 2  # Allow 2x the expected range
                extended_max = var_info['max'] * 2
                
                if var_min < extended_min or var_max > extended_max:
                    validation['warnings'].append(
                        f"{var_info['description']} values ({var_min:.3f} - {var_max:.3f}) "
                        f"outside extended range ({extended_min} - {extended_max})"
                    )
        
        # Check if we have at least one velocity component
        velocity_vars = ['uo', 'vo', 'u', 'v']
        found_velocity_vars = [var for var in velocity_vars if var in validation['variables_found']]
        
        if not found_velocity_vars:
            validation['errors'].append(
                f"No velocity variables found. Expected one of: {velocity_vars}"
            )
            validation['valid'] = False
        
        # Check if we have both u and v components (preferred)
        u_vars = ['uo', 'u']
        v_vars = ['vo', 'v']
        has_u = any(var in validation['variables_found'] for var in u_vars)
        has_v = any(var in validation['variables_found'] for var in v_vars)
        
        if not (has_u and has_v):
            validation['warnings'].append(
                "Missing paired velocity components. Both u and v components recommended for complete current analysis."
            )
        
        # Validate coordinate system
        coord_validation = self.harmonizer.validate_geographic_bounds(ds)
        if not coord_validation['valid']:
            validation['errors'].extend(coord_validation['errors'])
            validation['valid'] = False
        
        validation['warnings'].extend(coord_validation['warnings'])
        
        return validation
    
    def select_surface_layer(self, ds: xr.Dataset, depth_threshold: float = 5.0) -> xr.Dataset:
        """
        Select surface layer data from 3D currents dataset.
        
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
    
    def calculate_derived_quantities(self, ds: xr.Dataset) -> xr.Dataset:
        """
        Calculate derived quantities from velocity components.
        
        Args:
            ds: Input dataset with velocity components
            
        Returns:
            Dataset with additional derived variables
        """
        ds_processed = ds.copy()
        
        # Determine velocity variable names
        u_var = None
        v_var = None
        
        if 'uo' in ds_processed.data_vars:
            u_var = 'uo'
        elif 'u' in ds_processed.data_vars:
            u_var = 'u'
            
        if 'vo' in ds_processed.data_vars:
            v_var = 'vo'
        elif 'v' in ds_processed.data_vars:
            v_var = 'v'
        
        # Calculate speed and direction if both components are available
        if u_var and v_var:
            u_data = ds_processed[u_var]
            v_data = ds_processed[v_var]
            
            # Current speed (magnitude)
            speed = np.sqrt(u_data**2 + v_data**2)
            speed.attrs = {
                'standard_name': 'sea_water_speed',
                'long_name': 'Current speed',
                'units': 'm s-1',
                'description': f'Current speed calculated from {u_var} and {v_var} components',
                'valid_range': [0.0, 10.0]
            }
            ds_processed['current_speed'] = speed
            
            # Current direction (0-360 degrees, oceanographic convention)
            # Oceanographic convention: direction toward which current flows
            direction = (np.arctan2(u_data, v_data) * 180.0 / np.pi) % 360
            direction.attrs = {
                'standard_name': 'direction_of_sea_water_velocity',
                'long_name': 'Current direction',
                'units': 'degrees',
                'description': 'Direction toward which current flows (oceanographic convention, 0=North, 90=East)',
                'valid_range': [0.0, 360.0],
                'convention': 'Oceanographic (direction TO which flow is directed)'
            }
            ds_processed['current_direction'] = direction
            
            self.logger.info("Calculated current speed and direction from velocity components")
        
        return ds_processed
    
    def process_currents_variables(self, ds: xr.Dataset) -> xr.Dataset:
        """
        Process and standardize currents variables.
        
        Args:
            ds: Input dataset with currents variables
            
        Returns:
            Dataset with processed variables
        """
        ds_processed = ds.copy()
        
        # Process eastward velocity (uo or u)
        for u_name in ['uo', 'u']:
            if u_name in ds_processed.data_vars:
                u_data = ds_processed[u_name]
                
                # Add standard attributes
                u_data.attrs.update({
                    'standard_name': 'eastward_sea_water_velocity',
                    'long_name': 'Eastward velocity',
                    'units': 'm s-1',
                    'valid_range': [-10.0, 10.0],
                    'description': 'Eastward component of sea water velocity'
                })
                
                # Quality control: mask extreme values
                u_masked = u_data.where((u_data >= -10.0) & (u_data <= 10.0))
                ds_processed[u_name] = u_masked
        
        # Process northward velocity (vo or v)
        for v_name in ['vo', 'v']:
            if v_name in ds_processed.data_vars:
                v_data = ds_processed[v_name]
                
                # Add standard attributes
                v_data.attrs.update({
                    'standard_name': 'northward_sea_water_velocity',
                    'long_name': 'Northward velocity',
                    'units': 'm s-1',
                    'valid_range': [-10.0, 10.0],
                    'description': 'Northward component of sea water velocity'
                })
                
                # Quality control: mask extreme values
                v_masked = v_data.where((v_data >= -10.0) & (v_data <= 10.0))
                ds_processed[v_name] = v_masked
        
        # Process temperature if present
        if 'thetao' in ds_processed.data_vars:
            temp_data = ds_processed['thetao']
            
            temp_data.attrs.update({
                'standard_name': 'sea_water_potential_temperature',
                'long_name': 'Sea water potential temperature',
                'units': 'degrees_C',
                'valid_range': [-5.0, 50.0],
                'description': 'Sea water potential temperature'
            })
            
            # Quality control: mask extreme values
            temp_masked = temp_data.where((temp_data >= -5.0) & (temp_data <= 50.0))
            ds_processed['thetao'] = temp_masked
        
        # Process salinity if present
        if 'so' in ds_processed.data_vars:
            sal_data = ds_processed['so']
            
            sal_data.attrs.update({
                'standard_name': 'sea_water_salinity',
                'long_name': 'Sea water salinity',
                'units': 'psu',
                'valid_range': [0.0, 50.0],
                'description': 'Sea water salinity'
            })
            
            # Quality control: mask negative values and extreme high values
            sal_masked = sal_data.where((sal_data >= 0.0) & (sal_data <= 50.0))
            ds_processed['so'] = sal_masked
        
        # Calculate derived quantities
        ds_processed = self.calculate_derived_quantities(ds_processed)
        
        # Add processing metadata
        ds_processed.attrs.update({
            'currents_processing_date': str(date.today()),
            'currents_processing_note': 'Quality controlled and standardized ocean currents variables'
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
        Complete processing pipeline for currents dataset.
        
        Args:
            ds: Input dataset
            surface_only: Whether to extract surface layer only
            
        Returns:
            Fully processed dataset
        """
        # Validate input data
        validation = self.validate_currents_data(ds)
        
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
        ds_processed = self.process_currents_variables(ds_processed)
        
        # Harmonize coordinates
        ds_processed = self.harmonize_to_unified_coords(ds_processed)
        
        # Add final processing metadata
        ds_processed.attrs.update({
            'processing_pipeline': 'currents_processor',
            'processing_version': '1.0',
            'variables_processed': str(validation['variables_found']),
            'unified_coordinate_system': 'latitude: -90 to 90, longitude: -180 to 180',
            'surface_only': str(surface_only)
        })
        
        return ds_processed
    
    def process_file(self, input_path: Union[str, Path], output_path: Union[str, Path],
                    surface_only: bool = True) -> bool:
        """
        Process a NetCDF file containing currents data.
        
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
                
                self.logger.info(f"Successfully processed currents data: {input_path} -> {output_path}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error processing currents file {input_path}: {e}")
            return False
    
    def batch_process_directory(self, input_dir: Union[str, Path], output_dir: Union[str, Path],
                               surface_only: bool = True, pattern: str = "*.nc") -> Dict[str, Any]:
        """
        Batch process all currents NetCDF files in a directory.
        
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
            output_filename = relative_path.stem.replace('currents_phy', 'currents_harmonized') + '.nc'
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
            f"Batch currents processing complete: {results['successful']} successful, "
            f"{results['failed']} failed out of {results['total_files']} files"
        )
        
        return results