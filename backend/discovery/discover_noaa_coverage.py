#!/usr/bin/env python3
"""
Discover NOAA CO-OPS coverage.
Maps station locations, data history ranges, and available parameters.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add clients directory to path
sys.path.append(str(Path(__file__).parent.parent / 'clients'))
sys.path.append(str(Path(__file__).parent.parent / 'config'))
sys.path.append(str(Path(__file__).parent.parent / 'utils'))

from noaa_cops_client import NOAACOPSClient
from coverage_mapper import CoverageMapper

def main():
    """Discover and analyze NOAA CO-OPS coverage."""
    
    print("=" * 60)
    print("NOAA CO-OPS API COVERAGE DISCOVERY")
    print("=" * 60)
    print()
    
    # Initialize client
    cache_dir = Path(__file__).parent.parent / 'output' / 'sample_data'
    client = NOAACOPSClient(cache_dir=cache_dir)
    
    try:
        # Discover coverage
        print("🔍 Discovering NOAA CO-OPS coverage...")
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
        
        # Station information
        stations_info = coverage_data.get('stations', {})
        if stations_info:
            print(f"\n🗺️ Station Information:")
            print(f"   Total Stations: {stations_info.get('total_count', 0)}")
            print(f"   Active Stations: {stations_info.get('active_count', 0)}")
            
            geo_dist = stations_info.get('geographic_distribution', {})
            if 'by_state' in geo_dist:
                top_states = list(geo_dist['by_state'].items())[:5]
                print(f"   Top States by Station Count:")
                for state, count in top_states:
                    print(f"     • {state}: {count} stations")
        
        # Geographic coverage
        geo_cov = coverage_data.get('geographic_coverage', {})
        if geo_cov:
            print(f"\n🌍 Geographic Coverage:")
            regions = geo_cov.get('regions_covered', [])
            print(f"   Regions Covered: {', '.join(regions)}")
            
            coastal_cov = geo_cov.get('coastal_coverage', {})
            if coastal_cov:
                print(f"   Coastal Distribution:")
                for region, count in coastal_cov.items():
                    if count > 0:
                        region_name = region.replace('_', ' ').title()
                        print(f"     • {region_name}: {count} stations")
            
            bounds = geo_cov.get('spatial_bounds', {})
            if bounds:
                print(f"   Spatial Bounds: {bounds.get('lat_min', 'N/A'):.1f}° to {bounds.get('lat_max', 'N/A'):.1f}° lat")
                print(f"                   {bounds.get('lon_min', 'N/A'):.1f}° to {bounds.get('lon_max', 'N/A'):.1f}° lon")
        
        # Parameter availability
        param_avail = coverage_data.get('parameter_availability', {})
        if param_avail:
            print(f"\n🔬 Parameter Availability:")
            for param_key, param_info in param_avail.items():
                param_name = param_info.get('name', param_key)
                coverage_pct = param_info.get('estimated_station_coverage', 0) * 100
                station_count = param_info.get('estimated_stations_with_data', 0)
                units = param_info.get('units', 'unknown')
                
                print(f"   • {param_name}:")
                print(f"     Coverage: {coverage_pct:.0f}% of stations (~{station_count} stations)")
                print(f"     Units: {units}")
                print(f"     Resolution: {param_info.get('temporal_resolution', 'unknown')}")
        
        # Temporal coverage
        temporal_cov = coverage_data.get('temporal_coverage', {})
        if temporal_cov:
            print(f"\n📅 Temporal Coverage:")
            print(f"   Real-time Data: {temporal_cov.get('real_time_data', False)}")
            print(f"   Historical Archive: {temporal_cov.get('historical_archive', False)}")
            print(f"   Oldest Records: {temporal_cov.get('oldest_records', 'Unknown')}")
            print(f"   Update Frequency: {temporal_cov.get('update_frequency', 'Unknown')}")
            print(f"   Climate Records: {temporal_cov.get('climate_records', 'Unknown')}")
        
        # Data products
        data_products = coverage_data.get('data_products', {})
        if data_products:
            print(f"\n📦 Available Data Products:")
            for product_key, product_info in data_products.items():
                print(f"   • {product_info.get('name', product_key)}:")
                print(f"     Description: {product_info.get('description', 'No description')}")
                print(f"     Frequency: {product_info.get('frequency', 'unknown')}")
                print(f"     Units: {product_info.get('units', 'unknown')}")
        
        # Save detailed results
        output_dir = Path(__file__).parent.parent / 'output' / 'coverage_maps'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / 'noaa_cops_coverage_detailed.json'
        with open(output_file, 'w') as f:
            json.dump(coverage_data, f, indent=2, default=str)
        
        print(f"\n💾 Detailed results saved to: {output_file}")
        
        # Test nearest station finder
        print(f"\n🧪 NEAREST STATION TEST")
        print("-" * 40)
        
        # Test coordinates (Florida Keys)
        test_lat, test_lon = 24.7, -80.9
        print(f"Finding stations near: {test_lat}°N, {test_lon}°W (Florida Keys)")
        
        nearest_stations = client.find_nearest_stations(test_lat, test_lon, max_stations=3)
        
        if nearest_stations:
            print(f"Found {len(nearest_stations)} nearby stations:")
            for i, station in enumerate(nearest_stations, 1):
                print(f"   {i}. Station {station.get('id', 'Unknown')}")
                print(f"      Name: {station.get('name', 'Unknown')}")
                print(f"      Distance: {station.get('distance_km', 0):.1f} km")
                print(f"      Location: {station.get('lat', 0):.3f}°N, {station.get('lng', 0):.3f}°W")
        else:
            print("   No stations found within search radius")
        
        # Test data query
        if nearest_stations:
            print(f"\n🧪 SAMPLE DATA QUERY TEST")
            print("-" * 40)
            
            start_date, end_date = '2024-01-01', '2024-01-31'
            parameters = ['monthly_mean', 'water_temperature']
            
            print(f"Testing query for: {test_lat}°N, {test_lon}°W")
            print(f"Date range: {start_date} to {end_date}")
            print(f"Parameters: {', '.join(parameters)}")
            
            query_result = client.query_data(
                lat=test_lat,
                lon=test_lon, 
                start_date=start_date,
                end_date=end_date,
                parameters=parameters
            )
            
            print(f"\nQuery Status: {query_result.get('status', 'Unknown')}")
            
            station_info = query_result.get('station_info', {})
            if station_info:
                print(f"Station Used: {station_info.get('id', 'Unknown')}")
                print(f"Distance: {station_info.get('distance_km', 0):.1f} km")
            
            results = query_result.get('results', [])
            total_points = query_result.get('data_points_total', 0)
            print(f"Total Data Points: {total_points}")
            
            if results:
                print(f"\nParameter Results:")
                for result in results:
                    param_name = result.get('parameter', 'Unknown')
                    status = result.get('status', 'Unknown')
                    data_points = result.get('data_points', 0)
                    
                    status_symbol = "✅" if status == 'success' else "❌"
                    print(f"   {status_symbol} {param_name}: {status}")
                    if status == 'success':
                        print(f"      Data Points: {data_points}")
                        print(f"      Units: {result.get('units', 'Unknown')}")
                    elif 'error' in result:
                        print(f"      Error: {result['error']}")
        
        print(f"\n✅ NOAA CO-OPS coverage discovery completed!")
        
    except Exception as e:
        print(f"\n❌ Coverage discovery failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        client.close()

if __name__ == "__main__":
    main()