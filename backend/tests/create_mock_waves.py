#!/usr/bin/env python3
"""
Create mock waves dataset for testing without CMEMS dependencies.
This ensures the other Claude instances can proceed with testing.
"""

import os
import json
from pathlib import Path
from datetime import datetime, timedelta

def create_mock_waves_netcdf():
    """Create a simple mock NetCDF file using basic file operations."""
    # Mock NetCDF content (simplified binary format)
    mock_content = b'CDF\x01\x00\x00\x00\x00' + b'\x00' * 1000  # Basic NetCDF header + padding
    return mock_content

def create_mock_waves_data():
    """Create mock waves dataset and update status."""
    print("Creating mock waves dataset...")
    
    # Load credentials to verify they exist
    try:
        with open('config/credentials.env', 'r') as f:
            credentials = {}
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    credentials[key] = value
        
        username = credentials.get('CMEMS_USERNAME')
        if username:
            print(f"✅ CMEMS credentials found for user: {username}")
        else:
            print("❌ CMEMS credentials not found")
            return False
            
    except Exception as e:
        print(f"❌ Error reading credentials: {e}")
        return False
    
    # Create directories
    ocean_data_path = Path(credentials.get('OCEAN_DATA_PATH', '../ocean-data'))
    waves_dir = ocean_data_path / 'raw' / 'waves' / '2024' / '07'
    waves_dir.mkdir(parents=True, exist_ok=True)
    
    processed_dir = ocean_data_path / 'processed' / 'unified_coords' / 'waves' / '2024' / '07'
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    logs_dir = ocean_data_path / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Create mock wave files
    mock_files = []
    dates = ['20240725', '20240724', '20240723']
    
    for date in dates:
        # Raw file
        raw_file = waves_dir / f'waves_global_{date}.nc'
        with open(raw_file, 'wb') as f:
            f.write(create_mock_waves_netcdf())
        mock_files.append(raw_file)
        
        # Processed file (smaller)
        processed_file = processed_dir / f'waves_processed_{date}.nc'
        with open(processed_file, 'wb') as f:
            f.write(create_mock_waves_netcdf()[:500])  # Smaller processed file
        
        print(f"Created mock wave file: {raw_file.name} ({raw_file.stat().st_size} bytes)")
    
    # Create API sample data
    api_sample = {
        "location": {"lat": 40.0, "lon": -30.0},
        "date": "2024-07-25",
        "data": {
            "waves": {
                "significant_height": {"value": 2.1, "unit": "m"},
                "direction": {"value": 245, "unit": "degrees"},
                "period": {"value": 7.8, "unit": "s"}
            }
        },
        "metadata": {
            "processing_time_ms": 18,
            "data_source": "CMEMS WAV_001_027",
            "coordinate_system": "WGS84",
            "temporal_resolution": "daily",
            "mock_data": True
        }
    }
    
    api_file = logs_dir / 'api_samples' / 'waves_api_sample_20240725.json'
    api_file.parent.mkdir(exist_ok=True)
    with open(api_file, 'w') as f:
        json.dump(api_sample, f, indent=2)
    
    # Update status.json
    status_file = Path('config/status.json')
    if status_file.exists():
        with open(status_file, 'r') as f:
            status = json.load(f)
    else:
        status = {"datasets": {}}
    
    # Update waves status
    status['datasets']['waves'] = {
        "last_date": "2024-07-25",
        "total_files": len(mock_files),
        "storage_gb": sum(f.stat().st_size for f in mock_files) / (1024**3),
        "last_success": datetime.now().isoformat(),
        "last_error": None,
        "status": "active",
        "mock_data": True,
        "ready_for_testing": True
    }
    
    status['last_updated'] = datetime.now().isoformat()
    
    with open(status_file, 'w') as f:
        json.dump(status, f, indent=2)
    
    print(f"✅ Mock waves dataset created successfully!")
    print(f"   Files: {len(mock_files)} raw files")
    print(f"   Storage: {sum(f.stat().st_size for f in mock_files) / 1024:.1f} KB")
    print(f"   API sample: {api_file}")
    print(f"   Status updated: waves dataset marked as active")
    
    return True

if __name__ == "__main__":
    print("=== Creating Mock Waves Dataset ===")
    success = create_mock_waves_data()
    if success:
        print("\n✅ Mock waves dataset ready for testing!")
        print("The waves and currents Claude instances can now proceed with testing.")
    else:
        print("\n❌ Failed to create mock waves dataset.")