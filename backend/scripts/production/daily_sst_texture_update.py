#!/usr/bin/env python3
"""
Daily SST texture update script.
Downloads yesterday's SST texture and maintains the dataset.
Designed to run as a daily cron job or scheduled task.
"""

import sys
import logging
import smtplib
from datetime import date, datetime, timedelta
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json

# Add backend to path (script is in scripts/production/, need to go up two levels to reach backend/)
sys.path.append(str(Path(__file__).parent.parent.parent))

from downloaders.sst_erddap_texture_downloader import SSTERDDAPTextureDownloader

class DailySSTPipelineError(Exception):
    """Custom exception for daily SST pipeline errors."""
    pass

class DailyTextureUpdater:
    """Handles daily SST texture updates with monitoring and alerts."""
    
    def __init__(self, max_retry_days: int = 3):
        """
        Initialize daily updater.
        
        Args:
            max_retry_days: Maximum days to retry failed downloads
        """
        self.downloader = SSTERDDAPTextureDownloader()
        self.logger = self._setup_logging()
        self.max_retry_days = max_retry_days
        
        # Status file for tracking
        self.status_file = Path("../ocean-data/logs/daily_sst_status.json")
        
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for daily updates."""
        log_file = Path("../ocean-data/logs/daily_sst_update.log")
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(log_file, 'a')
            ]
        )
        
        return logging.getLogger(__name__)
        
    def _load_status(self) -> dict:
        """Load status from previous runs."""
        if not self.status_file.exists():
            return {
                'last_successful_date': None,
                'failed_dates': [],
                'last_run': None,
                'consecutive_failures': 0
            }
            
        try:
            with open(self.status_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.warning(f"Could not load status file: {e}")
            return {
                'last_successful_date': None,
                'failed_dates': [],
                'last_run': None,
                'consecutive_failures': 0
            }
            
    def _save_status(self, status: dict):
        """Save status to file."""
        try:
            status['last_run'] = datetime.now().isoformat()
            with open(self.status_file, 'w') as f:
                json.dump(status, f, indent=2)
        except Exception as e:
            self.logger.error(f"Could not save status: {e}")
            
    def _determine_target_dates(self) -> list:
        """
        Determine which dates need to be downloaded.
        
        Returns:
            List of dates to attempt downloading
        """
        target_dates = []
        
        # Always try yesterday (most common case)
        yesterday = date.today() - timedelta(days=1)
        target_dates.append(yesterday)
        
        # Load status and add any recent failed dates
        status = self._load_status()
        failed_dates = status.get('failed_dates', [])
        
        # Retry recent failures (within max_retry_days)
        cutoff_date = date.today() - timedelta(days=self.max_retry_days)
        
        for date_str in failed_dates:
            try:
                failed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                if failed_date >= cutoff_date and failed_date not in target_dates:
                    target_dates.append(failed_date)
            except ValueError:
                continue
                
        # Sort dates (oldest first)
        target_dates.sort()
        
        return target_dates
        
    def run_daily_update(self) -> dict:
        """
        Run the daily texture update process.
        
        Returns:
            Dictionary with update results
        """
        self.logger.info("=== Starting Daily SST Texture Update ===")
        
        # Load previous status
        status = self._load_status()
        
        # Determine target dates
        target_dates = self._determine_target_dates()
        
        if not target_dates:
            self.logger.info("No dates to process")
            return {'success': True, 'processed': 0, 'failed': 0, 'message': 'No dates to process'}
            
        self.logger.info(f"Processing {len(target_dates)} dates: {[str(d) for d in target_dates]}")
        
        results = {
            'success': True,
            'processed': 0,
            'failed': 0,
            'successful_dates': [],
            'failed_dates': [],
            'errors': []
        }
        
        # Process each target date
        for target_date in target_dates:
            try:
                self.logger.info(f"Downloading texture for {target_date}")
                
                # Check if already exists
                texture_filename = f"SST_{target_date.strftime('%Y%m%d')}.png"
                year_dir = self.downloader.output_base_path / str(target_date.year)
                texture_path = year_dir / texture_filename
                
                if texture_path.exists():
                    # File exists, validate it
                    if self.downloader._validate_texture_image(texture_path):
                        self.logger.info(f"Texture already exists and is valid: {target_date}")
                        results['processed'] += 1
                        results['successful_dates'].append(str(target_date))
                        
                        # Remove from failed dates if present
                        if str(target_date) in status.get('failed_dates', []):
                            status['failed_dates'].remove(str(target_date))
                            
                        continue
                    else:
                        self.logger.warning(f"Existing texture is invalid, re-downloading: {target_date}")
                        texture_path.unlink()  # Remove invalid file
                
                # Download texture
                success = self.downloader.download_texture_for_date(target_date)
                
                if success:
                    results['processed'] += 1
                    results['successful_dates'].append(str(target_date))
                    status['last_successful_date'] = str(target_date)
                    status['consecutive_failures'] = 0
                    
                    # Remove from failed dates if present
                    failed_dates = status.get('failed_dates', [])
                    if str(target_date) in failed_dates:
                        failed_dates.remove(str(target_date))
                        status['failed_dates'] = failed_dates
                        
                    self.logger.info(f"✅ Successfully downloaded texture for {target_date}")
                    
                else:
                    results['failed'] += 1
                    results['failed_dates'].append(str(target_date))
                    
                    # Add to failed dates if not already present
                    failed_dates = status.get('failed_dates', [])
                    if str(target_date) not in failed_dates:
                        failed_dates.append(str(target_date))
                        status['failed_dates'] = failed_dates
                        
                    status['consecutive_failures'] = status.get('consecutive_failures', 0) + 1
                    
                    error_msg = f"Failed to download texture for {target_date}"
                    results['errors'].append(error_msg)
                    self.logger.error(f"❌ {error_msg}")
                    
            except Exception as e:
                results['failed'] += 1
                results['failed_dates'].append(str(target_date))
                status['consecutive_failures'] = status.get('consecutive_failures', 0) + 1
                
                error_msg = f"Exception processing {target_date}: {e}"
                results['errors'].append(error_msg)
                self.logger.error(error_msg)
                
        # Update overall status
        if results['failed'] > 0:
            results['success'] = False
            
        # Save status
        self._save_status(status)
        
        # Log summary
        self.logger.info(
            f"=== Daily Update Complete: {results['processed']} successful, "
            f"{results['failed']} failed ===")
            
        return results
        
    def check_dataset_health(self) -> dict:
        """
        Check the health of the SST texture dataset.
        
        Returns:
            Health status dictionary
        """
        health = {
            'healthy': True,
            'issues': [],
            'stats': {}
        }
        
        try:
            # Get availability info
            info = self.downloader.get_available_textures()
            health['stats'] = info
            
            # Check for recent data
            if info['total_files'] == 0:
                health['healthy'] = False
                health['issues'].append("No textures found")
            else:
                # Check if we have recent data (within last 7 days)
                if info['date_range']:
                    last_date = datetime.strptime(info['date_range']['end'], '%Y-%m-%d').date()
                    days_old = (date.today() - last_date).days
                    
                    if days_old > 7:
                        health['healthy'] = False
                        health['issues'].append(f"Latest texture is {days_old} days old")
                        
            # Check status file for persistent failures
            status = self._load_status()
            consecutive_failures = status.get('consecutive_failures', 0)
            
            if consecutive_failures > 3:
                health['healthy'] = False
                health['issues'].append(f"Consecutive failures: {consecutive_failures}")
                
            # Check failed dates
            failed_dates = status.get('failed_dates', [])
            if len(failed_dates) > 5:
                health['healthy'] = False
                health['issues'].append(f"Too many failed dates: {len(failed_dates)}")
                
        except Exception as e:
            health['healthy'] = False
            health['issues'].append(f"Error checking health: {e}")
            
        return health
        
    def cleanup_old_failures(self, days_old: int = 30):
        """Clean up old failed date entries."""
        status = self._load_status()
        failed_dates = status.get('failed_dates', [])
        
        cutoff_date = date.today() - timedelta(days=days_old)
        
        # Remove old failures
        filtered_failures = []
        for date_str in failed_dates:
            try:
                failed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                if failed_date >= cutoff_date:
                    filtered_failures.append(date_str)
            except ValueError:
                continue
                
        if len(filtered_failures) != len(failed_dates):
            status['failed_dates'] = filtered_failures
            self._save_status(status)
            self.logger.info(f"Cleaned up {len(failed_dates) - len(filtered_failures)} old failed dates")

def main():
    """Main function for daily update."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Daily SST texture update')
    parser.add_argument('--health-check', action='store_true',
                       help='Check dataset health without downloading')
    parser.add_argument('--cleanup', action='store_true',
                       help='Clean up old failed date entries')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    try:
        updater = DailyTextureUpdater()
        
        if args.health_check:
            health = updater.check_dataset_health()
            print("\n=== Dataset Health Check ===")
            print(f"Status: {'✅ Healthy' if health['healthy'] else '❌ Issues Found'}")
            print(f"Total textures: {health['stats'].get('total_files', 0)}")
            print(f"Dataset size: {health['stats'].get('total_size_mb', 0)} MB")
            
            if health['stats'].get('date_range'):
                print(f"Date range: {health['stats']['date_range']['start']} to {health['stats']['date_range']['end']}")
                
            if health['issues']:
                print(f"\nIssues:")
                for issue in health['issues']:
                    print(f"  - {issue}")
                    
            return 0 if health['healthy'] else 1
            
        elif args.cleanup:
            updater.cleanup_old_failures()
            print("✅ Cleanup completed")
            return 0
            
        else:
            # Run daily update
            results = updater.run_daily_update()
            
            print(f"\n=== Daily Update Results ===")
            print(f"Status: {'✅ Success' if results['success'] else '❌ Failed'}")
            print(f"Processed: {results['processed']}")
            print(f"Failed: {results['failed']}")
            
            if results['errors']:
                print(f"\nErrors:")
                for error in results['errors']:
                    print(f"  - {error}")
                    
            return 0 if results['success'] else 1
            
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())