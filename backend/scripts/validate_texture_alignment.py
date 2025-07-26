#!/usr/bin/env python3
"""
Texture Coordinate Alignment Validation Script

This script validates that all generated textures have consistent coordinate systems
and alignment across different datasets. It helps prevent coordinate alignment issues
that can cause visual misalignment in the 3D globe visualization.

Usage:
    python scripts/validate_texture_alignment.py
"""

import sys
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Any
import logging

# Add backend to Python path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from processors.dataset_texture_generators import (
    SSTTextureGenerator, 
    AcidityTextureGenerator, 
    CurrentsTextureGenerator
)

class TextureAlignmentValidator:
    """Validates coordinate alignment across all texture generators."""
    
    def __init__(self):
        """Initialize validator."""
        self.logger = logging.getLogger(__name__)
        self.expected_coordinate_ranges = {
            'lat_min': -89.958,
            'lat_max': 89.958,
            'lon_min': -179.958,
            'lon_max': 179.958
        }
        self.expected_texture_shape = (2041, 4320, 4)  # (height, width, RGBA)
        self.tolerance = 0.1  # Coordinate tolerance in degrees
        
    def validate_texture_coordinates(self, texture_generator, sample_file: Path) -> Dict[str, Any]:
        """
        Validate coordinate system for a specific texture generator.
        
        Args:
            texture_generator: Instance of texture generator
            sample_file: Sample NetCDF file to test
            
        Returns:
            Validation results dictionary
        """
        validation_results = {
            'dataset': texture_generator.dataset_name,
            'file': str(sample_file),
            'success': False,
            'coordinate_validation': {},
            'texture_validation': {},
            'errors': []
        }
        
        try:
            if not sample_file.exists():
                validation_results['errors'].append(f"Sample file not found: {sample_file}")
                return validation_results
            
            # Temporarily capture texture generation validation output
            original_process = texture_generator.process_netcdf_to_texture
            captured_validation = {}
            
            def capture_validation(self, data, lon, lat, texture):
                """Capture validation results for analysis."""
                captured_validation.update({
                    'data_shape': data.shape,
                    'coord_arrays_len': (len(lat), len(lon)),
                    'texture_shape': texture.shape,
                    'lat_range': (float(lat.min()), float(lat.max())),
                    'lon_range': (float(lon.min()), float(lon.max())),
                    'lat_increasing': bool(np.all(np.diff(lat) > 0)),
                    'lon_increasing': bool(np.all(np.diff(lon) > 0))
                })
            
            # Temporarily replace validation method
            texture_generator._validate_texture_alignment = capture_validation.__get__(texture_generator)
            
            # Generate texture and capture validation
            success = texture_generator.process_netcdf_to_texture(sample_file)
            
            # Restore original method
            texture_generator._validate_texture_alignment = original_process
            
            validation_results['success'] = success
            
            if success and captured_validation:
                # Validate coordinate ranges
                lat_min, lat_max = captured_validation['lat_range']
                lon_min, lon_max = captured_validation['lon_range']
                
                lat_range_ok = (abs(lat_min - self.expected_coordinate_ranges['lat_min']) < self.tolerance and
                               abs(lat_max - self.expected_coordinate_ranges['lat_max']) < self.tolerance)
                lon_range_ok = (abs(lon_min - self.expected_coordinate_ranges['lon_min']) < self.tolerance and
                               abs(lon_max - self.expected_coordinate_ranges['lon_max']) < self.tolerance)
                
                validation_results['coordinate_validation'] = {
                    'lat_range': (lat_min, lat_max),
                    'lon_range': (lon_min, lon_max),
                    'lat_range_ok': lat_range_ok,
                    'lon_range_ok': lon_range_ok,
                    'lat_increasing': captured_validation['lat_increasing'],
                    'lon_increasing': captured_validation['lon_increasing'],
                    'coord_ordering_ok': captured_validation['lat_increasing'] and captured_validation['lon_increasing']
                }
                
                # Validate texture dimensions
                texture_shape = captured_validation['texture_shape']
                texture_shape_ok = texture_shape == self.expected_texture_shape
                
                validation_results['texture_validation'] = {
                    'texture_shape': texture_shape,
                    'expected_shape': self.expected_texture_shape,
                    'shape_ok': texture_shape_ok,
                    'data_coord_match': (captured_validation['data_shape'] == 
                                       (captured_validation['coord_arrays_len'][0], captured_validation['coord_arrays_len'][1]))
                }
                
                # Overall validation status
                all_checks_pass = (lat_range_ok and lon_range_ok and texture_shape_ok and 
                                 captured_validation['lat_increasing'] and captured_validation['lon_increasing'])
                validation_results['all_checks_pass'] = all_checks_pass
                
                if not all_checks_pass:
                    if not lat_range_ok:
                        validation_results['errors'].append(f"Latitude range mismatch: {lat_min:.3f}-{lat_max:.3f}")
                    if not lon_range_ok:
                        validation_results['errors'].append(f"Longitude range mismatch: {lon_min:.3f}-{lon_max:.3f}")
                    if not texture_shape_ok:
                        validation_results['errors'].append(f"Texture shape mismatch: {texture_shape}")
                    if not captured_validation['lat_increasing']:
                        validation_results['errors'].append("Latitude coordinates not properly ordered")
                    if not captured_validation['lon_increasing']:
                        validation_results['errors'].append("Longitude coordinates not properly ordered")
            else:
                validation_results['errors'].append("Texture generation failed or no validation data captured")
                
        except Exception as e:
            validation_results['errors'].append(f"Validation error: {str(e)}")
            
        return validation_results
    
    def run_full_validation(self) -> Dict[str, Any]:
        """
        Run complete validation across all texture generators.
        
        Returns:
            Complete validation results
        """
        results = {
            'validation_timestamp': str(np.datetime64('now')),
            'expected_coordinates': self.expected_coordinate_ranges,
            'expected_texture_shape': self.expected_texture_shape,
            'datasets': {},
            'overall_success': False,
            'summary': {}
        }
        
        # Define test cases
        test_cases = [
            (SSTTextureGenerator(), Path("/Volumes/Backup/panta-rhei-data-map/ocean-data/processed/unified_coords/sst/2024/01/sst_harmonized_20240115.nc")),
            (AcidityTextureGenerator(), Path("/Volumes/Backup/panta-rhei-data-map/ocean-data/processed/unified_coords/acidity/2024/01/acidity_harmonized_20240106.nc")),
            (CurrentsTextureGenerator(), Path("/Volumes/Backup/panta-rhei-data-map/ocean-data/processed/unified_coords/currents/2024/07/currents_harmonized_20240725.nc"))
        ]
        
        successful_datasets = []
        failed_datasets = []
        
        for generator, sample_file in test_cases:
            dataset_name = generator.dataset_name
            self.logger.info(f"Validating {dataset_name} texture generation...")
            
            validation_result = self.validate_texture_coordinates(generator, sample_file)
            results['datasets'][dataset_name] = validation_result
            
            if validation_result.get('all_checks_pass', False):
                successful_datasets.append(dataset_name)
                self.logger.info(f"✅ {dataset_name} validation PASSED")
            else:
                failed_datasets.append(dataset_name)
                self.logger.error(f"❌ {dataset_name} validation FAILED: {validation_result.get('errors', [])}")
        
        # Overall results
        results['overall_success'] = len(failed_datasets) == 0
        results['summary'] = {
            'total_datasets': len(test_cases),
            'successful': len(successful_datasets),
            'failed': len(failed_datasets),
            'successful_datasets': successful_datasets,
            'failed_datasets': failed_datasets
        }
        
        return results

def main():
    """Main validation function."""
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    print("🔍 Running Texture Coordinate Alignment Validation...")
    print("=" * 60)
    
    validator = TextureAlignmentValidator()
    results = validator.run_full_validation()
    
    print("\n📊 VALIDATION SUMMARY:")
    print(f"  Total datasets tested: {results['summary']['total_datasets']}")
    print(f"  Successful: {results['summary']['successful']}")
    print(f"  Failed: {results['summary']['failed']}")
    
    if results['overall_success']:
        print("\n✅ ALL DATASETS PASSED COORDINATE ALIGNMENT VALIDATION!")
        print("🌍 Textures should be properly aligned on the 3D globe visualization.")
    else:
        print(f"\n❌ VALIDATION FAILED for datasets: {results['summary']['failed_datasets']}")
        print("⚠️  Coordinate alignment issues detected - textures may be misaligned.")
        
        # Print detailed errors
        for dataset in results['summary']['failed_datasets']:
            dataset_results = results['datasets'][dataset]
            print(f"\n{dataset.upper()} ERRORS:")
            for error in dataset_results.get('errors', []):
                print(f"  - {error}")
    
    print("\n" + "=" * 60)
    return 0 if results['overall_success'] else 1

if __name__ == "__main__":
    sys.exit(main())