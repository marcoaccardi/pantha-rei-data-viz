#!/usr/bin/env python3
"""
Coordinate system harmonizer for ocean data.
Converts between different longitude conventions (0-360° vs -180-180°).
"""

import xarray as xr
import numpy as np
from pathlib import Path
from typing import Union, Tuple
import logging

class CoordinateHarmonizer:
    """Handles coordinate system conversions for ocean datasets."""
    
    def __init__(self):
        """Initialize coordinate harmonizer."""
        self.logger = logging.getLogger(__name__)
    
    def detect_longitude_convention(self, ds: xr.Dataset) -> str:
        """
        Detect the longitude convention used in dataset.
        
        Args:
            ds: Input xarray Dataset
            
        Returns:
            '0-360' or '-180-180' or 'mixed' or 'unknown'
        """
        if 'lon' not in ds.dims and 'longitude' not in ds.dims:
            return 'unknown'
        
        # Get longitude coordinate
        lon_coord = ds.lon if 'lon' in ds.dims else ds.longitude
        
        lon_min, lon_max = float(lon_coord.min()), float(lon_coord.max())
        
        # Determine convention
        if lon_min >= 0 and lon_max <= 360:
            if lon_max > 180:
                return '0-360'
            else:
                return 'ambiguous'  # Could be either, but likely -180-180
        elif lon_min >= -180 and lon_max <= 180:
            return '-180-180'
        else:
            return 'mixed'
    
    def convert_to_180_180(self, ds: xr.Dataset) -> xr.Dataset:
        """
        Convert longitude coordinates from 0-360° to -180-180°.
        
        Args:
            ds: Input xarray Dataset
            
        Returns:
            Dataset with converted coordinates
        """
        # Determine longitude coordinate name
        lon_name = 'lon' if 'lon' in ds.dims else 'longitude'
        
        if lon_name not in ds.dims:
            raise ValueError("No longitude coordinate found in dataset")
        
        current_convention = self.detect_longitude_convention(ds)
        
        if current_convention == '-180-180':
            self.logger.info("Dataset already uses -180-180° longitude convention")
            return ds
        elif current_convention == '0-360':
            self.logger.info("Converting longitude from 0-360° to -180-180°")
            
            # Create a copy to avoid modifying original
            ds_converted = ds.copy()
            
            # Convert longitude coordinates
            ds_converted = ds_converted.assign_coords({
                lon_name: (ds_converted[lon_name] + 180) % 360 - 180
            })
            
            # Sort by longitude to maintain proper ordering
            ds_converted = ds_converted.sortby(lon_name)
            
            # Add metadata about conversion
            ds_converted.attrs.update({
                'longitude_conversion': 'Converted from 0-360° to -180-180°',
                'longitude_conversion_date': str(np.datetime64('today')),
                'original_longitude_range': f"{float(ds[lon_name].min()):.3f} to {float(ds[lon_name].max()):.3f}",
                'converted_longitude_range': f"{float(ds_converted[lon_name].min()):.3f} to {float(ds_converted[lon_name].max()):.3f}"
            })
            
            return ds_converted
        else:
            raise ValueError(f"Cannot convert from {current_convention} longitude convention")
    
    def convert_to_0_360(self, ds: xr.Dataset) -> xr.Dataset:
        """
        Convert longitude coordinates from -180-180° to 0-360°.
        
        Args:
            ds: Input xarray Dataset
            
        Returns:
            Dataset with converted coordinates
        """
        # Determine longitude coordinate name
        lon_name = 'lon' if 'lon' in ds.dims else 'longitude'
        
        if lon_name not in ds.dims:
            raise ValueError("No longitude coordinate found in dataset")
        
        current_convention = self.detect_longitude_convention(ds)
        
        if current_convention == '0-360':
            self.logger.info("Dataset already uses 0-360° longitude convention")
            return ds
        elif current_convention == '-180-180':
            self.logger.info("Converting longitude from -180-180° to 0-360°")
            
            # Create a copy to avoid modifying original
            ds_converted = ds.copy()
            
            # Convert longitude coordinates
            ds_converted = ds_converted.assign_coords({
                lon_name: ds_converted[lon_name] % 360
            })
            
            # Sort by longitude to maintain proper ordering
            ds_converted = ds_converted.sortby(lon_name)
            
            # Add metadata about conversion
            ds_converted.attrs.update({
                'longitude_conversion': 'Converted from -180-180° to 0-360°',
                'longitude_conversion_date': str(np.datetime64('today')),
                'original_longitude_range': f"{float(ds[lon_name].min()):.3f} to {float(ds[lon_name].max()):.3f}",
                'converted_longitude_range': f"{float(ds_converted[lon_name].min()):.3f} to {float(ds_converted[lon_name].max()):.3f}"
            })
            
            return ds_converted
        else:
            raise ValueError(f"Cannot convert from {current_convention} longitude convention")
    
    def harmonize_dataset(self, ds: xr.Dataset, target_convention: str = '-180-180') -> xr.Dataset:
        """
        Harmonize dataset to target longitude convention.
        
        Args:
            ds: Input xarray Dataset
            target_convention: Target convention ('0-360' or '-180-180')
            
        Returns:
            Dataset with harmonized coordinates
        """
        if target_convention == '-180-180':
            return self.convert_to_180_180(ds)
        elif target_convention == '0-360':
            return self.convert_to_0_360(ds)
        else:
            raise ValueError(f"Unknown target convention: {target_convention}")
    
    def get_coordinate_info(self, ds: xr.Dataset) -> dict:
        """
        Get detailed information about dataset coordinates.
        
        Args:
            ds: Input xarray Dataset
            
        Returns:
            Dictionary with coordinate information
        """
        info = {
            'dimensions': list(ds.dims.keys()),
            'coordinates': list(ds.coords.keys()),
            'longitude_info': {},
            'latitude_info': {}
        }
        
        # Longitude information
        if 'lon' in ds.dims:
            lon_coord = ds.lon
            lon_name = 'lon'
        elif 'longitude' in ds.dims:
            lon_coord = ds.longitude
            lon_name = 'longitude'
        else:
            lon_coord = None
            lon_name = None
        
        if lon_coord is not None:
            info['longitude_info'] = {
                'name': lon_name,
                'size': len(lon_coord),
                'min': float(lon_coord.min()),
                'max': float(lon_coord.max()),
                'resolution': float(lon_coord.diff(lon_name).mean()) if len(lon_coord) > 1 else None,
                'convention': self.detect_longitude_convention(ds),
                'units': lon_coord.attrs.get('units', 'unknown')
            }
        
        # Latitude information
        if 'lat' in ds.dims:
            lat_coord = ds.lat
            lat_name = 'lat'
        elif 'latitude' in ds.dims:
            lat_coord = ds.latitude
            lat_name = 'latitude'
        else:
            lat_coord = None
            lat_name = None
        
        if lat_coord is not None:
            info['latitude_info'] = {
                'name': lat_name,
                'size': len(lat_coord),
                'min': float(lat_coord.min()),
                'max': float(lat_coord.max()),
                'resolution': abs(float(lat_coord.diff(lat_name).mean())) if len(lat_coord) > 1 else None,
                'units': lat_coord.attrs.get('units', 'unknown')
            }
        
        return info
    
    def validate_geographic_bounds(self, ds: xr.Dataset) -> dict:
        """
        Validate that coordinates are within expected geographic bounds.
        
        Args:
            ds: Input xarray Dataset
            
        Returns:
            Dictionary with validation results
        """
        validation = {
            'valid': True,
            'warnings': [],
            'errors': []
        }
        
        coord_info = self.get_coordinate_info(ds)
        
        # Validate longitude
        if coord_info['longitude_info']:
            lon_info = coord_info['longitude_info']
            lon_min, lon_max = lon_info['min'], lon_info['max']
            
            if lon_info['convention'] == '0-360':
                if lon_min < 0 or lon_max > 360:
                    validation['errors'].append(f"Longitude values {lon_min}-{lon_max} outside 0-360° range")
                    validation['valid'] = False
            elif lon_info['convention'] == '-180-180':
                if lon_min < -180 or lon_max > 180:
                    validation['errors'].append(f"Longitude values {lon_min}-{lon_max} outside -180-180° range")
                    validation['valid'] = False
        
        # Validate latitude
        if coord_info['latitude_info']:
            lat_info = coord_info['latitude_info']
            lat_min, lat_max = lat_info['min'], lat_info['max']
            
            if lat_min < -90 or lat_max > 90:
                validation['errors'].append(f"Latitude values {lat_min}-{lat_max} outside -90-90° range")
                validation['valid'] = False
            
            # Check for reasonable resolution
            if lat_info['resolution'] and lat_info['resolution'] > 5.0:
                validation['warnings'].append(f"Large latitude resolution: {lat_info['resolution']:.2f}°")
        
        return validation
    
    def process_file(self, input_path: Union[str, Path], output_path: Union[str, Path], 
                    target_convention: str = '-180-180') -> bool:
        """
        Process a NetCDF file to harmonize coordinates.
        
        Args:
            input_path: Path to input NetCDF file
            output_path: Path for output NetCDF file
            target_convention: Target longitude convention
            
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
                # Validate input
                validation = self.validate_geographic_bounds(ds)
                if not validation['valid']:
                    self.logger.error(f"Input validation failed: {validation['errors']}")
                    return False
                
                # Harmonize coordinates
                ds_harmonized = self.harmonize_dataset(ds, target_convention)
                
                # Save to output file
                ds_harmonized.to_netcdf(output_path, format='NETCDF4', engine='netcdf4')
                
                self.logger.info(f"Successfully processed {input_path} -> {output_path}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error processing file {input_path}: {e}")
            return False