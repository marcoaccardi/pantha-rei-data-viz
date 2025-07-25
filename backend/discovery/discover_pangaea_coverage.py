#!/usr/bin/env python3
"""
Discover PANGAEA coverage.
Maps research dataset coverage, DOI catalog, and parameter availability.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add clients directory to path
sys.path.append(str(Path(__file__).parent.parent / 'clients'))
sys.path.append(str(Path(__file__).parent.parent / 'config'))
sys.path.append(str(Path(__file__).parent.parent / 'utils'))

from pangaea_client import PANGAEAClient
from coverage_mapper import CoverageMapper

def main():
    """Discover and analyze PANGAEA coverage."""
    
    print("=" * 60)
    print("PANGAEA API COVERAGE DISCOVERY")
    print("=" * 60)
    print()
    
    # Initialize client
    cache_dir = Path(__file__).parent.parent / 'output' / 'sample_data'
    client = PANGAEAClient(cache_dir=cache_dir)
    
    try:
        # Discover coverage
        print("🔍 Discovering PANGAEA coverage...")
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
        
        # Research areas coverage
        research_areas = coverage_data.get('research_areas', {})
        if research_areas:
            print(f"\n🔬 Research Areas Coverage:")
            print(f"   Total Research Areas: {len(research_areas)}")
            
            for area_name, area_data in research_areas.items():
                print(f"\n   • {area_name.replace('_', ' ').title()}:")
                print(f"     Description: {area_data.get('description', 'No description')}")
                print(f"     Parameters: {len(area_data.get('parameters', []))}")
                print(f"     Keywords: {', '.join(area_data.get('keywords', []))}")
                print(f"     Estimated Datasets: {area_data.get('estimated_dataset_count', 'Unknown')}")
                
                # Geographic focus
                geo_focus = area_data.get('geographic_focus', [])
                if geo_focus:
                    print(f"     Geographic Focus: {', '.join(geo_focus)}")
                
                # Sample DOIs
                sample_dois = area_data.get('sample_datasets', [])
                if sample_dois:
                    print(f"     Sample DOIs: {len(sample_dois)} available")
                    for doi in sample_dois[:2]:  # Show first 2
                        print(f"       - {doi}")
        
        # Geographic coverage
        geo_cov = coverage_data.get('geographic_coverage', {})
        if geo_cov:
            print(f"\n🌍 Geographic Coverage:")
            print(f"   Global Datasets: {geo_cov.get('global_datasets', False)}")
            
            ocean_basins = geo_cov.get('ocean_basins_covered', [])
            if ocean_basins:
                print(f"   Ocean Basins: {', '.join(ocean_basins)}")
            
            special_regions = geo_cov.get('special_regions', [])
            if special_regions:
                print(f"   Special Regions: {', '.join(special_regions[:5])}")  # Show first 5
            
            depth_cov = geo_cov.get('depth_coverage', {})
            if depth_cov:
                print(f"   Depth Coverage:")
                for depth_zone, available in depth_cov.items():
                    status = "✅" if available else "❌"
                    zone_name = depth_zone.replace('_', ' ').title()
                    print(f"     {status} {zone_name}")
        
        # Parameter availability
        param_avail = coverage_data.get('parameter_availability', {})
        if param_avail:
            print(f"\n🔬 Parameter Availability:")
            print(f"   Total Unique Parameters: {param_avail.get('total_parameters', 0)}")
            
            params_by_category = param_avail.get('parameters_by_category', {})
            for category, parameters in params_by_category.items():
                category_name = category.replace('_', ' ').title()
                print(f"   • {category_name}: {len(parameters)} parameters")
                # Show first few parameters
                for param in parameters[:3]:
                    print(f"     - {param}")
                if len(parameters) > 3:
                    print(f"     ... and {len(parameters) - 3} more")
        
        # Temporal coverage
        temporal_cov = coverage_data.get('temporal_coverage', {})
        if temporal_cov:
            print(f"\n📅 Temporal Coverage:")
            print(f"   Archive Focus: {temporal_cov.get('archive_focus', False)}")
            print(f"   Real-time Data: {temporal_cov.get('real_time_data', False)}")
            print(f"   Historical Records: {temporal_cov.get('historical_records', 'Unknown')}")
            print(f"   Paleoclimate Records: {temporal_cov.get('paleoclimate_records', 'Unknown')}")
            print(f"   Modern Observations: {temporal_cov.get('modern_observations', 'Unknown')}")
        
        # Dataset statistics
        dataset_stats = coverage_data.get('dataset_statistics', {})
        if dataset_stats:
            print(f"\n📈 Dataset Statistics:")
            print(f"   Estimated Total Datasets: {dataset_stats.get('estimated_total_datasets', 'Unknown')}")
            print(f"   Marine Datasets: {dataset_stats.get('marine_datasets', 'Unknown')}")
            print(f"   Climate-related: {dataset_stats.get('climate_related', 'Unknown')}")
            print(f"   Microplastics Datasets: {dataset_stats.get('microplastics_datasets', 'Unknown')}")
            print(f"   Quality Control: {dataset_stats.get('quality_control', 'Unknown')}")
            print(f"   DOI Assignment: {dataset_stats.get('doi_assignment', 'Unknown')}")
        
        # Save detailed results
        output_dir = Path(__file__).parent.parent / 'output' / 'coverage_maps'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / 'pangaea_coverage_detailed.json'
        with open(output_file, 'w') as f:
            json.dump(coverage_data, f, indent=2, default=str)
        
        print(f"\n💾 Detailed results saved to: {output_file}")
        
        # Test dataset search
        print(f"\n🧪 DATASET SEARCH TEST")
        print("-" * 40)
        
        # Test microplastics search
        search_keywords = ['microplastic', 'marine debris']
        research_area = 'microplastics'
        
        print(f"Searching for: {', '.join(search_keywords)}")
        print(f"Research area filter: {research_area}")
        
        search_results = client.search_datasets(
            keywords=search_keywords,
            research_area=research_area
        )
        
        print(f"\nSearch Results:")
        print(f"   Total Matches: {search_results.get('total_matches', 0)}")
        
        results = search_results.get('results', [])
        if results:
            print(f"   Sample Datasets:")
            for i, result in enumerate(results[:3], 1):  # Show first 3
                print(f"   {i}. DOI: {result.get('doi', 'Unknown')}")
                print(f"      Research Area: {result.get('research_area', 'Unknown')}")
                print(f"      Access URL: {result.get('url', 'Unknown')}")
                print(f"      Parameters: {len(result.get('estimated_parameters', []))}")
        else:
            suggestions = search_results.get('suggestions', [])
            if suggestions:
                print(f"   Suggestions:")
                for suggestion in suggestions:
                    print(f"   • {suggestion}")
        
        # Test data query guidance
        print(f"\n🧪 DATA ACCESS GUIDANCE TEST")
        print("-" * 40)
        
        # Test coordinates (North Pacific Gyre - microplastics hotspot)
        test_lat, test_lon = 35.0, -155.0
        start_date, end_date = '2020-01-01', '2023-12-31'
        
        print(f"Getting guidance for: {test_lat}°N, {test_lon}°W (North Pacific Gyre)")
        print(f"Date range: {start_date} to {end_date}")
        print(f"Research focus: microplastics")
        
        query_result = client.query_data(
            lat=test_lat,
            lon=test_lon,
            start_date=start_date,
            end_date=end_date,
            research_area='microplastics'
        )
        
        print(f"\nQuery Status: {query_result.get('status', 'Unknown')}")
        print(f"Message: {query_result.get('message', 'No message')}")
        
        # Show recommended workflow
        workflow = query_result.get('recommended_workflow', [])
        if workflow:
            print(f"\nRecommended Workflow:")
            for step in workflow:
                print(f"   {step}")
        
        # Show relevant datasets
        relevant_datasets = query_result.get('relevant_datasets', [])
        if relevant_datasets:
            print(f"\nRelevant Datasets ({len(relevant_datasets)} found):")
            for dataset in relevant_datasets[:3]:  # Show first 3
                print(f"   • DOI: {dataset.get('doi', 'Unknown')}")
                print(f"     Research Area: {dataset.get('research_area', 'Unknown')}")
                print(f"     Geographic Relevance: {dataset.get('geographic_relevance', {}).get('ocean_basin', 'Unknown')}")
                print(f"     Access: {dataset.get('access_url', 'Unknown')}")
        
        # Show access instructions
        access_instructions = query_result.get('access_instructions', {})
        if access_instructions:
            print(f"\n📚 ACCESS INSTRUCTIONS")
            print("-" * 40)
            
            python_access = access_instructions.get('python_access', {})
            if python_access:
                print(f"Python Access:")
                print(f"   Package: {python_access.get('package', 'Unknown')}")
                print(f"   Installation: {python_access.get('installation', 'Unknown')}")
                print(f"   Example Code:")
                example_code = python_access.get('example_code', '').strip()
                for line in example_code.split('\n'):
                    print(f"     {line}")
        
        print(f"\n✅ PANGAEA coverage discovery completed!")
        
    except Exception as e:
        print(f"\n❌ Coverage discovery failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        client.close()

if __name__ == "__main__":
    main()