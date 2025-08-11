#!/usr/bin/env python3
"""
Download missing SST data from August 2024 onwards.
Bulk download script for filling data gaps.
"""

import sys
import os
sys.path.append('/Volumes/Backup/panta-rhei-data-map/backend')

from downloaders.sst_downloader import SSTDownloader
from datetime import datetime, timedelta, date
import logging

def main():
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    # Initialize downloader
    downloader = SSTDownloader()

    # Download from August 1, 2024 onwards (or resume from where we left off)
    start_date = date(2024, 8, 1)
    end_date = date.today() - timedelta(days=3)  # Skip last 3 days as they might not be available

    # Check existing files to determine resume point
    raw_path = "/Volumes/Backup/panta-rhei-data-map/ocean-data/raw/sst"
    existing_files = []
    
    for root, dirs, files in os.walk(raw_path):
        for file in files:
            if file.startswith("oisst-avhrr-v02r01.2024") or file.startswith("oisst-avhrr-v02r01.2025"):
                date_str = file.split('.')[1]
                if len(date_str) == 8:
                    existing_files.append(date_str)
    
    existing_files.sort()
    logger.info(f"Found {len(existing_files)} existing SST files from 2024-2025")
    
    if existing_files:
        latest_existing = datetime.strptime(existing_files[-1], '%Y%m%d').date()
        if latest_existing >= start_date:
            start_date = latest_existing + timedelta(days=1)
            logger.info(f"Resuming download from {start_date}")

    current_date = start_date
    success_count = 0
    fail_count = 0
    skip_count = 0

    logger.info(f'Starting SST bulk download from {start_date} to {end_date}')
    logger.info(f'Expected files to download: {(end_date - start_date).days + 1}')

    while current_date <= end_date:
        date_str = current_date.strftime('%Y%m%d')
        
        # Check if file already exists
        if date_str in existing_files:
            skip_count += 1
            current_date += timedelta(days=1)
            continue
            
        try:
            result = downloader.download_date(current_date)
            if result:
                success_count += 1
                if success_count % 25 == 0:
                    logger.info(f'Progress: {success_count} downloaded, {fail_count} failed, {skip_count} skipped')
            else:
                fail_count += 1
                logger.warning(f'Failed to download {current_date}')
                
        except Exception as e:
            logger.error(f'Exception downloading {current_date}: {e}')
            fail_count += 1
        
        current_date += timedelta(days=1)

    logger.info(f'SST bulk download complete!')
    logger.info(f'Results: {success_count} successful, {fail_count} failed, {skip_count} skipped')
    logger.info(f'Total new files: {success_count}')

if __name__ == "__main__":
    main()