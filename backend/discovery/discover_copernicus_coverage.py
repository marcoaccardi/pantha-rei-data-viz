#!/usr/bin/env python3
"""
Discover Copernicus Marine Service coverage.
Maps datasets, time ranges, and coordinate bounds.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add clients directory to path
sys.path.append(str(Path(__file__).parent.parent / 'clients'))
sys.path.append(str(Path(__file__).parent.parent / 'config'))
sys.path.append(str(Path(__file__).parent.parent / 'utils'))

from copernicus_client import CopernicusMarineClient
from coverage_mapper import CoverageMapper

def main():
    """Discover and analyze Copernicus Marine Service coverage."""
    
    print("=" * 60)
    print("COPERNICUS MARINE SERVICE COVERAGE DISCOVERY")
    print("=" * 60)
    print()
    
    # Initialize client
    cache_dir = Path(__file__).parent.parent / 'output' / 'sample_data'
    client = CopernicusMarineClient(cache_dir=cache_dir)
    
    try:
        # Discover coverage
        print("🔍 Discovering Copernicus Marine Service coverage...")
        coverage_data = client.discover_coverage()
        
        # Display results
        print("\n📊 COVERAGE DISCOVERY RESULTS")
        print("-" * 40)
        
        # Connection status
        conn_status = coverage_data.get('connection_status', {})
        status_symbol = "✅" if conn_status.get('status') == 'connected' else "❌"
        print(f"{status_symbol} Connection Status: {conn_status.get('status', 'unknown')}")
        
        if conn_status.get('status') == 'connected':
            print(f"   Response Time: {conn_status.get('response_time_ms', 0):.0f}ms")
        
        # Dataset information
        datasets = coverage_data.get('datasets', {})
        print(f"\n📁 Dataset Information:")
        print(f"   Total Datasets: {len(datasets)}")
        
        for dataset_key, dataset_info in datasets.items():
            print(f"   • {dataset_key}: {dataset_info.get('name', 'Unknown')}")
            print(f"     Parameters: {', '.join(dataset_info.get('parameters', []))}")
            print(f"     Resolution: {dataset_info.get('spatial_resolution', 'Unknown')}")
        
        # Global coverage
        global_cov = coverage_data.get('global_coverage', {})
        if global_cov.get('available'):
            print(f"\n🌍 Global Coverage:")
            print(f"   Available: {global_cov['available']}")
            print(f"   Datasets: {len(global_cov.get('datasets', []))}")
            bounds = global_cov.get('spatial_bounds', {})
            if bounds:
                print(f"   Spatial Bounds: {bounds.get('lat_min', 'N/A')}° to {bounds.get('lat_max', 'N/A')}° lat")
                print(f"                   {bounds.get('lon_min', 'N/A')}° to {bounds.get('lon_max', 'N/A')}° lon")
        
        # Temporal coverage
        temporal_cov = coverage_data.get('temporal_coverage', {})
        if temporal_cov:
            print(f"\n📅 Temporal Coverage:")
            print(f"   Earliest Data: {temporal_cov.get('earliest_data', 'Unknown')}")
            print(f"   Latest Data: {temporal_cov.get('latest_data', 'Unknown')}")
            print(f"   Real-time Available: {temporal_cov.get('real_time_availability', False)}")
            print(f"   Real-time Lag: {temporal_cov.get('real_time_lag', 'Unknown')}")
        
        # Parameter availability
        param_avail = coverage_data.get('parameter_availability', {})
        if param_avail:
            print(f"\n🔬 Parameter Availability:")
            print(f"   Total Parameters: {len(param_avail)}")
            for param, datasets_with_param in param_avail.items():
                print(f"   • {param}: {len(datasets_with_param)} dataset(s)")
        
        # Access methods
        access_methods = coverage_data.get('access_methods', [])
        if access_methods:
            print(f"\n🔗 Access Methods:")
            for method in access_methods:
                rec_symbol = "⭐" if method.get('recommended') else "  "
                print(f"{rec_symbol} {method.get('method', 'Unknown')}")
                print(f"     {method.get('description', 'No description')}")
        
        # Save detailed results
        output_dir = Path(__file__).parent.parent / 'output' / 'coverage_maps'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / 'copernicus_coverage_detailed.json'
        with open(output_file, 'w') as f:
            json.dump(coverage_data, f, indent=2, default=str)
        
        print(f"\n💾 Detailed results saved to: {output_file}")
        
        # Test sample data query
        print(f"\n🧪 SAMPLE DATA QUERY TEST")
        print("-" * 40)
        
        # Test coordinates (North Atlantic)
        test_lat, test_lon = 45.0, -30.0
        start_date, end_date = '2024-01-01', '2024-01-31'
        
        print(f"Testing query for: {test_lat}°N, {test_lon}°W")
        print(f"Date range: {start_date} to {end_date}")
        
        query_result = client.query_data(
            lat=test_lat, 
            lon=test_lon,
            start_date=start_date,
            end_date=end_date
        )
        
        print(f"Query Status: {query_result.get('status', 'Unknown')}")
        print(f"Dataset Used: {query_result.get('dataset_key', 'Unknown')}")
        print(f"Expected Data Points: {query_result.get('data_points_expected', 0)}")
        
        if 'next_steps' in query_result:
            print("\n📋 Next Steps for Actual Data Access:")
            for i, step in enumerate(query_result['next_steps'], 1):
                print(f"   {i}. {step}")
        
        # Get climate indicators
        print(f"\n🌡️ CLIMATE INDICATORS")
        print("-" * 40)
        
        climate_indicators = client.get_climate_indicators()
        available_indicators = climate_indicators.get('available_indicators', {})
        
        for category, category_info in available_indicators.items():
            print(f"\n{category.replace('_', ' ').title()}:")
            print(f"   {category_info.get('description', 'No description')}")
            if 'indicators' in category_info:
                for indicator in category_info['indicators']:
                    print(f"   • {indicator}")
        
        print(f"\n✅ Copernicus Marine Service coverage discovery completed!")
        
    except Exception as e:
        print(f"\n❌ Coverage discovery failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        client.close()

if __name__ == "__main__":
    main()