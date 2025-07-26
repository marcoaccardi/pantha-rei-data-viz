#!/usr/bin/env python3
"""
Waves data processor for converting ocean waves data to unified coordinate system.
Processes wave height (VHM0), direction (MWD), and period (PP1D) from CMEMS.
Includes proper land masking to ensure waves data only exists in ocean areas.
"""

import xarray as xr
import numpy as np
from pathlib import Path
from typing import Union, Optional, Dict, Any
import logging
from datetime import date
from .coordinate_harmonizer import CoordinateHarmonizer

class WavesProcessor:
    """Handles processing of ocean waves data with proper land masking."""
    
    def __init__(self):
        """Initialize waves processor."""
        self.logger = logging.getLogger(__name__)
        self.harmonizer = CoordinateHarmonizer()
    
    def validate_waves_data(self, ds: xr.Dataset) -> Dict[str, Any]:
        """
        Validate waves dataset for expected variables and ranges.
        
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
        
        # Expected variables for waves data
        expected_vars = {
            'VHM0': {'min': 0.0, 'max': 15.0, 'description': 'Significant wave height (m)'},
            'MWD': {'min': 0.0, 'max': 360.0, 'description': 'Mean wave direction (degrees)'},
            'PP1D': {'min': 0.0, 'max': 30.0, 'description': 'Peak wave period (s)'},
            'VMDR': {'min': 0.0, 'max': 360.0, 'description': 'Mean wave direction (degrees)'},
            'VTM10': {'min': 0.0, 'max': 30.0, 'description': 'Mean wave period (s)'}
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
                
                # Validate ranges (with extended bounds for extreme conditions)
                extended_max = var_info['max'] * 1.5  # Allow 1.5x for extreme weather
                
                if var_min < var_info['min']:
                    validation['warnings'].append(
                        f"{var_info['description']} has negative values ({var_min:.3f}), "
                        "which may indicate land areas or data issues"
                    )
                
                if var_max > extended_max:
                    validation['warnings'].append(
                        f"{var_info['description']} values ({var_max:.3f}) "
                        f"exceed extended maximum ({extended_max})"
                    )
        
        # Check if we have wave height (most important variable)
        if 'VHM0' not in validation['variables_found']:
            validation['errors'].append(
                "No VHM0 (significant wave height) variable found. This is required for waves processing."
            )
            validation['valid'] = False
        
        # Validate coordinate system
        coord_validation = self.harmonizer.validate_geographic_bounds(ds)
        if not coord_validation['valid']:
            validation['errors'].extend(coord_validation['errors'])
            validation['valid'] = False
        
        validation['warnings'].extend(coord_validation['warnings'])
        
        return validation
    
    def create_ocean_mask(self, lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
        """
        Create ocean mask using SST reference data as template for realistic land/ocean boundaries.
        This ensures wave land masking matches proven geographic accuracy of SST data.
        
        Args:
            lon: Longitude array (-180 to 180)
            lat: Latitude array (-90 to 90)
            
        Returns:
            Boolean mask (True for ocean, False for land)
        """
        try:
            # Use SST data as land mask template for geographic accuracy
            sst_reference_path = Path("/Volumes/Backup/panta-rhei-data-map/ocean-data/processed/unified_coords/sst/2024/07/sst_harmonized_20240724.nc")
            
            if sst_reference_path.exists():
                return self._create_sst_based_ocean_mask(lon, lat, sst_reference_path)
            else:
                # Fallback to improved simplified masking if SST not available
                self.logger.warning("SST reference not found, using fallback ocean masking")
                return self._create_fallback_ocean_mask(lon, lat)
                
        except Exception as e:
            self.logger.error(f"Error creating ocean mask: {e}")
            # Ultimate fallback - minimal masking to preserve ocean areas
            return self._create_minimal_ocean_mask(lon, lat)
    
    def _create_sst_based_ocean_mask(self, lon: np.ndarray, lat: np.ndarray, sst_path: Path) -> np.ndarray:
        """Create ocean mask based on SST reference data."""
        import xarray as xr
        from scipy.interpolate import RegularGridInterpolator
        
        with xr.open_dataset(sst_path) as sst_ds:
            # Get SST data and coordinates
            sst_data = sst_ds.sst.values
            if sst_data.ndim > 2:
                sst_data = np.squeeze(sst_data)
            
            sst_lat = sst_ds.lat.values if 'lat' in sst_ds.coords else sst_ds.latitude.values
            sst_lon = sst_ds.lon.values if 'lon' in sst_ds.coords else sst_ds.longitude.values
            
            # Create SST-based ocean mask (True where SST data is valid/non-NaN)
            sst_ocean_mask = ~np.isnan(sst_data)
            
            # Interpolate SST ocean mask to wave coordinate grid
            # Create interpolator for the mask
            mask_interpolator = RegularGridInterpolator(
                (sst_lat, sst_lon), 
                sst_ocean_mask.astype(float),  # Convert bool to float for interpolation
                method='nearest',  # Use nearest neighbor to preserve sharp land/ocean boundaries
                bounds_error=False,
                fill_value=0.0  # Default to land for areas outside SST coverage
            )
            
            # Create wave coordinate grids
            wave_lon_grid, wave_lat_grid = np.meshgrid(lon, lat)
            
            # Create interpolation points
            wave_points = np.column_stack([
                wave_lat_grid.ravel(),
                wave_lon_grid.ravel()
            ])
            
            # Interpolate SST mask to wave grid
            interpolated_mask = mask_interpolator(wave_points)
            wave_ocean_mask = interpolated_mask.reshape(wave_lat_grid.shape) > 0.5
            
            # Log masking statistics
            ocean_points = np.sum(wave_ocean_mask)
            total_points = wave_ocean_mask.size  
            ocean_pct = (ocean_points / total_points) * 100
            
            self.logger.info(f"SST-based ocean mask: {ocean_points}/{total_points} ocean points ({ocean_pct:.1f}%)")
            
            return wave_ocean_mask
    
    def _create_fallback_ocean_mask(self, lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
        """Improved fallback ocean mask with better ocean preservation."""
        lon_grid, lat_grid = np.meshgrid(lon, lat)
        
        # Start with all ocean
        ocean_mask = np.ones_like(lon_grid, dtype=bool)
        
        # Use only major continental cores (much smaller regions to preserve ocean)
        major_land_cores = [
            # North America core (smaller)
            (-130, -70, 25, 70),
            # South America core (smaller)  
            (-75, -45, -30, 10),
            # Europe core (smaller)
            (0, 40, 45, 70),
            # Africa core (smaller)
            (10, 40, -20, 25),
            # Asia core (smaller)
            (70, 140, 20, 60),
            # Australia core (smaller)
            (130, 150, -35, -15),
            # Antarctica (reduced)
            (-180, 180, -90, -70),
        ]
        
        # Apply conservative land masking (only major land cores)
        for lon_min, lon_max, lat_min, lat_max in major_land_cores:
            mask = ((lon_grid >= lon_min) & (lon_grid <= lon_max) & 
                   (lat_grid >= lat_min) & (lat_grid <= lat_max))
            ocean_mask[mask] = False
        
        # Explicitly preserve major ocean basins
        # Atlantic Ocean
        atlantic = ((lon_grid >= -70) & (lon_grid <= 0) & 
                   (lat_grid >= -60) & (lat_grid <= 70))
        ocean_mask[atlantic] = True
        
        # Pacific Ocean
        pacific_west = ((lon_grid >= 120) & (lon_grid <= 180) & 
                       (lat_grid >= -60) & (lat_grid <= 70))
        pacific_east = ((lon_grid >= -180) & (lon_grid <= -120) & 
                       (lat_grid >= -60) & (lat_grid <= 70))
        ocean_mask[pacific_west] = True
        ocean_mask[pacific_east] = True
        
        # Indian Ocean
        indian = ((lon_grid >= 40) & (lon_grid <= 120) & 
                 (lat_grid >= -60) & (lat_grid <= 30))
        ocean_mask[indian] = True
        
        return ocean_mask
    
    def _create_minimal_ocean_mask(self, lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
        """Minimal masking - preserve maximum ocean area."""
        lon_grid, lat_grid = np.meshgrid(lon, lat)
        
        # Start with all ocean
        ocean_mask = np.ones_like(lon_grid, dtype=bool)
        
        # Mask only the most obvious large landmasses (very conservative)
        # North America (core only)
        north_america = ((lon_grid >= -110) & (lon_grid <= -80) & 
                        (lat_grid >= 35) & (lat_grid <= 55))
        ocean_mask[north_america] = False
        
        # Eurasia (core only)
        eurasia = ((lon_grid >= 20) & (lon_grid <= 120) & 
                  (lat_grid >= 45) & (lat_grid <= 65))
        ocean_mask[eurasia] = False
        
        # Antarctica (reduced)
        antarctica = (lat_grid <= -75)
        ocean_mask[antarctica] = False
        
        return ocean_mask
    
    def apply_land_masking(self, ds: xr.Dataset) -> xr.Dataset:
        """
        Apply land masking to waves dataset by setting land areas to NaN.
        
        Args:
            ds: Input dataset with waves variables
            
        Returns:
            Dataset with land areas masked as NaN
        """
        ds_masked = ds.copy()
        
        # Get coordinate arrays
        lat = ds.latitude.values if 'latitude' in ds.coords else ds.lat.values
        lon = ds.longitude.values if 'longitude' in ds.coords else ds.lon.values
        
        # Create ocean mask
        ocean_mask = self.create_ocean_mask(lon, lat)
        
        # Variables to mask (all wave-related variables)
        wave_vars = ['VHM0', 'MWD', 'PP1D', 'VMDR', 'VTM10']
        
        masked_count = 0
        for var_name in wave_vars:
            if var_name in ds_masked.data_vars:
                # Apply ocean mask (set land areas to NaN)
                var_data = ds_masked[var_name].values
                
                # Ensure consistent dimensions
                if var_data.ndim == 2:
                    var_data_masked = np.where(ocean_mask, var_data, np.nan)
                elif var_data.ndim == 3:  # Has time dimension
                    var_data_masked = np.where(ocean_mask[None, :, :], var_data, np.nan)
                else:
                    self.logger.warning(f"Unexpected dimensions for {var_name}: {var_data.shape}")
                    continue
                
                # Update the dataset
                ds_masked[var_name] = (ds_masked[var_name].dims, var_data_masked, ds_masked[var_name].attrs)
                
                # Count masked values
                land_points = np.sum(~ocean_mask)
                self.logger.info(f"Masked {land_points} land points for {var_name}")
                masked_count += 1
        
        # Add masking metadata
        total_ocean_points = np.sum(ocean_mask)
        total_land_points = np.sum(~ocean_mask)
        
        ds_masked.attrs.update({
            'land_masking_applied': 'true',  # Use string instead of boolean for NetCDF compatibility
            'land_masking_date': str(date.today()),
            'ocean_points': int(total_ocean_points),
            'land_points_masked': int(total_land_points),
            'variables_masked': int(masked_count),
            'masking_method': 'Continental boundary approximation'
        })
        
        self.logger.info(f"Applied land masking: {total_ocean_points} ocean points, {total_land_points} land points masked")
        
        return ds_masked
    
    def process_waves_variables(self, ds: xr.Dataset) -> xr.Dataset:
        """
        Process and standardize waves variables.
        
        Args:
            ds: Input dataset with waves variables
            
        Returns:
            Dataset with processed variables
        """
        ds_processed = ds.copy()
        
        # Process significant wave height (VHM0)
        if 'VHM0' in ds_processed.data_vars:
            vhm0_data = ds_processed['VHM0']
            
            # Add standard attributes
            vhm0_data.attrs.update({
                'standard_name': 'sea_surface_wave_significant_height',
                'long_name': 'Spectral significant wave height (Hm0)',
                'units': 'm',
                'valid_range': [0.0, 15.0],
                'description': 'Significant wave height of wind waves and swell'
            })
            
            # Quality control: mask negative values and extreme values
            vhm0_masked = vhm0_data.where((vhm0_data >= 0.0) & (vhm0_data <= 20.0))
            ds_processed['VHM0'] = vhm0_masked
        
        # Process mean wave direction (MWD)
        if 'MWD' in ds_processed.data_vars:
            mwd_data = ds_processed['MWD']
            
            mwd_data.attrs.update({
                'standard_name': 'sea_surface_wave_from_direction',
                'long_name': 'Mean wave direction from (nautical convention)',
                'units': 'degrees',
                'valid_range': [0.0, 360.0],
                'description': 'Mean direction from which waves are coming (nautical convention)'
            })
            
            # Quality control: ensure values are within 0-360 range
            mwd_masked = mwd_data.where((mwd_data >= 0.0) & (mwd_data <= 360.0))
            ds_processed['MWD'] = mwd_masked
        
        # Process peak wave period (PP1D)
        if 'PP1D' in ds_processed.data_vars:
            pp1d_data = ds_processed['PP1D']
            
            pp1d_data.attrs.update({
                'standard_name': 'sea_surface_wave_period_at_variance_spectral_density_maximum',
                'long_name': 'Peak wave period',
                'units': 's',
                'valid_range': [0.0, 30.0],
                'description': 'Wave period at the peak of the variance density spectrum'
            })
            
            # Quality control: mask negative values and extreme values
            pp1d_masked = pp1d_data.where((pp1d_data >= 0.0) & (pp1d_data <= 40.0))
            ds_processed['PP1D'] = pp1d_masked
        
        # Process alternative wave direction (VMDR) if present
        if 'VMDR' in ds_processed.data_vars:
            vmdr_data = ds_processed['VMDR']
            
            vmdr_data.attrs.update({
                'standard_name': 'sea_surface_wave_from_direction',
                'long_name': 'Mean wave direction from',
                'units': 'degrees',
                'valid_range': [0.0, 360.0],
                'description': 'Mean direction from which waves are coming'
            })
            
            vmdr_masked = vmdr_data.where((vmdr_data >= 0.0) & (vmdr_data <= 360.0))
            ds_processed['VMDR'] = vmdr_masked
        
        # Process alternative wave period (VTM10) if present
        if 'VTM10' in ds_processed.data_vars:
            vtm10_data = ds_processed['VTM10']
            
            vtm10_data.attrs.update({
                'standard_name': 'sea_surface_wave_mean_period',
                'long_name': 'Mean wave period',
                'units': 's',
                'valid_range': [0.0, 30.0],
                'description': 'Mean wave period (T_m-1,0)'
            })
            
            vtm10_masked = vtm10_data.where((vtm10_data >= 0.0) & (vtm10_data <= 40.0))
            ds_processed['VTM10'] = vtm10_masked
        
        # Add processing metadata
        ds_processed.attrs.update({
            'waves_processing_date': str(date.today()),
            'waves_processing_note': 'Quality controlled and standardized ocean waves variables with land masking'
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
    
    def process_dataset(self, ds: xr.Dataset) -> xr.Dataset:
        """
        Complete processing pipeline for waves dataset.
        
        Args:
            ds: Input dataset
            
        Returns:
            Fully processed dataset with land masking
        """
        # Validate input data
        validation = self.validate_waves_data(ds)
        
        if not validation['valid']:
            raise ValueError(f"Input validation failed: {validation['errors']}")
        
        # Log warnings
        for warning in validation['warnings']:
            self.logger.warning(warning)
        
        # Process variables first
        ds_processed = self.process_waves_variables(ds)
        
        # Harmonize coordinates
        ds_processed = self.harmonize_to_unified_coords(ds_processed)
        
        # Apply land masking (CRITICAL for waves data)
        ds_processed = self.apply_land_masking(ds_processed)
        
        # Add final processing metadata
        ds_processed.attrs.update({
            'processing_pipeline': 'waves_processor',
            'processing_version': '1.0',
            'variables_processed': str(validation['variables_found']),
            'unified_coordinate_system': 'latitude: -90 to 90, longitude: -180 to 180',
            'land_masking': 'Applied - land areas set to NaN for proper texture generation'
        })
        
        return ds_processed
    
    def process_file(self, input_path: Union[str, Path], output_path: Union[str, Path]) -> bool:
        """
        Process a NetCDF file containing waves data.
        
        Args:
            input_path: Path to input NetCDF file
            output_path: Path for output NetCDF file
            
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
                ds_processed = self.process_dataset(ds)
                
                # Save processed dataset
                ds_processed.to_netcdf(output_path, format='NETCDF4', engine='netcdf4')
                
                self.logger.info(f"Successfully processed waves data: {input_path} -> {output_path}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error processing waves file {input_path}: {e}")
            return False
    
    def batch_process_directory(self, input_dir: Union[str, Path], output_dir: Union[str, Path],
                               pattern: str = "*.nc") -> Dict[str, Any]:
        """
        Batch process all waves NetCDF files in a directory.
        
        Args:
            input_dir: Directory containing input NetCDF files
            output_dir: Directory for output files
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
            output_filename = relative_path.stem.replace('waves_global', 'waves_processed') + '.nc'
            output_file = output_dir / relative_path.parent / output_filename
            
            try:
                success = self.process_file(input_file, output_file)
                if success:
                    results['successful'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append(f"Failed to process {input_file}")
                    
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"Error processing {input_file}: {e}")
        
        self.logger.info(
            f"Batch waves processing complete: {results['successful']} successful, "
            f"{results['failed']} failed out of {results['total_files']} files"
        )
        
        return results