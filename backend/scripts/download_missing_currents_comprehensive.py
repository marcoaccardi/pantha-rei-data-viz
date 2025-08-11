#!/usr/bin/env python3
"""
Comprehensive CMEMS currents data downloader.
Downloads all missing CMEMS currents data to complete coverage from 2023-06-05 to present.
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
    
    # Define the period we need to check (post-OSCAR gap)
    start_date = date(2023, 6, 5)  # Start of CMEMS coverage needed
    end_date = date.today() - timedelta(days=1)  # Yesterday
    
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
    
    print(f"📊 CMEMS Currents Coverage Analysis:")
    print(f"   Period: {start_date} to {end_date}")
    print(f"   Total days: {total_days}")
    print(f"   Existing files: {existing_count}")
    print(f"   Missing files: {missing_count}")
    print(f"   Coverage: {100 * existing_count / total_days:.1f}%")
    print()
    
    return missing_dates, existing_count, total_days

def download_missing_data(missing_dates, batch_size=25):
    """Download missing CMEMS currents data in batches."""
    
    if not missing_dates:
        print("✅ No missing data to download!")
        return True
    
    print(f"🚀 Downloading {len(missing_dates)} missing files in batches of {batch_size}...")
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Initialize CMEMS downloader directly
        downloader = CurrentsDownloader()
        
        total_downloaded = 0
        total_failed = 0
        
        # Process in batches to avoid overwhelming the system
        for i in range(0, len(missing_dates), batch_size):
            batch = missing_dates[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(missing_dates) + batch_size - 1) // batch_size
            
            print(f"\n📦 Batch {batch_num}/{total_batches}: {len(batch)} files")
            print(f"   Date range: {batch[0]} to {batch[-1]}")
            
            batch_downloaded = 0
            batch_failed = 0
            
            for target_date in batch:
                try:
                    print(f"   📅 Downloading {target_date}...", end=" ")
                    success = downloader.download_date(target_date)
                    
                    if success:
                        print("✅")
                        batch_downloaded += 1
                        total_downloaded += 1
                    else:
                        print("❌")
                        batch_failed += 1
                        total_failed += 1
                        
                except Exception as e:
                    print(f"❌ ({str(e)[:50]}...)")
                    batch_failed += 1
                    total_failed += 1
            
            print(f"   Batch results: {batch_downloaded} downloaded, {batch_failed} failed")
            
            # Brief pause between batches
            if i + batch_size < len(missing_dates):
                print("   ⏳ Brief pause before next batch...")
                import time
                time.sleep(2)
        
        print(f"\n📈 Final Results:")
        print(f"   Total downloaded: {total_downloaded}")
        print(f"   Total failed: {total_failed}")
        print(f"   Success rate: {100 * total_downloaded / len(missing_dates):.1f}%")
        
        return total_downloaded > 0
        
    except Exception as e:
        print(f"❌ Error during download: {e}")
        import traceback
        traceback.print_exc()
        return False

def prioritize_dates(missing_dates):
    """Prioritize missing dates - recent dates first, then critical gap."""
    
    # Critical gap (just after OSCAR ends)
    critical_start = date(2023, 6, 5)
    critical_end = date(2023, 6, 30)
    
    # Recent data (last 60 days)
    recent_start = date.today() - timedelta(days=60)
    
    critical_dates = [d for d in missing_dates if critical_start <= d <= critical_end]
    recent_dates = [d for d in missing_dates if d >= recent_start]
    other_dates = [d for d in missing_dates if d < recent_start and d not in critical_dates]
    
    # Prioritize: recent, then critical, then others
    prioritized = recent_dates + critical_dates + other_dates
    
    # Remove duplicates while preserving order
    seen = set()
    unique_prioritized = []
    for d in prioritized:
        if d not in seen:
            seen.add(d)
            unique_prioritized.append(d)
    
    print(f"📋 Download Priority:")
    print(f"   Recent dates (last 60 days): {len(recent_dates)}")
    print(f"   Critical gap dates: {len(critical_dates)}")
    print(f"   Other historical dates: {len(other_dates)}")
    
    return unique_prioritized

def main():
    """Main function to download all missing currents data."""
    
    print("🌊 Comprehensive CMEMS Currents Data Download")
    print("=" * 50)
    
    # Step 1: Analyze current coverage
    missing_dates, existing_count, total_days = analyze_missing_dates()
    
    if not missing_dates:
        print("🎉 All currents data is already downloaded!")
        return True
    
    # Step 2: Prioritize dates
    prioritized_dates = prioritize_dates(missing_dates)
    
    # Step 3: Download missing data
    success = download_missing_data(prioritized_dates)
    
    # Step 4: Final analysis
    print(f"\n🔍 Re-analyzing coverage...")
    final_missing, final_existing, final_total = analyze_missing_dates()
    
    improvement = len(missing_dates) - len(final_missing)
    print(f"📈 Improvement: Downloaded {improvement} new files")
    
    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)