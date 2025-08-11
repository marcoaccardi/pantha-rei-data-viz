#!/usr/bin/env python3
"""
Direct CMEMS currents downloader bypassing hybrid system.
Downloads CMEMS currents data directly without OSCAR dependencies.
"""

import sys
from pathlib import Path
from datetime import date, datetime, timedelta
import logging

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

from downloaders.currents_downloader import CurrentsDownloader

def main():
    """Download recent CMEMS currents data."""
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    print("🎯 Direct CMEMS Currents Download")
    print("=" * 40)
    
    try:
        # Initialize CMEMS downloader directly
        downloader = CurrentsDownloader()
        
        # Download yesterday's data
        target_date = date.today() - timedelta(days=1)
        print(f"📅 Downloading CMEMS data for: {target_date}")
        
        success = downloader.download_date(target_date)
        
        if success:
            print(f"✅ Successfully downloaded CMEMS currents data for {target_date}")
            return True
        else:
            print(f"❌ Failed to download CMEMS currents data for {target_date}")
            return False
            
    except Exception as e:
        print(f"❌ Error during download: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)