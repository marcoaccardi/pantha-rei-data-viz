#!/usr/bin/env python3
"""
Download missing CMEMS currents data to complete the coverage from 2023-2025.
Focuses on filling gaps identified after OSCAR organization.
"""

import sys
from pathlib import Path
from datetime import date, datetime, timedelta
import logging

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

from downloaders.currents_downloader import CurrentsDownloader

def analyze_missing_dates():
    """Analyze what CMEMS currents data is missing."""
    
    currents_dir = Path("/Volumes/Backup/panta-rhei-data-map/ocean-data/raw/currents")
    
    # Define the period we need to check
    start_date = date(2023, 6, 5)  # The 1-day gap
    end_date = date(2025, 7, 28)   # Current date
    
    missing_dates = []
    existing_count = 0
    
    current_date = start_date
    while current_date <= end_date:
        year_dir = currents_dir / str(current_date.year)
        month_dir = year_dir / f"{current_date.month:02d}"
        
        # Check for CMEMS file (pattern: currents_global_YYYYMMDD.nc)
        cmems_file = month_dir / f"currents_global_{current_date.strftime('%Y%m%d')}.nc"
        
        # Check for OSCAR file (shouldn't exist after June 4, but check anyway)
        oscar_file = month_dir / f"oscar_currents_final_{current_date.strftime('%Y%m%d')}.nc4"
        
        if not cmems_file.exists() and not oscar_file.exists():
            missing_dates.append(current_date)
        else:
            existing_count += 1
            
        current_date += timedelta(days=1)
    
    total_days = (end_date - start_date).days + 1
    missing_count = len(missing_dates)
    
    print(f"📊 Missing CMEMS Data Analysis:")
    print(f"   Period analyzed: {start_date} to {end_date}")
    print(f"   Total days: {total_days}")
    print(f"   Existing files: {existing_count}")
    print(f"   Missing files: {missing_count}")
    print(f"   Coverage: {100 * existing_count / total_days:.1f}%")
    
    return missing_dates

def download_missing_data(missing_dates, max_downloads=50):
    """Download missing CMEMS currents data."""
    
    if not missing_dates:
        print("✅ No missing data to download!")
        return True
    
    print(f"\n🚀 Downloading {min(len(missing_dates), max_downloads)} missing files...")
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Initialize CMEMS downloader with specific configuration
        from downloaders.base_downloader import BaseDataDownloader
        
        # Create a temporary downloader that uses currents_cmems config
        class TempCmemsDownloader(BaseDataDownloader):
            def __init__(self):
                super().__init__("currents_cmems")
                
        temp_downloader = TempCmemsDownloader()
        
        # Use the CMEMS downloader 
        downloader = CurrentsDownloader()
        
        # Override the specific config fields needed
        downloader.product_id = temp_downloader.dataset_config["product_id"]
        downloader.dataset_id = temp_downloader.dataset_config["dataset_id"]
        
        # Download in chronological order
        missing_dates.sort()
        
        downloaded = 0
        failed = 0
        skipped = 0
        
        for i, missing_date in enumerate(missing_dates[:max_downloads], 1):
            try:
                print(f"\n[{i}/{min(len(missing_dates), max_downloads)}] Downloading {missing_date}...")
                
                result = downloader.download_for_date(missing_date)
                
                if result.get('success', False):
                    if result.get('skipped', False):
                        print(f"   ⏭️  Skipped (already exists)")
                        skipped += 1
                    else:
                        print(f"   ✅ Downloaded successfully")
                        downloaded += 1
                else:
                    print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")
                    failed += 1
                    
            except Exception as e:
                print(f"   ❌ Exception: {e}")
                failed += 1
        
        print(f"\n📈 Download Results:")
        print(f"   Downloaded: {downloaded}")
        print(f"   Skipped: {skipped}")
        print(f"   Failed: {failed}")
        print(f"   Success rate: {100 * (downloaded + skipped) / (downloaded + skipped + failed):.1f}%")
        
        return failed == 0
        
    except Exception as e:
        print(f"❌ Error initializing downloader: {e}")
        return False

def main():
    """Main function to analyze and download missing data."""
    
    print("🔍 Analyzing missing CMEMS currents data...")
    missing_dates = analyze_missing_dates()
    
    if not missing_dates:
        print("✅ All data is already available!")
        return True
    
    # Show sample of missing dates
    print(f"\n📅 Sample missing dates:")
    for date_sample in missing_dates[:10]:
        print(f"   - {date_sample}")
    if len(missing_dates) > 10:
        print(f"   ... and {len(missing_dates) - 10} more")
    
    # Ask about download strategy
    print(f"\nRecommended approach:")
    print(f"1. Start with critical gap (2023-06-05): 1 file")
    print(f"2. Fill 2023 remainder (Jun-Dec): ~180 files") 
    print(f"3. Complete 2024: ~365 files")
    print(f"4. Complete 2025 to date: ~200 files")
    print(f"Total estimated: ~746 files")
    
    # Download priority dates first (recent months)
    priority_dates = [d for d in missing_dates if d >= date(2024, 6, 1)]  # Last 13+ months
    
    print(f"\n🎯 Starting with recent priority period: {len(priority_dates)} files")
    
    success = download_missing_data(priority_dates, max_downloads=20)  # Start conservative
    
    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)