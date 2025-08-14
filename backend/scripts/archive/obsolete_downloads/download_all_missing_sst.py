#!/usr/bin/env python3
"""
Download all missing SST data based on texture gaps analysis.
This script identifies missing texture files and downloads the corresponding raw data.
"""

import sys
import os
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from downloaders.sst_downloader import SSTDownloader
from datetime import datetime, timedelta, date
import logging

def find_missing_dates():
    """Find all missing texture dates from 2003-2025"""
    texture_base = "../ocean-data/textures/sst"
    missing_dates = []
    
    for year in range(2003, 2026):
        year_dir = os.path.join(texture_base, str(year))
        if not os.path.exists(year_dir):
            continue
        
        start_date = datetime(year, 1, 1)
        if year == 2025:
            end_date = datetime(2025, 8, 4)  # Current date
        else:
            end_date = datetime(year, 12, 31)
        
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime('%Y%m%d')
            texture_file = os.path.join(year_dir, f'SST_{date_str}.png')
            
            if not os.path.exists(texture_file):
                missing_dates.append(current_date.date())
            
            current_date += timedelta(days=1)
    
    return missing_dates

def check_existing_raw_data(missing_dates):
    """Check which missing dates already have raw data"""
    raw_path = "../ocean-data/raw/sst"
    
    need_download = []
    have_raw = []
    
    for missing_date in missing_dates:
        date_str = missing_date.strftime('%Y%m%d')
        
        # Check for raw file existence
        found_raw = False
        for root, dirs, files in os.walk(raw_path):
            for file in files:
                if date_str in file and file.endswith('.nc'):
                    found_raw = True
                    break
            if found_raw:
                break
        
        if found_raw:
            have_raw.append(missing_date)
        else:
            need_download.append(missing_date)
    
    return need_download, have_raw

def main():
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    logger.info("Finding missing texture dates...")
    missing_dates = find_missing_dates()
    logger.info(f"Found {len(missing_dates)} missing texture dates")
    
    logger.info("Checking existing raw data...")
    need_download, have_raw = check_existing_raw_data(missing_dates)
    
    logger.info(f"Summary:")
    logger.info(f"  Total missing textures: {len(missing_dates)}")
    logger.info(f"  Have raw data (need texture generation): {len(have_raw)}")
    logger.info(f"  Need to download: {len(need_download)}")
    
    if not need_download:
        logger.info("No downloads needed! All missing textures have raw data available.")
        logger.info("Run texture generation script to create missing textures.")
        return
    
    # Initialize downloader
    downloader = SSTDownloader()
    
    success_count = 0
    fail_count = 0
    
    logger.info(f'Starting SST download for {len(need_download)} missing dates')
    
    for i, download_date in enumerate(need_download, 1):
        try:
            logger.info(f"Downloading {download_date} ({i}/{len(need_download)})")
            result = downloader.download_date(download_date)
            
            if result:
                success_count += 1
                if success_count % 10 == 0:
                    logger.info(f'Progress: {success_count}/{len(need_download)} downloaded, {fail_count} failed')
            else:
                fail_count += 1
                logger.warning(f'Failed to download {download_date}')
                
        except Exception as e:
            logger.error(f'Exception downloading {download_date}: {e}')
            fail_count += 1
    
    logger.info(f'Download complete!')
    logger.info(f'Results: {success_count} successful, {fail_count} failed')
    logger.info(f'Next step: Run texture generation for all {len(missing_dates)} missing textures')

if __name__ == "__main__":
    main()