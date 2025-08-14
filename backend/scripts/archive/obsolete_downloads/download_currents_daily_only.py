#!/usr/bin/env python3
"""
Daily-Only Currents Downloader with Anomaly Prevention

This script enforces strict daily-only downloads for CMEMS currents data,
preventing the creation of massive monthly aggregate files (99GB anomalies).

Features:
- Strict file size validation (reject >500MB files)
- Daily filename pattern enforcement  
- Anomaly detection and replacement
- Gap detection and filling
- Storage optimization

Usage:
    # Audit existing data for anomalies
    python scripts/download_currents_daily_only.py --audit
    
    # Replace specific anomaly with daily files  
    python scripts/download_currents_daily_only.py --replace-anomaly 2023-11
    
    # Fill all detected gaps
    python scripts/download_currents_daily_only.py --fill-all-gaps
    
    # Download specific date range (daily only)
    python scripts/download_currents_daily_only.py --start 2024-02-01 --end 2024-03-31
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import date, datetime, timedelta
from typing import List, Tuple, Optional, Dict
import calendar
import re

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

from downloaders.currents_downloader import CurrentsDownloader

# Configuration
MAX_DAILY_FILE_SIZE_MB = 500  # Daily files should be ~270MB
ANOMALY_THRESHOLD_MB = 50 * 1024  # Files >50GB are considered anomalies
EXPECTED_DAILY_SIZE_MB = 270  # Expected size for daily files

class DailyCurrentsDownloader:
    """Enhanced currents downloader with strict daily-only enforcement."""
    
    def __init__(self):
        """Initialize the daily-only downloader."""
        self.currents_dir = Path("../ocean-data/raw/currents")
        self.downloader = CurrentsDownloader()
        
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("🌊 Daily-Only Currents Downloader initialized")
    
    def audit_existing_data(self) -> Dict[str, List]:
        """
        Audit existing currents data to find anomalies and gaps.
        
        Returns:
            Dictionary with 'anomalies', 'gaps', and 'summary' keys
        """
        self.logger.info("🔍 Starting comprehensive data audit...")
        
        anomalies = []
        gaps = []
        monthly_stats = {}
        
        # Scan all year/month directories
        if not self.currents_dir.exists():
            self.logger.error(f"Currents directory not found: {self.currents_dir}")
            return {'anomalies': [], 'gaps': [], 'summary': {}}
        
        # Check each year directory
        for year_dir in sorted(self.currents_dir.glob("[0-9]*")):
            if not year_dir.is_dir():
                continue
                
            year = int(year_dir.name)
            monthly_stats[year] = {}
            
            # Check each month directory
            for month in range(1, 13):
                month_str = f"{month:02d}"
                month_dir = year_dir / month_str
                monthly_stats[year][month] = {'files': 0, 'total_size_mb': 0, 'anomalies': 0}
                
                if not month_dir.exists():
                    # Check if this month should exist (not future dates)
                    check_date = date(year, month, 1)
                    if check_date < date.today().replace(day=1):
                        gaps.append({'year': year, 'month': month, 'reason': 'missing_directory'})
                    continue
                
                # Scan files in month directory
                files = list(month_dir.glob("*.nc*"))
                monthly_stats[year][month]['files'] = len(files)
                
                if not files:
                    # Check if this month should have data
                    check_date = date(year, month, 1)
                    if check_date < date.today().replace(day=1):
                        gaps.append({'year': year, 'month': month, 'reason': 'no_files'})
                    continue
                
                # Check each file
                for file_path in files:
                    file_size_mb = file_path.stat().st_size / (1024 * 1024)
                    monthly_stats[year][month]['total_size_mb'] += file_size_mb
                    
                    # Check for anomalies
                    if file_size_mb > ANOMALY_THRESHOLD_MB:
                        anomalies.append({
                            'file': str(file_path),
                            'year': year,
                            'month': month,
                            'size_mb': round(file_size_mb, 1),
                            'size_gb': round(file_size_mb / 1024, 1),
                            'type': 'monthly_aggregate'
                        })
                        monthly_stats[year][month]['anomalies'] += 1
                    
                    # Check filename pattern (skip OSCAR files - they're valid historical data)
                    elif not self._is_valid_daily_filename(file_path.name) and not self._is_valid_oscar_filename(file_path.name):
                        anomalies.append({
                            'file': str(file_path),
                            'year': year,
                            'month': month,
                            'size_mb': round(file_size_mb, 1),
                            'type': 'invalid_filename'
                        })
                
                # Check for insufficient daily coverage
                if files and monthly_stats[year][month]['anomalies'] == 0:
                    days_in_month = calendar.monthrange(year, month)[1]
                    if len(files) < days_in_month * 0.8:  # Less than 80% coverage
                        gaps.append({
                            'year': year,
                            'month': month,
                            'reason': 'incomplete_coverage',
                            'files_found': len(files),
                            'expected_files': days_in_month
                        })
        
        # Generate summary
        summary = {
            'total_anomalies': len(anomalies),
            'total_gaps': len(gaps),
            'storage_wasted_gb': sum(a['size_gb'] for a in anomalies if 'size_gb' in a),
            'monthly_stats': monthly_stats
        }
        
        return {
            'anomalies': anomalies,
            'gaps': gaps, 
            'summary': summary
        }
    
    def _is_valid_daily_filename(self, filename: str) -> bool:
        """Check if filename matches daily pattern: currents_global_YYYYMMDD.nc"""
        daily_pattern = r'^currents_global_\d{8}\.nc$'
        return bool(re.match(daily_pattern, filename))
    
    def _is_valid_oscar_filename(self, filename: str) -> bool:
        """Check if filename matches OSCAR pattern: oscar_currents_final_YYYYMMDD.nc4"""
        oscar_pattern = r'^oscar_currents_final_\d{8}\.nc4?$'
        return bool(re.match(oscar_pattern, filename))
    
    def print_audit_report(self, audit_results: Dict[str, List]):
        """Print comprehensive audit report."""
        anomalies = audit_results['anomalies']
        gaps = audit_results['gaps']
        summary = audit_results['summary']
        
        print("\n" + "="*60)
        print("🔍 CURRENTS DATA AUDIT REPORT")
        print("="*60)
        
        # Summary
        print(f"\n📊 SUMMARY:")
        print(f"   Total anomalies found: {summary['total_anomalies']}")
        print(f"   Total gaps found: {summary['total_gaps']}")
        print(f"   Storage wasted: {summary['storage_wasted_gb']:.1f} GB")
        
        # Anomalies
        if anomalies:
            print(f"\n🚨 ANOMALIES FOUND ({len(anomalies)}):")
            for anomaly in anomalies:
                if anomaly['type'] == 'monthly_aggregate':
                    print(f"   ⚠️  {anomaly['year']}-{anomaly['month']:02d}: {anomaly['size_gb']:.1f}GB monthly aggregate")
                    print(f"      {anomaly['file']}")
                else:
                    print(f"   ⚠️  {anomaly['year']}-{anomaly['month']:02d}: {anomaly['type']}")
                    print(f"      {anomaly['file']}")
        
        # Gaps
        if gaps:
            print(f"\n📂 GAPS FOUND ({len(gaps)}):")
            for gap in gaps:
                if gap['reason'] == 'incomplete_coverage':
                    print(f"   📅 {gap['year']}-{gap['month']:02d}: {gap['files_found']}/{gap['expected_files']} files")
                else:
                    print(f"   📅 {gap['year']}-{gap['month']:02d}: {gap['reason']}")
        
        # Monthly breakdown
        print(f"\n📈 MONTHLY BREAKDOWN:")
        for year, months in summary['monthly_stats'].items():
            year_total_gb = 0
            year_anomalies = 0
            for month, stats in months.items():
                if stats['files'] > 0:
                    size_gb = stats['total_size_mb'] / 1024
                    year_total_gb += size_gb
                    year_anomalies += stats['anomalies']
            
            if year_total_gb > 0:
                status = "⚠️" if year_anomalies > 0 else "✅"
                print(f"   {status} {year}: {year_total_gb:.1f}GB ({year_anomalies} anomalies)")
        
        print("\n" + "="*60)
    
    def replace_anomaly(self, year_month: str) -> bool:
        """
        Replace a monthly anomaly with proper daily files.
        
        Args:
            year_month: String in format "2023-11" or "2024-04"
            
        Returns:
            True if successful, False otherwise
        """
        try:
            year, month = map(int, year_month.split('-'))
            
            self.logger.info(f"🔄 Replacing anomaly for {year}-{month:02d}")
            
            # Check if anomaly exists
            month_dir = self.currents_dir / str(year) / f"{month:02d}"
            if not month_dir.exists():
                self.logger.error(f"Month directory not found: {month_dir}")
                return False
            
            # Find anomalous file
            anomaly_files = []
            for file_path in month_dir.glob("*.nc*"):
                file_size_mb = file_path.stat().st_size / (1024 * 1024)
                if file_size_mb > ANOMALY_THRESHOLD_MB:
                    anomaly_files.append(file_path)
            
            if not anomaly_files:
                self.logger.info(f"No anomalies found in {year}-{month:02d}")
                return True
            
            # Backup anomalous files (optional)
            backup_dir = month_dir / "backup_anomalies"
            backup_dir.mkdir(exist_ok=True)
            
            for anomaly_file in anomaly_files:
                backup_path = backup_dir / anomaly_file.name
                self.logger.info(f"📦 Backing up anomaly: {anomaly_file.name}")
                anomaly_file.rename(backup_path)
            
            # Download daily files for the month
            start_date = date(year, month, 1)
            days_in_month = calendar.monthrange(year, month)[1]
            end_date = date(year, month, days_in_month)
            
            success = self.download_date_range(start_date, end_date)
            
            if success:
                self.logger.info(f"✅ Successfully replaced anomaly for {year}-{month:02d}")
                # Calculate space saved
                total_anomaly_size = sum(f.stat().st_size for f in backup_dir.glob("*.nc*"))
                space_saved_gb = total_anomaly_size / (1024**3)
                self.logger.info(f"💾 Space optimization: {space_saved_gb:.1f}GB replaced with ~{days_in_month * EXPECTED_DAILY_SIZE_MB / 1024:.1f}GB")
            else:
                self.logger.error(f"❌ Failed to replace anomaly for {year}-{month:02d}")
                # Restore backup files
                for backup_file in backup_dir.glob("*.nc*"):
                    original_path = month_dir / backup_file.name
                    backup_file.rename(original_path)
                backup_dir.rmdir()
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error replacing anomaly {year_month}: {e}")
            return False
    
    def fill_gaps(self, gaps: List[Dict]) -> bool:
        """
        Fill detected gaps with proper daily files.
        
        Args:
            gaps: List of gap dictionaries from audit_existing_data
            
        Returns:
            True if all gaps filled successfully, False otherwise
        """
        if not gaps:
            self.logger.info("✅ No gaps to fill!")
            return True
        
        self.logger.info(f"🔄 Filling {len(gaps)} detected gaps...")
        
        success_count = 0
        
        for gap in gaps:
            year = gap['year']
            month = gap['month']
            
            self.logger.info(f"📅 Filling gap: {year}-{month:02d}")
            
            # Generate date range for the month
            start_date = date(year, month, 1)
            days_in_month = calendar.monthrange(year, month)[1]
            end_date = date(year, month, days_in_month)
            
            # Don't download future dates
            if start_date >= date.today():
                self.logger.info(f"⏭️  Skipping future month: {year}-{month:02d}")
                continue
            
            # Adjust end date if it's in the future
            if end_date >= date.today():
                end_date = date.today() - timedelta(days=1)
            
            if start_date <= end_date:
                success = self.download_date_range(start_date, end_date)
                if success:
                    success_count += 1
                    self.logger.info(f"✅ Successfully filled gap: {year}-{month:02d}")
                else:
                    self.logger.error(f"❌ Failed to fill gap: {year}-{month:02d}")
        
        self.logger.info(f"📈 Gap filling results: {success_count}/{len(gaps)} successful")
        return success_count == len(gaps)
    
    def download_date_range(self, start_date: date, end_date: date) -> bool:
        """
        Download daily files for a date range with strict validation.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            True if all downloads successful, False otherwise
        """
        self.logger.info(f"📅 Downloading daily files: {start_date} to {end_date}")
        
        current_date = start_date
        success_count = 0
        total_days = (end_date - start_date).days + 1
        
        while current_date <= end_date:
            try:
                self.logger.info(f"   📥 Downloading {current_date}...")
                
                # Pre-download validation
                if not self._validate_download_date(current_date):
                    self.logger.warning(f"   ⏭️  Skipping {current_date} (validation failed)")
                    current_date += timedelta(days=1)
                    continue
                
                # Attempt download with strict daily enforcement
                success = self._download_single_date_with_validation(current_date)
                
                if success:
                    self.logger.info(f"   ✅ {current_date}")
                    success_count += 1
                else:
                    self.logger.error(f"   ❌ {current_date}")
                
            except Exception as e:
                self.logger.error(f"   ❌ {current_date}: {e}")
            
            current_date += timedelta(days=1)
        
        success_rate = 100 * success_count / total_days
        self.logger.info(f"📊 Download completed: {success_count}/{total_days} files ({success_rate:.1f}%)")
        
        return success_count == total_days
    
    def _validate_download_date(self, target_date: date) -> bool:
        """Validate that a date should be downloaded."""
        # Don't download future dates
        if target_date >= date.today():
            return False
        
        # Don't download very old dates (before CMEMS coverage)
        if target_date < date(2022, 6, 1):
            return False
        
        return True
    
    def _download_single_date_with_validation(self, target_date: date) -> bool:
        """
        Download single date with strict validation to prevent anomalies.
        
        Args:
            target_date: Date to download
            
        Returns:
            True if successful and valid, False otherwise
        """
        try:
            # Attempt download using existing downloader
            success = self.downloader.download_date(target_date)
            
            if not success:
                return False
            
            # Post-download validation
            year_month = target_date.strftime("%Y/%m")
            output_dir = self.currents_dir / year_month
            filename = f"currents_global_{target_date.strftime('%Y%m%d')}.nc"
            file_path = output_dir / filename
            
            if not file_path.exists():
                self.logger.error(f"Downloaded file not found: {file_path}")
                return False
            
            # Validate file size
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            
            if file_size_mb > MAX_DAILY_FILE_SIZE_MB:
                self.logger.error(f"File too large ({file_size_mb:.1f}MB > {MAX_DAILY_FILE_SIZE_MB}MB): {file_path}")
                # Remove oversized file to prevent anomaly
                file_path.unlink()
                return False
            
            if file_size_mb < 50:  # Suspiciously small
                self.logger.warning(f"File suspiciously small ({file_size_mb:.1f}MB): {file_path}")
                # Don't remove, but warn - might be legitimate
            
            # Validate filename
            if not self._is_valid_daily_filename(file_path.name):
                self.logger.error(f"Invalid filename pattern: {file_path.name}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error downloading {target_date}: {e}")
            return False

def main():
    """Main function to handle command line interface."""
    parser = argparse.ArgumentParser(
        description='Daily-Only Currents Downloader with Anomaly Prevention',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Audit existing data for anomalies and gaps
    python scripts/download_currents_daily_only.py --audit
    
    # Replace specific anomaly (2023-11 or 2024-04)
    python scripts/download_currents_daily_only.py --replace-anomaly 2023-11
    
    # Fill all detected gaps  
    python scripts/download_currents_daily_only.py --fill-all-gaps
    
    # Download specific date range
    python scripts/download_currents_daily_only.py --start 2024-02-01 --end 2024-03-31
    
    # Download yesterday's data only
    python scripts/download_currents_daily_only.py --yesterday
        """
    )
    
    parser.add_argument('--audit', action='store_true',
                       help='Audit existing data for anomalies and gaps')
    parser.add_argument('--replace-anomaly', type=str, metavar='YYYY-MM',
                       help='Replace anomaly for specific month (e.g., 2023-11)')
    parser.add_argument('--fill-all-gaps', action='store_true',
                       help='Fill all detected gaps with daily files')
    parser.add_argument('--start', type=str, metavar='YYYY-MM-DD',
                       help='Start date for download range')
    parser.add_argument('--end', type=str, metavar='YYYY-MM-DD', 
                       help='End date for download range')
    parser.add_argument('--yesterday', action='store_true',
                       help='Download yesterday\'s data only')
    
    args = parser.parse_args()
    
    # Initialize downloader
    downloader = DailyCurrentsDownloader()
    
    try:
        # Audit mode
        if args.audit:
            audit_results = downloader.audit_existing_data()
            downloader.print_audit_report(audit_results)
            return 0
        
        # Replace anomaly mode
        if args.replace_anomaly:
            success = downloader.replace_anomaly(args.replace_anomaly)
            return 0 if success else 1
        
        # Fill gaps mode
        if args.fill_all_gaps:
            # First audit to find gaps
            audit_results = downloader.audit_existing_data()
            success = downloader.fill_gaps(audit_results['gaps'])
            return 0 if success else 1
        
        # Yesterday mode
        if args.yesterday:
            yesterday = date.today() - timedelta(days=1)
            success = downloader.download_date_range(yesterday, yesterday)
            return 0 if success else 1
        
        # Date range mode
        if args.start and args.end:
            start_date = datetime.strptime(args.start, '%Y-%m-%d').date()
            end_date = datetime.strptime(args.end, '%Y-%m-%d').date()
            success = downloader.download_date_range(start_date, end_date)
            return 0 if success else 1
        
        # No arguments - show help
        parser.print_help()
        return 0
        
    except KeyboardInterrupt:
        print("\n⏹️  Download interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())