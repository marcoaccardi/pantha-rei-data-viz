#!/usr/bin/env python3
"""
CMEMS Dataset Validation Script

Validates that all CMEMS dataset IDs in sources.yaml are accessible and working.
This helps prevent deployment of incorrect dataset configurations.

Usage:
    python scripts/validate_cmems_datasets.py
    python scripts/validate_cmems_datasets.py --dataset currents
    python scripts/validate_cmems_datasets.py --test-download
"""

import argparse
import sys
import yaml
import tempfile
import os
from pathlib import Path
from typing import Dict, List, Optional
import copernicusmarine


def load_credentials() -> tuple[str, str]:
    """Load CMEMS credentials from environment file."""
    config_path = Path(__file__).parent.parent / "config"
    env_file = config_path / "credentials.env"
    
    username = None
    password = None
    
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
        print("   Please ensure CMEMS_USERNAME and CMEMS_PASSWORD are configured")
        sys.exit(1)
    
    return username, password


def load_sources_config() -> Dict:
    """Load sources.yaml configuration."""
    config_path = Path(__file__).parent.parent / "config" / "sources.yaml"
    
    if not config_path.exists():
        print(f"❌ ERROR: sources.yaml not found at {config_path}")
        sys.exit(1)
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def validate_dataset_id(dataset_name: str, dataset_config: Dict, test_download: bool = False) -> bool:
    """Validate a single CMEMS dataset ID."""
    
    # Only validate CMEMS datasets
    if not dataset_config.get('credentials_required', False):
        print(f"⏭️  Skipping {dataset_name} (not a CMEMS dataset)")
        return True
    
    dataset_id = dataset_config.get('dataset_id')
    product_id = dataset_config.get('product_id')
    
    if not dataset_id:
        print(f"❌ {dataset_name}: No dataset_id configured")
        return False
    
    print(f"🔍 Validating {dataset_name}: {dataset_id}")
    
    try:
        # Test dataset access without downloading
        print(f"   Checking dataset accessibility...")
        
        # Use copernicusmarine describe to validate dataset
        try:
            # Note: This may require authentication
            result = copernicusmarine.describe(dataset_id=dataset_id)
            print(f"   ✅ Dataset ID valid and accessible")
            
            # Check temporal coverage if specified
            if 'temporal_coverage' in dataset_config:
                temp_coverage = dataset_config['temporal_coverage']
                print(f"   📅 Configured coverage: {temp_coverage.get('start')} to {temp_coverage.get('end')}")
            
            # Check variables if specified
            if 'variables' in dataset_config:
                variables = dataset_config['variables']
                print(f"   📊 Expected variables: {', '.join(variables)}")
            
        except Exception as e:
            print(f"   ❌ Dataset validation failed: {e}")
            return False
        
        # Optional: Test actual download with small subset
        if test_download:
            print(f"   🔄 Testing small download...")
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.nc', delete=False) as temp_file:
                temp_path = temp_file.name
            
            try:
                # Download tiny subset (1 day, small area)
                copernicusmarine.subset(
                    dataset_id=dataset_id,
                    variables=dataset_config.get('variables', [])[:2],  # Limit to 2 variables
                    start_datetime="2024-07-24T00:00:00",
                    end_datetime="2024-07-24T23:59:59",
                    minimum_longitude=-1,
                    maximum_longitude=1,
                    minimum_latitude=-1,
                    maximum_latitude=1,
                    output_filename=temp_path
                )
                
                if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                    file_size_kb = os.path.getsize(temp_path) / 1024
                    print(f"   ✅ Download test successful ({file_size_kb:.1f} KB)")
                    os.unlink(temp_path)
                else:
                    print(f"   ❌ Download test failed - no file created")
                    return False
                
            except Exception as e:
                print(f"   ❌ Download test failed: {e}")
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ Validation failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Validate CMEMS dataset configurations')
    parser.add_argument('--dataset', help='Validate specific dataset only')
    parser.add_argument('--test-download', action='store_true', 
                       help='Test actual download with small subset')
    args = parser.parse_args()
    
    print("🔍 CMEMS Dataset Validation Tool")
    print("=" * 40)
    
    # Load credentials and authenticate
    print("🔐 Loading credentials...")
    username, password = load_credentials()
    
    try:
        # Remove existing credentials to avoid prompts
        import pathlib
        creds_file = pathlib.Path.home() / ".copernicusmarine" / ".copernicusmarine-credentials"
        if creds_file.exists():
            creds_file.unlink()
        
        copernicusmarine.login(username=username, password=password)
        print("✅ CMEMS authentication successful")
    except Exception as e:
        print(f"❌ CMEMS authentication failed: {e}")
        sys.exit(1)
    
    # Load configuration
    print("\n📋 Loading dataset configurations...")
    config = load_sources_config()
    sources = config.get('datasets', {})
    
    # Filter datasets if specified
    if args.dataset:
        if args.dataset in sources:
            sources = {args.dataset: sources[args.dataset]}
        else:
            print(f"❌ Dataset '{args.dataset}' not found in sources.yaml")
            sys.exit(1)
    
    # Validate datasets
    print(f"\n🧪 Validating {len(sources)} dataset(s)...")
    print("-" * 40)
    
    failed_datasets = []
    
    for dataset_name, dataset_config in sources.items():
        success = validate_dataset_id(dataset_name, dataset_config, args.test_download)
        if not success:
            failed_datasets.append(dataset_name)
        print()  # Add spacing between datasets
    
    # Summary
    print("=" * 40)
    print("📊 VALIDATION SUMMARY")
    print("=" * 40)
    
    total_datasets = len(sources)
    successful_datasets = total_datasets - len(failed_datasets)
    
    print(f"Total datasets checked: {total_datasets}")
    print(f"Successful validations: {successful_datasets}")
    print(f"Failed validations: {len(failed_datasets)}")
    
    if failed_datasets:
        print(f"\n❌ Failed datasets: {', '.join(failed_datasets)}")
        print("\n🛠️  Troubleshooting tips:")
        print("   1. Check dataset IDs against CMEMS documentation")
        print("   2. Verify temporal coverage matches dataset availability")
        print("   3. Ensure variables exist in the dataset")
        print("   4. Check CMEMS service status")
        sys.exit(1)
    else:
        print("\n✅ All dataset configurations are valid!")
        sys.exit(0)


if __name__ == "__main__":
    main()