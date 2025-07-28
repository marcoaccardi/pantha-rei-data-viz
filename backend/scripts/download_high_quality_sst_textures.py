#!/usr/bin/env python3
"""
Download high-quality SST textures using PacIOOS ERDDAP transparentPng service.
This script provides the same professional-grade texture quality as the Corals project.
"""

import sys
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
import argparse

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

from downloaders.sst_erddap_texture_downloader import SSTERDDAPTextureDownloader

def setup_logging(verbose: bool = False):
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('/Volumes/Backup/panta-rhei-data-map/ocean-data/logs/sst_texture_download.log', 'a')
        ]
    )

def main():
    """Main script function."""
    parser = argparse.ArgumentParser(
        description='Download high-quality SST textures from PacIOOS ERDDAP',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download recent 30 days of textures
  python download_high_quality_sst_textures.py --recent 30
  
  # Download specific date range
  python download_high_quality_sst_textures.py --start 2024-01-01 --end 2024-01-31
  
  # Download single date
  python download_high_quality_sst_textures.py --date 2024-07-28
  
  # Show availability information
  python download_high_quality_sst_textures.py --info
        """
    )
    
    parser.add_argument('--recent', type=int, metavar='DAYS',
                       help='Download recent N days of textures')
    parser.add_argument('--start', type=str, metavar='YYYY-MM-DD',
                       help='Start date for download range')
    parser.add_argument('--end', type=str, metavar='YYYY-MM-DD',
                       help='End date for download range')
    parser.add_argument('--date', type=str, metavar='YYYY-MM-DD',
                       help='Download texture for specific date')
    parser.add_argument('--info', action='store_true',
                       help='Show information about available textures')
    parser.add_argument('--cleanup', type=int, metavar='DAYS',
                       help='Clean up textures older than N days')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--output-dir', type=str,
                       help='Custom output directory for textures')
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Initialize downloader
    try:
        output_dir = Path(args.output_dir) if args.output_dir else None
        downloader = SSTERDDAPTextureDownloader(output_dir)
        logger.info("Initialized ERDDAP SST texture downloader")
        
    except Exception as e:
        logger.error(f"Failed to initialize downloader: {e}")
        return 1
    
    # Handle different operations
    try:
        if args.info:
            # Show texture availability information
            info = downloader.get_available_textures()
            print(f"\n=== SST Texture Availability ===")
            print(f"Total files: {info['total_files']}")
            print(f"Total size: {info['total_size_mb']} MB")
            
            if info['date_range']:
                print(f"Date range: {info['date_range']['start']} to {info['date_range']['end']}")
                print(f"Years available: {', '.join(map(str, info['years_available']))}")
            else:
                print("No textures found")
                
        elif args.cleanup:
            # Clean up old textures
            logger.info(f"Cleaning up textures older than {args.cleanup} days")
            results = downloader.cleanup_old_textures(args.cleanup)
            
            print(f"\n=== Cleanup Results ===")
            print(f"Files checked: {results['files_checked']}")
            print(f"Files removed: {results['files_removed']}")
            print(f"Space freed: {results['space_freed_mb']} MB")
            
            if results['errors']:
                print(f"Errors: {len(results['errors'])}")
                for error in results['errors'][:5]:  # Show first 5 errors
                    logger.warning(error)
                    
        elif args.recent:
            # Download recent textures
            logger.info(f"Downloading recent {args.recent} days of SST textures")
            results = downloader.download_recent_textures(args.recent)
            
            print(f"\n=== Download Results ===")
            print(f"Requested: {results['total_requested']}")
            print(f"Successful: {results['successful']}")
            print(f"Failed: {results['failed']}")
            
            if results['errors']:
                print(f"\nErrors ({len(results['errors'])}):")
                for error in results['errors'][:10]:  # Show first 10 errors
                    print(f"  - {error}")
                    
        elif args.start and args.end:
            # Download date range
            try:
                start_date = datetime.strptime(args.start, '%Y-%m-%d').date()
                end_date = datetime.strptime(args.end, '%Y-%m-%d').date()
                
                logger.info(f"Downloading SST textures from {start_date} to {end_date}")
                results = downloader.download_date_range(start_date, end_date)
                
                print(f"\n=== Download Results ===")
                print(f"Requested: {results['total_requested']}")
                print(f"Successful: {results['successful']}")
                print(f"Failed: {results['failed']}")
                
                if results['errors']:
                    print(f"\nErrors ({len(results['errors'])}):")
                    for error in results['errors'][:10]:
                        print(f"  - {error}")
                        
            except ValueError as e:
                logger.error(f"Invalid date format: {e}")
                return 1
                
        elif args.date:
            # Download single date
            try:
                target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
                
                logger.info(f"Downloading SST texture for {target_date}")
                success = downloader.download_texture_for_date(target_date)
                
                if success:
                    print(f"✅ Successfully downloaded texture for {target_date}")
                else:
                    print(f"❌ Failed to download texture for {target_date}")
                    return 1
                    
            except ValueError as e:
                logger.error(f"Invalid date format: {e}")
                return 1
                
        else:
            # No specific operation requested - show help and download today
            parser.print_help()
            print(f"\nNo operation specified. Downloading texture for today...")
            
            today = date.today() - timedelta(days=1)  # Yesterday (accounting for processing delay)
            success = downloader.download_texture_for_date(today)
            
            if success:
                print(f"✅ Successfully downloaded texture for {today}")
            else:
                print(f"❌ Failed to download texture for {today}")
                return 1
                
    except KeyboardInterrupt:
        logger.info("Download interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1
    
    logger.info("SST texture download operation completed")
    return 0

if __name__ == '__main__':
    sys.exit(main())