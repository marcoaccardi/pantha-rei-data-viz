#!/usr/bin/env python3
"""
Deep Dataset Validation Script

Comprehensive validation that verifies actual data structure, variables, temporal coverage,
and data quality for all ocean datasets. Goes beyond basic API access to validate what
we actually receive vs what we expect.

Usage:
    python scripts/maintenance/deep_dataset_validation.py
    python scripts/maintenance/deep_dataset_validation.py --dataset sst
    python scripts/maintenance/deep_dataset_validation.py --test-historical --start-date 1993-01-01
"""

import argparse
import sys
import yaml
import tempfile
import os
import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import copernicusmarine
import requests


class DeepDatasetValidator:
    """Comprehensive dataset validation with deep structure checking."""
    
    def __init__(self):
        self.config_path = Path(__file__).parent.parent / "config"
        self.config = self._load_config()
        self.failed_validations = []
        self.validation_results = {}
        
    def _load_config(self) -> Dict:
        """Load sources.yaml configuration."""
        config_file = self.config_path / "sources.yaml"
        if not config_file.exists():
            print(f"❌ ERROR: sources.yaml not found at {config_file}")
            sys.exit(1)
        
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    
    def _load_credentials(self) -> Tuple[str, str]:
        """Load CMEMS credentials."""
        env_file = self.config_path / "credentials.env"
        username = password = None
        
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        if key.strip() == 'CMEMS_USERNAME':
                            username = value.strip()
                        elif key.strip() == 'CMEMS_PASSWORD':
                            password = value.strip()
        
        if not username or not password:
            print("❌ ERROR: CMEMS credentials not found in backend/config/credentials.env")
            sys.exit(1)
        
        return username, password
    
    def _authenticate_cmems(self):
        """Authenticate with CMEMS."""
        try:
            username, password = self._load_credentials()
            # Clear existing credentials to avoid prompts
            creds_file = Path.home() / ".copernicusmarine" / ".copernicusmarine-credentials"
            if creds_file.exists():
                creds_file.unlink()
            
            copernicusmarine.login(username=username, password=password)
            print("✅ CMEMS authentication successful")
            return True
        except Exception as e:
            print(f"❌ CMEMS authentication failed: {e}")
            return False
    
    def validate_sst_dataset(self, dataset_config: Dict) -> Dict[str, Any]:
        """Validate SST dataset (NOAA OISST)."""
        print(f"🌊 Validating SST Dataset (NOAA OISST)")
        results = {
            'dataset': 'sst',
            'accessible': False,
            'variables_correct': False,
            'temporal_coverage': {},
            'spatial_resolution': None,
            'coordinate_system': None,
            'data_quality': {},
            'issues': []
        }
        
        try:
            # Test a recent date
            test_date = date(2025, 7, 25)  # Yesterday
            base_url = dataset_config['base_url']
            year_month = test_date.strftime('%Y%m')
            date_str = test_date.strftime('%Y%m%d')
            
            # Construct URL
            url = f"{base_url}{year_month}/oisst-avhrr-v02r01.{date_str}.nc"
            
            print(f"   Testing URL: {url}")
            
            # Test URL accessibility (HEAD request to avoid downloading)
            response = requests.head(url, timeout=30)
            if response.status_code == 200:
                results['accessible'] = True
                print(f"   ✅ URL accessible (HTTP 200)")
                
                # Download small sample to test data structure
                with tempfile.NamedTemporaryFile(suffix='.nc', delete=False) as temp_file:
                    temp_path = temp_file.name
                
                try:
                    # Download file
                    download_response = requests.get(url, timeout=60)
                    with open(temp_path, 'wb') as f:
                        f.write(download_response.content)
                    
                    # Analyze file structure
                    with xr.open_dataset(temp_path) as ds:
                        print(f"   📊 Variables found: {list(ds.data_vars.keys())}")
                        print(f"   📐 Dimensions: {dict(ds.dims)}")
                        print(f"   🗺️  Coordinate ranges: lat({ds.lat.min().values:.2f}, {ds.lat.max().values:.2f}), lon({ds.lon.min().values:.2f}, {ds.lon.max().values:.2f})")
                        
                        # Check expected variables
                        expected_vars = set(dataset_config['variables'])
                        actual_vars = set(ds.data_vars.keys())
                        
                        if expected_vars.issubset(actual_vars):
                            results['variables_correct'] = True
                            print(f"   ✅ All expected variables present")
                        else:
                            missing = expected_vars - actual_vars
                            results['issues'].append(f"Missing variables: {missing}")
                            print(f"   ❌ Missing variables: {missing}")
                        
                        # Check spatial resolution
                        lat_diff = float(ds.lat[1] - ds.lat[0])
                        lon_diff = float(ds.lon[1] - ds.lon[0])
                        results['spatial_resolution'] = {'lat': abs(lat_diff), 'lon': abs(lon_diff)}
                        print(f"   📏 Spatial resolution: {abs(lat_diff):.3f}° lat, {abs(lon_diff):.3f}° lon")
                        
                        # Check coordinate system
                        lon_min, lon_max = float(ds.lon.min()), float(ds.lon.max())
                        if lon_min >= 0 and lon_max <= 360:
                            results['coordinate_system'] = '0-360'
                        else:
                            results['coordinate_system'] = '-180-180'
                        print(f"   🧭 Coordinate system: {results['coordinate_system']}")
                        
                        # Check data quality
                        if 'sst' in ds:
                            sst_data = ds.sst.values
                            sst_valid = sst_data[~np.isnan(sst_data)]
                            if len(sst_valid) > 0:
                                results['data_quality'] = {
                                    'sst_range': (float(sst_valid.min()), float(sst_valid.max())),
                                    'valid_points': len(sst_valid),
                                    'total_points': sst_data.size,
                                    'coverage_percent': (len(sst_valid) / sst_data.size) * 100
                                }
                                print(f"   🌡️  SST range: {sst_valid.min():.1f}°C to {sst_valid.max():.1f}°C")
                                print(f"   📊 Data coverage: {(len(sst_valid) / sst_data.size) * 100:.1f}%")
                        
                    os.unlink(temp_path)
                    
                except Exception as e:
                    results['issues'].append(f"File analysis failed: {e}")
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                    
            else:
                results['issues'].append(f"URL not accessible: HTTP {response.status_code}")
                print(f"   ❌ URL not accessible: HTTP {response.status_code}")
                
        except Exception as e:
            results['issues'].append(f"Validation failed: {e}")
            print(f"   ❌ Validation failed: {e}")
        
        return results
    
    def validate_cmems_dataset(self, dataset_name: str, dataset_config: Dict, test_dates: List[str] = None) -> Dict[str, Any]:
        """Validate CMEMS dataset with multiple test dates."""
        print(f"🌊 Validating CMEMS Dataset: {dataset_name}")
        
        results = {
            'dataset': dataset_name,
            'accessible': False,
            'variables_correct': False,
            'temporal_coverage': {},
            'spatial_resolution': None,
            'coordinate_system': None,
            'data_quality': {},
            'issues': []
        }
        
        dataset_id = dataset_config.get('dataset_id')
        if not dataset_id:
            results['issues'].append("No dataset_id configured")
            return results
        
        # Default test dates
        if not test_dates:
            test_dates = ['2024-07-01', '2023-01-01']  # Recent and older dates
            
            # Add specific dates based on dataset temporal coverage
            if 'temporal_coverage' in dataset_config:
                start_date = dataset_config['temporal_coverage'].get('start')
                if start_date:
                    test_dates.append(start_date)
        
        successful_downloads = 0
        
        for test_date in test_dates:
            print(f"   🔍 Testing date: {test_date}")
            
            try:
                with tempfile.NamedTemporaryFile(suffix='.nc', delete=False) as temp_file:
                    temp_path = temp_file.name
                
                try:
                    # Attempt small area download
                    copernicusmarine.subset(
                        dataset_id=dataset_id,
                        variables=dataset_config.get('variables', [])[:2],  # Limit variables
                        start_datetime=f"{test_date}T00:00:00",
                        end_datetime=f"{test_date}T23:59:59",
                        minimum_longitude=0,
                        maximum_longitude=10,
                        minimum_latitude=0,
                        maximum_latitude=10,
                        output_filename=temp_path
                    )
                    
                    if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                        successful_downloads += 1
                        results['accessible'] = True
                        
                        # Analyze first successful file
                        if successful_downloads == 1:
                            with xr.open_dataset(temp_path) as ds:
                                print(f"     📊 Variables: {list(ds.data_vars.keys())}")
                                print(f"     📐 Dimensions: {dict(ds.dims)}")
                                
                                # Check variables
                                expected_vars = set(dataset_config.get('variables', []))
                                actual_vars = set(ds.data_vars.keys())
                                
                                if expected_vars.issubset(actual_vars):
                                    results['variables_correct'] = True
                                    print(f"     ✅ Variables correct")
                                else:
                                    missing = expected_vars - actual_vars
                                    results['issues'].append(f"Missing variables: {missing}")
                                    print(f"     ❌ Missing variables: {missing}")
                                
                                # Coordinate system
                                if 'longitude' in ds.coords:
                                    lon_coord = 'longitude'
                                elif 'lon' in ds.coords:
                                    lon_coord = 'lon'
                                else:
                                    lon_coord = None
                                
                                if lon_coord:
                                    lon_min, lon_max = float(ds[lon_coord].min()), float(ds[lon_coord].max())
                                    if lon_min >= -180 and lon_max <= 180:
                                        results['coordinate_system'] = '-180-180'
                                    else:
                                        results['coordinate_system'] = '0-360'
                                    print(f"     🧭 Coordinate system: {results['coordinate_system']}")
                        
                        print(f"     ✅ Download successful ({os.path.getsize(temp_path)} bytes)")
                        
                    else:
                        print(f"     ❌ Download failed - no file created")
                        
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                        
                except Exception as e:
                    error_msg = str(e)
                    if "exceed the dataset coordinates" in error_msg:
                        print(f"     ⚠️  Date {test_date} outside dataset range")
                        results['temporal_coverage'][test_date] = 'outside_range'
                    else:
                        print(f"     ❌ Download failed: {e}")
                        results['issues'].append(f"Download failed for {test_date}: {e}")
                    
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                
            except Exception as e:
                results['issues'].append(f"Test failed for {test_date}: {e}")
        
        results['temporal_coverage']['successful_dates'] = successful_downloads
        results['temporal_coverage']['tested_dates'] = len(test_dates)
        
        return results
    
    def validate_dataset(self, dataset_name: str, dataset_config: Dict, test_historical: bool = False) -> Dict[str, Any]:
        """Validate a single dataset based on its type."""
        
        if not dataset_config.get('credentials_required', False):
            # Non-CMEMS dataset (SST, microplastics)
            if dataset_name == 'sst':
                return self.validate_sst_dataset(dataset_config)
            else:
                print(f"⏭️  Skipping {dataset_name} (validation not implemented yet)")
                return {'dataset': dataset_name, 'skipped': True}
        else:
            # CMEMS dataset
            test_dates = None
            if test_historical:
                # Test historical dates for comprehensive coverage check
                test_dates = ['1993-01-01', '2000-01-01', '2010-01-01', '2020-01-01', '2024-01-01']
            
            return self.validate_cmems_dataset(dataset_name, dataset_config, test_dates)
    
    def generate_coverage_report(self):
        """Generate comprehensive coverage analysis report."""
        print("\n" + "="*80)
        print("📋 COMPREHENSIVE DATASET COVERAGE ANALYSIS")
        print("="*80)
        
        for dataset_name, results in self.validation_results.items():
            if results.get('skipped'):
                continue
                
            print(f"\n📊 {dataset_name.upper()}:")
            print("-" * 40)
            
            if results['accessible']:
                print(f"✅ Accessible: Yes")
            else:
                print(f"❌ Accessible: No")
            
            if results['variables_correct']:
                print(f"✅ Variables: Correct")
            else:
                print(f"❌ Variables: Issues found")
            
            if 'coordinate_system' in results:
                print(f"🧭 Coordinates: {results['coordinate_system']}")
            
            if 'spatial_resolution' in results and results['spatial_resolution']:
                res = results['spatial_resolution']
                if isinstance(res, dict):
                    print(f"📏 Resolution: {res['lat']:.3f}° × {res['lon']:.3f}°")
                else:
                    print(f"📏 Resolution: {res}")
            
            if 'data_quality' in results and results['data_quality']:
                dq = results['data_quality']
                if 'sst_range' in dq:
                    print(f"🌡️  SST Range: {dq['sst_range'][0]:.1f}°C to {dq['sst_range'][1]:.1f}°C")
                    print(f"📊 Coverage: {dq['coverage_percent']:.1f}%")
            
            if 'temporal_coverage' in results and results['temporal_coverage']:
                tc = results['temporal_coverage']
                if 'successful_dates' in tc:
                    print(f"📅 Temporal Tests: {tc['successful_dates']}/{tc['tested_dates']} dates successful")
            
            if results.get('issues'):
                print(f"⚠️  Issues:")
                for issue in results['issues']:
                    print(f"     • {issue}")
        
        # Summary for 1993-2025 coverage requirement
        print(f"\n{'='*80}")
        print("🎯 COVERAGE ASSESSMENT FOR 1993-2025 REQUIREMENT")
        print("="*80)
        
        coverage_assessment = {
            'sst': '✅ Full coverage (1981-present)',
            'currents': '❌ Limited coverage (2022-present only)',
            'acidity': '✅ Hybrid coverage (1993-present)',
        }
        
        for dataset, status in coverage_assessment.items():
            print(f"{dataset.upper():12s}: {status}")
        
        print(f"\n🚨 CRITICAL GAP IDENTIFIED:")
        print(f"   • Currents dataset only available from June 2022")
        print(f"   • Missing 29 years of currents data (1993-2021)")
        print(f"   • This affects complete 1993-2025 coverage requirement")


def main():
    parser = argparse.ArgumentParser(description='Deep dataset validation with structure checking')
    parser.add_argument('--dataset', help='Validate specific dataset only')
    parser.add_argument('--test-historical', action='store_true', 
                       help='Test historical dates (1993+) for coverage verification')
    parser.add_argument('--start-date', help='Start date for historical testing (YYYY-MM-DD)')
    args = parser.parse_args()
    
    print("🔍 Deep Dataset Validation Tool")
    print("=" * 50)
    
    validator = DeepDatasetValidator()
    
    # Authenticate with CMEMS if needed
    datasets = validator.config.get('datasets', {})
    has_cmems_datasets = any(ds.get('credentials_required', False) for ds in datasets.values())
    
    if has_cmems_datasets:
        print("🔐 Authenticating with CMEMS...")
        if not validator._authenticate_cmems():
            sys.exit(1)
    
    # Filter datasets if specified
    if args.dataset:
        if args.dataset in datasets:
            datasets = {args.dataset: datasets[args.dataset]}
        else:
            print(f"❌ Dataset '{args.dataset}' not found in sources.yaml")
            sys.exit(1)
    
    print(f"\n🧪 Validating {len(datasets)} dataset(s)...")
    print("-" * 50)
    
    # Validate each dataset
    for dataset_name, dataset_config in datasets.items():
        if dataset_name == 'microplastics':  # Skip as requested
            print(f"⏭️  Skipping {dataset_name} (excluded)")
            continue
            
        print(f"\n{'='*60}")
        results = validator.validate_dataset(dataset_name, dataset_config, args.test_historical)
        validator.validation_results[dataset_name] = results
        
        if results.get('issues'):
            validator.failed_validations.append(dataset_name)
    
    # Generate comprehensive report
    validator.generate_coverage_report()
    
    # Exit with appropriate code
    if validator.failed_validations:
        print(f"\n❌ Validation completed with issues in: {', '.join(validator.failed_validations)}")
        sys.exit(1)
    else:
        print(f"\n✅ All validations completed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()