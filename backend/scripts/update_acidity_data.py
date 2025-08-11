#!/usr/bin/env python3
"""
Ocean Acidity Data Update Script
Downloads yesterday's ocean acidity data for processing.
"""

import sys
import argparse
from datetime import date, timedelta
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

from downloaders.acidity_hybrid_downloader import AcidityHybridDownloader

def main():
    """Download ocean acidity data."""
    parser = argparse.ArgumentParser(description='Download ocean acidity data')
    parser.add_argument('--yesterday', action='store_true',
                       help='Download yesterday\'s data')
    parser.add_argument('--date', type=str,
                       help='Download specific date (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    # Determine target date
    if args.yesterday:
        target_date = date.today() - timedelta(days=1)
    elif args.date:
        from datetime import datetime
        target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
    else:
        target_date = date.today() - timedelta(days=1)  # Default to yesterday
    
    print(f"🧪 Downloading ocean acidity data for {target_date}")
    
    try:
        downloader = AcidityHybridDownloader()
        success = downloader.download_date(target_date)
        
        if success:
            print(f"✅ Successfully downloaded acidity data for {target_date}")
            return 0
        else:
            print(f"❌ Failed to download acidity data for {target_date}")
            return 1
            
    except Exception as e:
        print(f"❌ Error downloading acidity data: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())