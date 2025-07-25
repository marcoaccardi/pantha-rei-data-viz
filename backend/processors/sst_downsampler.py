#!/usr/bin/env python3
"""
SST downsampler for reducing spatial resolution of sea surface temperature data.
Downsamples from high resolution (e.g., 0.25°) to lower resolution (e.g., 1°) using spatial averaging.
"""

import xarray as xr
import numpy as np
from pathlib import Path
from typing import Union, Optional, Tuple
import logging
from datetime import date

class SSTDownsampler:
    """Handles spatial downsampling of SST data."""
    
    def __init__(self):
        """Initialize SST downsampler."""
        self.logger = logging.getLogger(__name__)
    
    def detect_resolution(self, ds: xr.Dataset) -> Tuple[float, float]:
        """
        Detect the spatial resolution of the dataset.
        
        Args:
            ds: Input xarray Dataset
            
        Returns:
            Tuple of (lat_resolution, lon_resolution) in degrees
        """
        # Get coordinate names
        lat_name = 'lat' if 'lat' in ds.dims else 'latitude'
        lon_name = 'lon' if 'lon' in ds.dims else 'longitude'
        
        if lat_name not in ds.dims or lon_name not in ds.dims:
            raise ValueError("Cannot find latitude and longitude coordinates")
        
        # Calculate resolution from coordinate spacing
        lat_res = abs(float(ds[lat_name].diff(lat_name).mean()))
        lon_res = abs(float(ds[lon_name].diff(lon_name).mean()))
        
        return lat_res, lon_res
    
    def calculate_coarsening_factors(self, current_resolution: float, target_resolution: float) -> int:
        """
        Calculate coarsening factor for spatial downsampling.
        
        Args:
            current_resolution: Current spatial resolution in degrees
            target_resolution: Target spatial resolution in degrees
            
        Returns:
            Integer coarsening factor
        """
        if target_resolution <= current_resolution:
            raise ValueError(f"Target resolution ({target_resolution}°) must be coarser than current resolution ({current_resolution}°)")
        
        # Calculate exact factor
        exact_factor = target_resolution / current_resolution
        
        # Round to nearest integer
        coarsening_factor = int(round(exact_factor))
        
        # Verify the factor makes sense
        resulting_resolution = current_resolution * coarsening_factor
        resolution_error = abs(resulting_resolution - target_resolution) / target_resolution
        
        if resolution_error > 0.1:  # More than 10% error
            self.logger.warning(
                f"Coarsening factor {coarsening_factor} results in {resulting_resolution:.3f}° "
                f"resolution, which differs from target {target_resolution}° by {resolution_error:.1%}"
            )
        
        return coarsening_factor
    
    def downsample_dataset(self, ds: xr.Dataset, target_lat_res: float, target_lon_res: float,
                          method: str = 'mean') -> xr.Dataset:
        """
        Downsample dataset to target resolution.
        
        Args:
            ds: Input xarray Dataset
            target_lat_res: Target latitude resolution in degrees
            target_lon_res: Target longitude resolution in degrees
            method: Downsampling method ('mean', 'median', 'max', 'min')
            
        Returns:
            Downsampled Dataset
        """
        # Detect current resolution
        current_lat_res, current_lon_res = self.detect_resolution(ds)
        
        self.logger.info(
            f"Downsampling from {current_lat_res:.3f}°×{current_lon_res:.3f}° "
            f"to {target_lat_res:.3f}°×{target_lon_res:.3f}°"
        )
        
        # Calculate coarsening factors
        lat_factor = self.calculate_coarsening_factors(current_lat_res, target_lat_res)
        lon_factor = self.calculate_coarsening_factors(current_lon_res, target_lon_res)
        
        self.logger.info(f"Using coarsening factors: lat={lat_factor}, lon={lon_factor}")
        
        # Get coordinate names
        lat_name = 'lat' if 'lat' in ds.dims else 'latitude'
        lon_name = 'lon' if 'lon' in ds.dims else 'longitude'
        
        # Perform coarsening
        coarsen_kwargs = {
            lat_name: lat_factor,
            lon_name: lon_factor,
            'boundary': 'trim'  # Drop incomplete edge cells
        }
        
        coarsened = ds.coarsen(**coarsen_kwargs)
        
        # Apply aggregation method
        if method == 'mean':
            ds_downsampled = coarsened.mean()
        elif method == 'median':
            ds_downsampled = coarsened.median()
        elif method == 'max':
            ds_downsampled = coarsened.max()
        elif method == 'min':
            ds_downsampled = coarsened.min()
        else:
            raise ValueError(f"Unknown downsampling method: {method}")
        
        # Update attributes
        original_shape = f"{len(ds[lat_name])}×{len(ds[lon_name])}"
        new_shape = f"{len(ds_downsampled[lat_name])}×{len(ds_downsampled[lon_name])}"
        
        ds_downsampled.attrs.update({
            'downsampling_method': method,
            'downsampling_date': str(date.today()),
            'original_resolution': f'{current_lat_res:.3f}°×{current_lon_res:.3f}°',
            'target_resolution': f'{target_lat_res:.3f}°×{target_lon_res:.3f}°',
            'actual_resolution': f'{target_lat_res * lat_factor:.3f}°×{target_lon_res * lon_factor:.3f}°',
            'coarsening_factors': f'lat={lat_factor}, lon={lon_factor}',
            'original_shape': original_shape,
            'downsampled_shape': new_shape,
            'data_reduction_factor': f'{len(ds[lat_name]) * len(ds[lon_name]) / (len(ds_downsampled[lat_name]) * len(ds_downsampled[lon_name])):.1f}x'
        })
        
        # Add processing notes to variables
        for var_name in ds_downsampled.data_vars:
            if var_name in ds.data_vars:
                ds_downsampled[var_name].attrs.update({
                    'downsampling_note': f'Spatially downsampled using {method} aggregation'
                })
        
        return ds_downsampled
    
    def downsample_sst_to_1degree(self, ds: xr.Dataset, method: str = 'mean') -> xr.Dataset:
        """
        Convenience method to downsample SST data to 1-degree resolution.
        
        Args:
            ds: Input xarray Dataset
            method: Downsampling method
            
        Returns:
            Dataset downsampled to 1-degree resolution
        """
        return self.downsample_dataset(ds, 1.0, 1.0, method)
    
    def validate_downsampling(self, original_ds: xr.Dataset, downsampled_ds: xr.Dataset) -> dict:
        """
        Validate that downsampling was performed correctly.
        
        Args:
            original_ds: Original high-resolution dataset
            downsampled_ds: Downsampled dataset
            
        Returns:
            Dictionary with validation results
        """
        validation = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'statistics': {}
        }
        
        # Get coordinate names
        lat_name = 'lat' if 'lat' in original_ds.dims else 'latitude'
        lon_name = 'lon' if 'lon' in original_ds.dims else 'longitude'
        
        # Check dimensions
        orig_lat_size = len(original_ds[lat_name])
        orig_lon_size = len(original_ds[lon_name])
        down_lat_size = len(downsampled_ds[lat_name])
        down_lon_size = len(downsampled_ds[lon_name])
        
        validation['statistics'] = {
            'original_shape': f"{orig_lat_size}×{orig_lon_size}",
            'downsampled_shape': f"{down_lat_size}×{down_lon_size}",
            'reduction_factor': f"{(orig_lat_size * orig_lon_size) / (down_lat_size * down_lon_size):.1f}x"
        }
        
        # Check that dimensions were reduced
        if down_lat_size >= orig_lat_size or down_lon_size >= orig_lon_size:
            validation['errors'].append("Downsampled dataset is not smaller than original")
            validation['valid'] = False
        
        # Check coordinate bounds
        orig_lat_bounds = (float(original_ds[lat_name].min()), float(original_ds[lat_name].max()))
        orig_lon_bounds = (float(original_ds[lon_name].min()), float(original_ds[lon_name].max()))
        down_lat_bounds = (float(downsampled_ds[lat_name].min()), float(downsampled_ds[lat_name].max()))
        down_lon_bounds = (float(downsampled_ds[lon_name].min()), float(downsampled_ds[lon_name].max()))
        
        # Allow some tolerance for coordinate bounds due to edge trimming
        lat_bound_tolerance = abs(orig_lat_bounds[1] - orig_lat_bounds[0]) * 0.05  # 5% tolerance
        lon_bound_tolerance = abs(orig_lon_bounds[1] - orig_lon_bounds[0]) * 0.05
        
        if (abs(down_lat_bounds[0] - orig_lat_bounds[0]) > lat_bound_tolerance or 
            abs(down_lat_bounds[1] - orig_lat_bounds[1]) > lat_bound_tolerance):
            validation['warnings'].append(
                f"Latitude bounds changed significantly: {orig_lat_bounds} -> {down_lat_bounds}"
            )
        
        if (abs(down_lon_bounds[0] - orig_lon_bounds[0]) > lon_bound_tolerance or 
            abs(down_lon_bounds[1] - orig_lon_bounds[1]) > lon_bound_tolerance):
            validation['warnings'].append(
                f"Longitude bounds changed significantly: {orig_lon_bounds} -> {down_lon_bounds}"
            )
        
        # Check data variables
        for var_name in original_ds.data_vars:
            if var_name not in downsampled_ds.data_vars:
                validation['warnings'].append(f"Variable '{var_name}' missing from downsampled dataset")
                continue
            
            # Check for reasonable value ranges (for SST)
            if var_name == 'sst':
                orig_sst_range = (float(original_ds[var_name].min()), float(original_ds[var_name].max()))
                down_sst_range = (float(downsampled_ds[var_name].min()), float(downsampled_ds[var_name].max()))
                
                # SST should be roughly in same range (-5 to 40°C typically)
                if (down_sst_range[0] < -10 or down_sst_range[1] > 50 or
                    abs(down_sst_range[0] - orig_sst_range[0]) > 5 or
                    abs(down_sst_range[1] - orig_sst_range[1]) > 5):
                    validation['warnings'].append(
                        f"SST value range changed significantly: {orig_sst_range} -> {down_sst_range}"
                    )
        
        return validation
    
    def process_file(self, input_path: Union[str, Path], output_path: Union[str, Path],
                    target_lat_res: float = 1.0, target_lon_res: float = 1.0,
                    method: str = 'mean') -> bool:
        """
        Process a NetCDF file to downsample SST data.
        
        Args:
            input_path: Path to input NetCDF file
            output_path: Path for output NetCDF file
            target_lat_res: Target latitude resolution in degrees
            target_lon_res: Target longitude resolution in degrees
            method: Downsampling method
            
        Returns:
            True if successful, False otherwise
        """
        try:
            input_path = Path(input_path)
            output_path = Path(output_path)
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Load dataset
            with xr.open_dataset(input_path) as ds:
                # Downsample
                ds_downsampled = self.downsample_dataset(ds, target_lat_res, target_lon_res, method)
                
                # Validate downsampling
                validation = self.validate_downsampling(ds, ds_downsampled)
                
                if not validation['valid']:
                    self.logger.error(f"Downsampling validation failed: {validation['errors']}")
                    return False
                
                if validation['warnings']:
                    for warning in validation['warnings']:
                        self.logger.warning(warning)
                
                # Save downsampled dataset
                ds_downsampled.to_netcdf(output_path, format='NETCDF4', engine='netcdf4')
                
                self.logger.info(f"Successfully downsampled {input_path} -> {output_path}")
                self.logger.info(f"Shape reduction: {validation['statistics']['reduction_factor']}")
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error processing file {input_path}: {e}")
            return False
    
    def batch_process_directory(self, input_dir: Union[str, Path], output_dir: Union[str, Path],
                               target_lat_res: float = 1.0, target_lon_res: float = 1.0,
                               method: str = 'mean', pattern: str = "*.nc") -> dict:
        """
        Batch process all NetCDF files in a directory.
        
        Args:
            input_dir: Directory containing input NetCDF files
            output_dir: Directory for output files
            target_lat_res: Target latitude resolution
            target_lon_res: Target longitude resolution
            method: Downsampling method
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
            output_file = output_dir / relative_path
            
            try:
                success = self.process_file(input_file, output_file, target_lat_res, target_lon_res, method)
                if success:
                    results['successful'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append(f"Failed to process {input_file}")
                    
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"Error processing {input_file}: {e}")
        
        self.logger.info(
            f"Batch processing complete: {results['successful']} successful, "
            f"{results['failed']} failed out of {results['total_files']} files"
        )
        
        return results