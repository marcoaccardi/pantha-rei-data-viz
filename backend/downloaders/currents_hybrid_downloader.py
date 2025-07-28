#!/usr/bin/env python3
"""
Hybrid Currents downloader combining NASA OSCAR historical data with CMEMS current data.
Provides seamless access to ocean currents from 2021 to present.
"""

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

from .base_downloader import BaseDataDownloader
from .currents_oscar_downloader import CurrentsOscarDownloader
from .currents_downloader import CurrentsDownloader


class CurrentsHybridDownloader(BaseDataDownloader):
    """Hybrid downloader for ocean currents combining OSCAR and CMEMS data sources."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize hybrid currents downloader."""
        super().__init__("currents", config_path)
        
        # Initialize component downloaders
        self.oscar_downloader = CurrentsOscarDownloader(config_path)
        self.cmems_downloader = CurrentsDownloader(config_path)
        
        # Date ranges for each source
        self.oscar_start = date(2003, 1, 1)
        self.oscar_end = date(2023, 6, 4)  # Extended! Discovered extended coverage to June 4
        self.cmems_start = date(2022, 6, 1)
        
        # Overlap strategy: prefer OSCAR for historical consistency
        self.overlap_strategy = "prefer_oscar"
        
        self.logger.info("Initialized Hybrid Currents downloader")
        self.logger.info(f"OSCAR range: {self.oscar_start} to {self.oscar_end} (20 years)")
        self.logger.info(f"CMEMS range: {self.cmems_start} to present")
        self.logger.info(f"Overlap period: {self.cmems_start} to {self.oscar_end} (primary: OSCAR)")
        self.logger.info(f"Total coverage: 2003-2025 (22+ years of historical ocean currents)")
    
    def _determine_source_for_date(self, target_date: date) -> str:
        """
        Determine which data source to use for a given date.
        
        Args:
            target_date: Date to check
            
        Returns:
            'oscar', 'cmems', or 'unavailable'
        """
        # Define gap period explicitly (MUCH SMALLER NOW!)
        gap_start = date(2023, 6, 5)  # Only 1 day gap!
        gap_end = date(2023, 6, 5)    # Same day - minimal gap
        cmems_post_gap = date(2023, 6, 6)
        
        if target_date < self.oscar_start:
            return 'unavailable'  # Before any available data
        
        elif self.oscar_start <= target_date <= self.oscar_end:
            return 'oscar'  # OSCAR period (preferred in overlap)
        
        elif gap_start <= target_date <= gap_end:
            return 'unavailable'  # Gap period (2023-04-08 to 2023-05-31)
        
        elif target_date >= cmems_post_gap:
            return 'cmems'  # CMEMS period after gap
        
        else:
            return 'unavailable'  # Fallback
    
    def download_for_date(self, target_date: date) -> Dict[str, Any]:
        """
        Download currents data for a specific date using appropriate source.
        
        Args:
            target_date: Date to download data for
            
        Returns:
            Dictionary with download results including source information
        """
        source = self._determine_source_for_date(target_date)
        
        if source == 'unavailable':
            return {
                'success': False,
                'date': target_date.strftime('%Y-%m-%d'),
                'error': 'Date outside available data range',
                'available_ranges': [
                    f"OSCAR: {self.oscar_start} to {self.oscar_end}",
                    f"CMEMS: {self.cmems_start} to present"
                ]
            }
        
        self.logger.info(f"Downloading currents data for {target_date} using {source.upper()} source")
        
        try:
            if source == 'oscar':
                result = self.oscar_downloader.download_for_date(target_date)
            elif source == 'cmems':
                result = self.cmems_downloader.download_for_date(target_date)
            
            # Add source information to result
            result['source'] = source
            result['hybrid_info'] = {
                'primary_source': source,
                'date_range_type': self._get_date_range_type(target_date),
                'alternative_available': self._check_alternative_available(target_date, source)
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in hybrid download for {target_date}: {e}")
            return {
                'success': False,
                'date': target_date.strftime('%Y-%m-%d'),
                'source': source,
                'error': str(e)
            }
    
    def _get_date_range_type(self, target_date: date) -> str:
        """Get the type of date range for a given date."""
        if target_date < self.oscar_start:
            return 'before_coverage'
        elif self.oscar_start <= target_date < self.cmems_start:
            return 'oscar_only'
        elif self.cmems_start <= target_date <= self.oscar_end:
            return 'overlap_period'
        elif self.oscar_end < target_date < date(2023, 6, 1):
            return 'gap_period'
        else:
            return 'cmems_only'
    
    def _check_alternative_available(self, target_date: date, primary_source: str) -> bool:
        """Check if alternative source is available for the date."""
        if primary_source == 'oscar':
            return target_date >= self.cmems_start
        elif primary_source == 'cmems':
            return self.oscar_start <= target_date <= self.oscar_end
        return False
    
    def download_date_range(self, start_date: str, end_date: str, max_files: Optional[int] = None) -> Dict[str, Any]:
        """
        Download currents data for a date range using hybrid approach.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            max_files: Optional maximum number of files to download
            
        Returns:
            Dictionary with comprehensive download results
        """
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError as e:
            return {
                'success': False,
                'error': f'Invalid date format: {e}',
                'expected_format': 'YYYY-MM-DD'
            }
        
        self.logger.info(f"Starting hybrid currents download from {start_date} to {end_date}")
        
        # Get all dates in range
        dates = self.get_dates_in_range(start_dt, end_dt)
        
        if max_files:
            dates = dates[:max_files]
            self.logger.info(f"Limited to {max_files} files")
        
        results = {
            'downloaded': 0,
            'failed': 0,
            'skipped': 0,
            'errors': [],
            'source_breakdown': {'oscar': 0, 'cmems': 0, 'unavailable': 0},
            'files': []
        }
        
        for target_date in dates:
            source = self._determine_source_for_date(target_date)
            
            if source == 'unavailable':
                results['failed'] += 1
                results['source_breakdown']['unavailable'] += 1
                results['errors'].append(f"{target_date}: Date outside available data range")
                continue
            
            try:
                result = self.download_for_date(target_date)
                
                if result.get('success', False):
                    if result.get('skipped', False):
                        results['skipped'] += 1
                    else:
                        results['downloaded'] += 1
                    results['source_breakdown'][source] += 1
                    results['files'].append({
                        'date': target_date.strftime('%Y-%m-%d'),
                        'source': source,
                        'status': 'skipped' if result.get('skipped') else 'downloaded',
                        'path': str(result.get('processed_path', result.get('path', '')))
                    })
                else:
                    results['failed'] += 1
                    results['errors'].append(f"{target_date}: {result.get('error', 'Unknown error')}")
                
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"{target_date}: {str(e)}")
                self.logger.error(f"Error downloading {target_date}: {e}")
        
        # Summary
        total_processed = results['downloaded'] + results['failed'] + results['skipped']
        results['summary'] = {
            'total_requested': len(dates),
            'total_processed': total_processed,
            'success_rate': (results['downloaded'] + results['skipped']) / total_processed if total_processed > 0 else 0,
            'sources_used': {k: v for k, v in results['source_breakdown'].items() if v > 0}
        }
        
        self.logger.info(f"Hybrid download complete: {results['downloaded']} downloaded, {results['skipped']} skipped, {results['failed']} failed")
        self.logger.info(f"Source breakdown: {results['source_breakdown']}")
        
        return results
    
    def _get_filename_for_date(self, target_date: date) -> str:
        """
        Get filename for a specific date by delegating to appropriate downloader.
        
        Args:
            target_date: Date to get filename for
            
        Returns:
            Filename string for the date
        """
        source = self._determine_source_for_date(target_date)
        
        if source == 'oscar':
            return self.oscar_downloader._get_filename_for_date(target_date)
        elif source == 'cmems':
            return self.cmems_downloader._get_filename_for_date(target_date)
        else:
            # For unavailable dates, return a generic filename
            return f"currents_unavailable_{target_date.strftime('%Y%m%d')}.nc"
    
    def download_date(self, target_date: date) -> bool:
        """
        Download data for a specific date (abstract method implementation).
        
        Args:
            target_date: Date to download data for
            
        Returns:
            True if download successful, False otherwise
        """
        try:
            result = self.download_for_date(target_date)
            return result.get('success', False)
        except Exception as e:
            self.logger.error(f"Error in hybrid download_date for {target_date}: {e}")
            return False

    def get_coverage_info(self) -> Dict[str, Any]:
        """
        Get comprehensive information about data coverage.
        
        Returns:
            Dictionary with coverage information
        """
        return {
            'total_coverage': {
                'start': self.oscar_start.strftime('%Y-%m-%d'),
                'end': 'present',
                'note': 'Extended historical coverage: 2003-2025 (22+ years) with small gap in April-May 2023'
            },
            'sources': {
                'oscar': {
                    'name': 'NASA OSCAR',
                    'coverage': f"{self.oscar_start} to {self.oscar_end}",
                    'resolution': '0.25°',
                    'variables': ['u', 'v'],
                    'priority': 'primary for 2003-2023 (historical data)'
                },
                'cmems': {
                    'name': 'CMEMS Global Currents',
                    'coverage': f"{self.cmems_start} to present",
                    'resolution': '0.083°',
                    'variables': ['uo', 'vo'],
                    'priority': 'primary for 2023-present'
                }
            },
            'coverage_periods': {
                'oscar_only': f"{self.oscar_start} to {self.cmems_start - timedelta(days=1)}",
                'overlap': f"{self.cmems_start} to {self.oscar_end}",
                'gap': "2023-06-05 (1 day only!)",
                'cmems_only': "2023-06-06 to present"
            },
            'strategy': {
                'overlap_preference': 'OSCAR (for historical consistency)',
                'gap_handling': 'No data available',
                'coordinate_system': '-180 to +180 degrees (harmonized)'
            }
        }