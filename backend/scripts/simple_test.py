#!/usr/bin/env python3
"""Simple test to identify why synthetic data is being returned."""

import requests
import json
from datetime import datetime

def test_basic_erddap():
    """Test basic ERDDAP connection."""
    print("TESTING ERDDAP API CONNECTIVITY")
    print("=" * 50)
    
    urls = [
        "https://coastwatch.pfeg.noaa.gov/erddap/griddap/jplMURSST41.json",
        "https://pae-paha.pacioos.hawaii.edu/erddap/griddap/esa-cci-chla-monthly-v6-0.json"
    ]
    
    for url in urls:
        print(f"\nTesting: {url}")
        try:
            response = requests.get(url, timeout=15)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if 'table' in data:
                    print("✅ Dataset accessible")
                    columns = data['table'].get('columnNames', [])[:5]
                    print(f"Variables: {columns}")
                else:
                    print("⚠️ Unexpected response format")
            else:
                print(f"❌ HTTP Error: {response.text[:200]}")
                
        except requests.exceptions.Timeout:
            print("❌ TIMEOUT - Server too slow")
        except requests.exceptions.ConnectionError:
            print("❌ CONNECTION ERROR - Cannot reach server")
        except Exception as e:
            print(f"❌ ERROR: {e}")

def test_specific_query():
    """Test a specific data query."""
    print("\n\nTESTING SPECIFIC DATA QUERY")
    print("=" * 50)
    
    # Build a query for recent SST data near NYC
    base_url = "https://coastwatch.pfeg.noaa.gov/erddap/griddap"
    dataset = "jplMURSST41"
    
    # Query for today's data (or recent)
    date_str = "2025-07-23T12:00:00Z"  # Yesterday
    lat = 40.7
    lon = -74.0
    
    query_url = f"{base_url}/{dataset}.json?analysed_sst[({date_str}):1:({date_str})][({lat}):1:({lat})][({lon}):1:({lon})]"
    
    print(f"Query URL: {query_url}")
    
    try:
        headers = {'User-Agent': 'NOAA-Climate-System/1.0 (Investigation)'}
        response = requests.get(query_url, timeout=30)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            rows = data.get('table', {}).get('rows', [])
            if rows:
                print(f"✅ Got data: {rows[0]}")
            else:
                print("⚠️ No data rows returned")
        else:
            error_text = response.text[:300]
            print(f"❌ Query failed: {error_text}")
            
    except Exception as e:
        print(f"❌ Query error: {e}")

def test_why_synthetic():
    """Check common reasons for synthetic data."""
    print("\n\nANALYZING WHY SYNTHETIC DATA IS RETURNED")
    print("=" * 50)
    
    reasons = []
    
    # Check if imports work
    try:
        import sys
        sys.path.insert(0, 'src')
        from processors.fast_climate_processor import FastClimateProcessor
        print("✅ Processors import successfully")
        
        # Test the actual system
        processor = FastClimateProcessor()
        print("✅ FastClimateProcessor initialized")
        
        # Check ocean downloader status
        if processor.ocean_downloader is None:
            reasons.append("Ocean downloader failed to initialize")
            print("❌ Ocean downloader is None")
        else:
            print("✅ Ocean downloader initialized")
            
    except Exception as e:
        reasons.append(f"Import error: {e}")
        print(f"❌ Import failed: {e}")
    
    # Test direct API calls
    print("\nTesting individual API calls...")
    
    # Test NWS API (US weather)
    try:
        nws_url = "https://api.weather.gov/points/40.7128,-74.0060"
        response = requests.get(nws_url, timeout=10)
        if response.status_code == 200:
            print("✅ NWS API accessible")
        else:
            reasons.append("NWS API failed")
            print(f"❌ NWS API failed: {response.status_code}")
    except Exception as e:
        reasons.append(f"NWS API error: {e}")
        print(f"❌ NWS API error: {e}")
    
    # Summary
    print(f"\n\nSUMMARY - REASONS FOR SYNTHETIC DATA:")
    print("=" * 50)
    if reasons:
        for i, reason in enumerate(reasons, 1):
            print(f"{i}. {reason}")
    else:
        print("No obvious issues found - APIs should work")
        
    print("\nLikely causes:")
    print("- Network timeouts to ERDDAP servers")
    print("- API rate limiting")
    print("- Incorrect query date ranges")
    print("- Missing datasets at requested coordinates")
    print("- Fallback logic triggering too quickly")

if __name__ == "__main__":
    test_basic_erddap()
    test_specific_query()
    test_why_synthetic()