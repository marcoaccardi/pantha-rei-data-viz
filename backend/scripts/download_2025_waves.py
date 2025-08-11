#!/usr/bin/env python3
"""
Download all 2025 waves data systematically.
This script downloads waves data month by month for 2025.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from downloaders.waves_downloader import WavesDownloader
from datetime import date, timedelta
import logging
import time

def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def download_month(downloader, year, month):
    """Download all days for a specific month."""
    print(f"\n📅 Downloading {year}-{month:02d}")
    print("-" * 40)
    
    # Get first and last day of month
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    
    # Don't download future dates
    today = date.today()
    if last_day > today:
        last_day = today
    
    if first_day > today:
        print(f"⏭️  Skipping future month {year}-{month:02d}")
        return {'success': 0, 'failed': 0, 'skipped': 0}
    
    current_date = first_day
    success_count = 0
    failed_count = 0
    
    while current_date <= last_day:
        try:
            print(f"  {current_date}: ", end="", flush=True)
            
            # Check if file already exists and is valid
            year_month = current_date.strftime("%Y/%m")
            filename = f"waves_global_{current_date.strftime('%Y%m%d')}.nc"
            raw_file = Path(f"/Volumes/Backup/panta-rhei-data-map/ocean-data/raw/waves/{year_month}/{filename}")
            
            if raw_file.exists() and raw_file.stat().st_size > 1000000:  # > 1MB
                print("✅ exists")
                success_count += 1
            else:
                success = downloader.download_date(current_date)
                if success:
                    print("✅ downloaded")
                    success_count += 1
                else:
                    print("❌ failed")
                    failed_count += 1
                    
        except Exception as e:
            print(f"❌ error: {e}")
            failed_count += 1
        
        current_date += timedelta(days=1)
        time.sleep(0.5)  # Small delay to avoid overwhelming the server
    
    print(f"\n📊 Month {year}-{month:02d} Summary:")
    print(f"  ✅ Success: {success_count}")
    print(f"  ❌ Failed: {failed_count}")
    
    return {'success': success_count, 'failed': failed_count}

def main():
    """Main download function."""
    setup_logging()
    
    print("🌊 Downloading All 2025 Waves Data")
    print("=" * 50)
    
    # Initialize downloader
    try:
        downloader = WavesDownloader()
        print("✅ Initialized waves downloader")
    except Exception as e:
        print(f"❌ Failed to initialize downloader: {e}")
        return
    
    # Download each month of 2025
    year = 2025
    total_success = 0
    total_failed = 0
    
    for month in range(1, 13):  # January to December
        try:
            result = download_month(downloader, year, month)
            total_success += result['success']
            total_failed += result['failed']
            
            # Brief pause between months
            time.sleep(2)
            
        except KeyboardInterrupt:
            print("\n⏹️  Download interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ Error downloading month {year}-{month:02d}: {e}")
            total_failed += 1
    
    # Final summary
    print("\n" + "=" * 50)
    print("📊 FINAL DOWNLOAD SUMMARY")
    print("=" * 50)
    print(f"✅ Total successful downloads: {total_success}")
    print(f"❌ Total failed downloads: {total_failed}")
    print(f"📈 Success rate: {total_success/(total_success+total_failed)*100:.1f}%" if (total_success + total_failed) > 0 else "No downloads attempted")
    
    # Check final file count
    import subprocess
    try:
        result = subprocess.run(
            ["find", "/Volumes/Backup/panta-rhei-data-map/ocean-data/raw/waves/2025", "-name", "*.nc", "-type", "f"],
            capture_output=True, text=True
        )
        file_count = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
        print(f"📁 Total 2025 wave files: {file_count}")
        
        # Expected days in 2025 up to today
        days_in_2025 = (date.today() - date(2025, 1, 1)).days + 1
        print(f"📅 Expected files (Jan 1 - today): {days_in_2025}")
        print(f"📊 Coverage: {file_count/days_in_2025*100:.1f}%")
        
    except Exception as e:
        print(f"⚠️  Could not count files: {e}")

if __name__ == "__main__":
    main()