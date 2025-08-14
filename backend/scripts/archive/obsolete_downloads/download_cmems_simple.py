#!/usr/bin/env python3
"""
Simple CMEMS currents downloader to fill gaps in 2023-2025.
Uses currents_cmems configuration directly.
"""

import sys
from pathlib import Path
from datetime import date, datetime, timedelta
import logging

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

def download_cmems_date_range(start_date, end_date, max_files=10):
    """Download CMEMS data for a date range using the hybrid downloader."""
    
    print(f"🚀 Downloading CMEMS data from {start_date} to {end_date}")
    print(f"   Max files: {max_files}")
    
    try:
        from downloaders.currents_hybrid_downloader import CurrentsHybridDownloader
        
        # Initialize hybrid downloader (it knows how to route to CMEMS)
        downloader = CurrentsHybridDownloader()
        
        # Use the hybrid downloader's date range method
        result = downloader.download_date_range(
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            max_files=max_files
        )
        
        print(f"\n📈 Download Results:")
        print(f"   Downloaded: {result.get('downloaded', 0)}")
        print(f"   Skipped: {result.get('skipped', 0)}")
        print(f"   Failed: {result.get('failed', 0)}")
        
        if result.get('errors'):
            print(f"\n❌ Errors encountered:")
            for error in result['errors'][:5]:  # Show first 5 errors
                print(f"   - {error}")
        
        success_rate = result.get('summary', {}).get('success_rate', 0)
        print(f"   Success rate: {success_rate * 100:.1f}%")
        
        return result.get('downloaded', 0) > 0 or result.get('skipped', 0) > 0
        
    except Exception as e:
        print(f"❌ Error during download: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function to download critical missing data."""
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    print("🎯 CMEMS Currents Gap Filling")
    print("=" * 40)
    
    # Priority 1: Critical 1-day gap
    gap_date = date(2023, 6, 5)
    print(f"\n1️⃣ Filling critical 1-day gap: {gap_date}")
    success1 = download_cmems_date_range(gap_date, gap_date, max_files=1)
    
    # Priority 2: Recent 2025 data (last 30 days)
    end_date = date(2025, 7, 28)
    start_date = end_date - timedelta(days=30)
    print(f"\n2️⃣ Downloading recent 2025 data: {start_date} to {end_date}")
    success2 = download_cmems_date_range(start_date, end_date, max_files=10)
    
    # Priority 3: 2024 Q4 (last quarter of 2024)
    q4_start = date(2024, 10, 1)
    q4_end = date(2024, 12, 31)
    print(f"\n3️⃣ Downloading 2024 Q4: {q4_start} to {q4_end}")
    success3 = download_cmems_date_range(q4_start, q4_end, max_files=15)
    
    print(f"\n✅ Summary:")
    print(f"   Gap fill: {'✅' if success1 else '❌'}")
    print(f"   Recent 2025: {'✅' if success2 else '❌'}")
    print(f"   2024 Q4: {'✅' if success3 else '❌'}")
    
    return success1 or success2 or success3

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)