#!/usr/bin/env python3
"""
Batch download script for comprehensive SST texture dataset.
Handles large date ranges efficiently with resume capability.
"""

import sys
import logging
import time
from datetime import date, datetime, timedelta
from pathlib import Path
import argparse
import json
import signal

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

from downloaders.sst_erddap_texture_downloader import SSTERDDAPTextureDownloader

class BatchDownloadManager:
    """Manages large-scale batch downloads with resume capability."""
    
    def __init__(self, output_dir: Path = None):
        self.downloader = SSTERDDAPTextureDownloader(output_dir)
        self.logger = logging.getLogger(__name__)
        self.interrupted = False
        
        # Set up interrupt handler
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle interrupt signals gracefully."""
        self.logger.info(f"Received signal {signum}, finishing current download...")
        self.interrupted = True
        
    def download_with_resume(self, start_date: date, end_date: date, 
                           batch_size: int = 10, delay_seconds: float = 2.0) -> dict:
        """
        Download date range with resume capability and rate limiting.
        
        Args:
            start_date: Start date
            end_date: End date  
            batch_size: Number of files to download before saving progress
            delay_seconds: Delay between downloads to avoid overwhelming server
            
        Returns:
            Download results
        """
        progress_file = Path("/tmp/sst_batch_download_progress.json")
        
        # Load existing progress
        completed_dates = set()
        if progress_file.exists():
            try:
                with open(progress_file, 'r') as f:
                    progress_data = json.load(f)
                    completed_dates = set(progress_data.get('completed_dates', []))
                    self.logger.info(f"Resuming download, {len(completed_dates)} files already completed")
            except Exception as e:
                self.logger.warning(f"Could not load progress file: {e}")
                
        # Generate date list
        current_date = start_date
        all_dates = []
        while current_date <= end_date:
            if current_date.strftime('%Y-%m-%d') not in completed_dates:
                all_dates.append(current_date)
            current_date += timedelta(days=1)
            
        if not all_dates:
            self.logger.info("All files already downloaded!")
            return {'total_requested': 0, 'successful': 0, 'failed': 0, 'errors': []}
            
        self.logger.info(f"Downloading {len(all_dates)} remaining files from {start_date} to {end_date}")
        
        results = {
            'total_requested': len(all_dates),
            'successful': 0,
            'failed': 0,
            'errors': [],
            'start_time': datetime.now().isoformat(),
        }
        
        batch_count = 0
        for i, target_date in enumerate(all_dates):
            if self.interrupted:
                self.logger.info("Download interrupted by user")
                break
                
            try:
                self.logger.info(f"Downloading {i+1}/{len(all_dates)}: {target_date}")
                
                # Download texture
                success = self.downloader.download_texture_for_date(target_date)
                
                if success:
                    results['successful'] += 1
                    completed_dates.add(target_date.strftime('%Y-%m-%d'))
                    self.logger.info(f"✅ Downloaded {target_date}")
                else:
                    results['failed'] += 1
                    results['errors'].append(f"Failed to download {target_date}")
                    self.logger.error(f"❌ Failed {target_date}")
                
                # Save progress every batch_size downloads
                batch_count += 1
                if batch_count >= batch_size:
                    self._save_progress(progress_file, completed_dates, results)
                    batch_count = 0
                    
                # Rate limiting - delay between downloads
                if delay_seconds > 0 and i < len(all_dates) - 1:
                    time.sleep(delay_seconds)
                    
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"Exception downloading {target_date}: {e}")
                self.logger.error(f"Exception downloading {target_date}: {e}")
                
        # Final progress save
        results['end_time'] = datetime.now().isoformat()
        self._save_progress(progress_file, completed_dates, results)
        
        # Calculate performance stats
        if 'start_time' in results and 'end_time' in results:
            start_time = datetime.fromisoformat(results['start_time'])
            end_time = datetime.fromisoformat(results['end_time'])
            duration = end_time - start_time
            results['duration_minutes'] = duration.total_seconds() / 60
            results['average_seconds_per_file'] = duration.total_seconds() / max(results['successful'], 1)
            
        self.logger.info(
            f"Batch download complete: {results['successful']} successful, "
            f"{results['failed']} failed out of {results['total_requested']} requested"
        )
        
        return results
        
    def _save_progress(self, progress_file: Path, completed_dates: set, results: dict):
        """Save download progress to file."""
        try:
            progress_data = {
                'completed_dates': list(completed_dates),
                'last_update': datetime.now().isoformat(),
                'results': results
            }
            with open(progress_file, 'w') as f:
                json.dump(progress_data, f, indent=2)
            self.logger.debug(f"Progress saved: {len(completed_dates)} completed")
        except Exception as e:
            self.logger.warning(f"Could not save progress: {e}")
            
    def download_missing_dates(self, year: int) -> dict:
        """Download any missing dates for a specific year."""
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        
        # Don't go beyond current date
        if end_date > date.today():
            end_date = date.today() - timedelta(days=1)
            
        return self.download_with_resume(start_date, end_date)
        
    def estimate_download_time(self, start_date: date, end_date: date) -> dict:
        """Estimate download time for date range."""
        total_days = (end_date - start_date).days + 1
        
        # Based on observed performance: ~1-2 minutes per file
        avg_seconds_per_file = 90  # Conservative estimate
        total_seconds = total_days * avg_seconds_per_file
        
        return {
            'total_files': total_days,
            'estimated_hours': total_seconds / 3600,
            'estimated_size_gb': total_days * 11.6 / 1024,  # ~11.6MB per file
            'recommendation': 'Run overnight or in background' if total_seconds > 3600 else 'Can complete in current session'
        }

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Batch download SST textures with resume capability',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download complete 2024 data
  python batch_download_sst_textures.py --year 2024
  
  # Download specific date range
  python batch_download_sst_textures.py --start 2024-01-01 --end 2024-12-31
  
  # Estimate download time
  python batch_download_sst_textures.py --estimate --start 2023-01-01 --end 2024-12-31
  
  # Resume interrupted download
  python batch_download_sst_textures.py --resume
        """
    )
    
    parser.add_argument('--year', type=int, metavar='YYYY',
                       help='Download complete year of data')
    parser.add_argument('--start', type=str, metavar='YYYY-MM-DD',
                       help='Start date for download range')
    parser.add_argument('--end', type=str, metavar='YYYY-MM-DD',
                       help='End date for download range')
    parser.add_argument('--estimate', action='store_true',
                       help='Estimate download time without downloading')
    parser.add_argument('--resume', action='store_true',
                       help='Resume previous interrupted download')
    parser.add_argument('--batch-size', type=int, default=10,
                       help='Number of files to download before saving progress (default: 10)')
    parser.add_argument('--delay', type=float, default=2.0,
                       help='Delay in seconds between downloads (default: 2.0)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set up logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('/Volumes/Backup/panta-rhei-data-map/ocean-data/logs/sst_batch_download.log', 'a')
        ]
    )
    
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize batch manager
        manager = BatchDownloadManager()
        
        # Determine date range
        if args.resume:
            # Resume with previous parameters - user needs to specify again
            logger.info("Resume mode - please specify date range with --start and --end")
            return 1
            
        elif args.year:
            start_date = date(args.year, 1, 1)
            end_date = date(args.year, 12, 31)
            if end_date > date.today():
                end_date = date.today() - timedelta(days=1)
                
        elif args.start and args.end:
            start_date = datetime.strptime(args.start, '%Y-%m-%d').date()
            end_date = datetime.strptime(args.end, '%Y-%m-%d').date()
            
        else:
            parser.print_help()
            return 1
            
        # Handle estimation
        if args.estimate:
            estimate = manager.estimate_download_time(start_date, end_date)
            print(f"\n=== Download Estimation ===")
            print(f"Date range: {start_date} to {end_date}")
            print(f"Total files: {estimate['total_files']}")
            print(f"Estimated time: {estimate['estimated_hours']:.1f} hours")
            print(f"Estimated size: {estimate['estimated_size_gb']:.1f} GB")
            print(f"Recommendation: {estimate['recommendation']}")
            return 0
            
        # Start batch download
        logger.info(f"Starting batch download: {start_date} to {end_date}")
        results = manager.download_with_resume(start_date, end_date, args.batch_size, args.delay)
        
        # Print results
        print(f"\n=== Batch Download Results ===")
        print(f"Total requested: {results['total_requested']}")
        print(f"Successful: {results['successful']}")
        print(f"Failed: {results['failed']}")
        
        if 'duration_minutes' in results:
            print(f"Duration: {results['duration_minutes']:.1f} minutes")
            print(f"Average: {results['average_seconds_per_file']:.1f} seconds per file")
            
        if results['errors']:
            print(f"\nErrors ({len(results['errors'])}):")
            for error in results['errors'][:10]:  # Show first 10
                print(f"  - {error}")
                
        return 0 if results['failed'] == 0 else 1
        
    except KeyboardInterrupt:
        logger.info("Download interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())