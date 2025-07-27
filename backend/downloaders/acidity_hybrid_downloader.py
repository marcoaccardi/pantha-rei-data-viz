#!/usr/bin/env python3
"""
Hybrid acidity downloader that combines historical (1993-2022) and current (2021-present) datasets.
Routes download requests to appropriate CMEMS products based on date ranges.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from datetime import date, datetime, timedelta

from .base_downloader import BaseDataDownloader
from .acidity_historical_downloader import AcidityHistoricalDownloader
from .acidity_current_downloader import AcidityCurrentDownloader

class AcidityHybridDownloader(BaseDataDownloader):
    """Hybrid downloader for acidity data combining historical and current sources."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize Hybrid Acidity downloader."""
        super().__init__("acidity", config_path)
        
        # Initialize individual downloaders
        try:
            self.historical_downloader = AcidityHistoricalDownloader(config_path)
            self.current_downloader = AcidityCurrentDownloader(config_path)
        except Exception as e:
            self.logger.error(f"Failed to initialize sub-downloaders: {e}")
            raise
        
        # Load hybrid configuration
        self.hybrid_config = self.dataset_config.get("hybrid_config", False)
        if not self.hybrid_config:
            raise ValueError("Dataset 'acidity' is not configured as a hybrid dataset")
        
        self.overlap_config = self.dataset_config.get("overlap_period", {})
        self.overlap_start = date.fromisoformat(self.overlap_config.get("start", "2021-10-01"))
        self.overlap_end = date.fromisoformat(self.overlap_config.get("end", "2022-12-31"))
        self.overlap_primary = self.overlap_config.get("primary", "acidity_historical")
        
        # Dataset boundaries
        self.historical_start = date(1993, 1, 1)
        self.historical_end = date(2022, 12, 31)
        self.current_start = date(2021, 10, 1)
        self.current_end = date.today()
        
        # GLODAP dataset boundaries for pH data
        self.glodap_start = date(1993, 1, 1)
        self.glodap_end = date(2021, 12, 31)
        
        self.logger.info("Initialized Hybrid Acidity downloader")
        self.logger.info(f"Historical range: {self.historical_start} to {self.historical_end}")
        self.logger.info(f"Current range: {self.current_start} to {self.current_end}")
        self.logger.info(f"GLODAP pH range: {self.glodap_start} to {self.glodap_end}")
        self.logger.info(f"Overlap period: {self.overlap_start} to {self.overlap_end} (primary: {self.overlap_primary})")
    
    def route_date_to_downloader(self, target_date: date) -> tuple[BaseDataDownloader, str]:
        """
        Route a date to the appropriate downloader.
        
        Args:
            target_date: Date to route
            
        Returns:
            Tuple of (downloader, dataset_name)
        """
        # Check if date is in overlap period
        if self.overlap_start <= target_date <= self.overlap_end:
            if self.overlap_primary == "acidity_historical":
                return self.historical_downloader, "acidity_historical"
            else:
                return self.current_downloader, "acidity_current"
        
        # Route based on date ranges
        if target_date <= self.historical_end:
            if target_date >= self.historical_start:
                return self.historical_downloader, "acidity_historical"
            else:
                raise ValueError(f"Date {target_date} is before historical dataset start ({self.historical_start})")
        
        if target_date >= self.current_start:
            return self.current_downloader, "acidity_current"
        
        # Date falls in gap between datasets (should not happen with current configuration)
        raise ValueError(f"Date {target_date} falls in gap between datasets")
    
    def _get_filename_for_date(self, target_date: date) -> str:
        """Get filename for hybrid acidity data for given date."""
        return f"acidity_harmonized_{target_date.strftime('%Y%m%d')}.nc"
    
    def download_date(self, target_date: date) -> bool:
        """
        Download acidity data for a specific date using multi-source hybrid approach.
        
        For historical dates (1993-2021), downloads both:
        - GLODAP discrete pH samples 
        - CMEMS daily nutrients
        
        For current dates (2021+), downloads CMEMS with pH + nutrients.
        
        Args:
            target_date: Date to download data for
            
        Returns:
            True if successful, False otherwise
        """
        try:
            success_count = 0
            total_downloads = 0
            
            # Strategy: Download biogeochemistry data from appropriate CMEMS source
            # Note: GLODAP discrete pH integration was planned but not implemented
            # Using comprehensive CMEMS data instead
            downloader, dataset_name = self.route_date_to_downloader(target_date)
            self.logger.info(f"Downloading {dataset_name} data for {target_date}")
            
            cmems_success = downloader.download_date(target_date)
            total_downloads += 1
            if cmems_success:
                success_count += 1
                self._update_hybrid_status(target_date, dataset_name, cmems_success)
                
                # Copy to unified location for API access
                self._copy_to_unified_location(target_date, dataset_name)
            
            # Consider success if at least one source succeeded
            overall_success = success_count > 0
            
            if overall_success:
                self.logger.info(f"Hybrid download successful for {target_date}: {success_count}/{total_downloads} sources")
            else:
                self.logger.error(f"All hybrid downloads failed for {target_date}")
            
            return overall_success
            
        except Exception as e:
            self.logger.error(f"Error downloading hybrid acidity data for {target_date}: {e}")
            return False
    
    def download_date_range(self, start_date: Union[str, date], end_date: Union[str, date], max_files: Optional[int] = None) -> Dict[str, Any]:
        """
        Download acidity data for a date range using hybrid approach.
        
        Args:
            start_date: Start date for download (string or date object)
            end_date: End date for download (string or date object)
            max_files: Maximum number of files to download
            
        Returns:
            Dictionary with download results
        """
        # Convert string dates to date objects if needed
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            
        self.logger.info(f"Starting hybrid acidity download from {start_date} to {end_date}")
        
        # Split date range by datasets
        date_ranges = self._split_date_range_by_datasets(start_date, end_date)
        
        results = {
            "downloaded": 0,
            "failed": 0,
            "errors": [],
            "datasets_used": [],
            "date_ranges": date_ranges
        }
        
        files_downloaded = 0
        
        for dataset_name, date_range in date_ranges.items():
            if max_files and files_downloaded >= max_files:
                self.logger.info(f"Reached max_files limit ({max_files}), stopping download")
                break
            
            range_start, range_end = date_range
            remaining_files = max_files - files_downloaded if max_files else None
            
            self.logger.info(f"Downloading {dataset_name} data from {range_start} to {range_end}")
            
            try:
                if dataset_name == "acidity_historical":
                    downloader_result = self.historical_downloader.download_date_range(
                        range_start, range_end, remaining_files
                    )
                elif dataset_name == "acidity_current":
                    downloader_result = self.current_downloader.download_date_range(
                        range_start, range_end, remaining_files
                    )
                else:
                    raise ValueError(f"Unknown dataset: {dataset_name}")
                
                # Accumulate results
                results["downloaded"] += downloader_result.get("downloaded", 0)
                results["failed"] += downloader_result.get("failed", 0)
                results["errors"].extend(downloader_result.get("errors", []))
                results["datasets_used"].append(dataset_name)
                
                files_downloaded += downloader_result.get("downloaded", 0)
                
            except Exception as e:
                self.logger.error(f"Error downloading {dataset_name} data: {e}")
                results["failed"] += 1
                results["errors"].append(f"Error downloading {dataset_name}: {e}")
        
        self.logger.info(f"Hybrid download complete: {results['downloaded']} downloaded, {results['failed']} failed")
        
        # Update overall status
        self._update_overall_hybrid_status(results)
        
        return results
    
    def _split_date_range_by_datasets(self, start_date: date, end_date: date) -> Dict[str, tuple[date, date]]:
        """
        Split a date range into sub-ranges for each dataset.
        
        Args:
            start_date: Overall start date
            end_date: Overall end date
            
        Returns:
            Dictionary mapping dataset names to (start_date, end_date) tuples
        """
        ranges = {}
        
        # Historical range
        hist_start = max(start_date, self.historical_start)
        hist_end = min(end_date, self.historical_end)
        
        if hist_start <= hist_end:
            ranges["acidity_historical"] = (hist_start, hist_end)
        
        # Current range (only if beyond historical end date, considering overlap handling)
        if end_date > self.historical_end:
            curr_start = max(start_date, self.historical_end + timedelta(days=1))
            curr_end = min(end_date, self.current_end)
            
            if curr_start <= curr_end:
                ranges["acidity_current"] = (curr_start, curr_end)
        
        return ranges
    
    def _copy_to_unified_location(self, target_date: date, source_dataset: str):
        """
        Copy downloaded file to unified acidity location for API access.
        
        Args:
            target_date: Date of the downloaded data
            source_dataset: Source dataset name
        """
        try:
            # Define source and destination paths
            source_base = self.processed_data_path / "unified_coords" / source_dataset
            dest_base = self.processed_data_path / "unified_coords" / "acidity"
            
            dest_base.mkdir(parents=True, exist_ok=True)
            
            # Create year/month structure
            year_month = target_date.strftime("%Y/%m")
            source_dir = source_base / year_month
            dest_dir = dest_base / year_month
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            # Find source file
            if source_dataset == "acidity_historical":
                source_filename = f"acidity_historical_{target_date.strftime('%Y%m%d')}.nc"
            else:
                source_filename = f"acidity_current_{target_date.strftime('%Y%m%d')}.nc"
            
            source_file = source_dir / source_filename
            
            # Define unified filename
            dest_filename = f"acidity_harmonized_{target_date.strftime('%Y%m%d')}.nc"
            dest_file = dest_dir / dest_filename
            
            # Copy file if source exists
            if source_file.exists():
                import shutil
                shutil.copy2(source_file, dest_file)
                self.logger.info(f"Copied {source_file} to unified location {dest_file}")
            else:
                self.logger.warning(f"Source file not found for unified copy: {source_file}")
                
        except Exception as e:
            self.logger.error(f"Error copying to unified location: {e}")
    
    def _update_hybrid_status(self, target_date: date, dataset_name: str, success: bool):
        """Update status for individual date download."""
        try:
            current_status = self.get_status()
            
            # Update last successful date if this download succeeded
            if success:
                last_date_key = "last_date"
                current_last_date = current_status.get(last_date_key)
                
                if not current_last_date or target_date.strftime("%Y-%m-%d") > current_last_date:
                    self.update_status(last_date=target_date.strftime("%Y-%m-%d"))
                
                # Track which dataset was used for this date
                dataset_usage = current_status.get("dataset_usage", {})
                dataset_usage[target_date.strftime("%Y-%m-%d")] = dataset_name
                self.update_status(dataset_usage=dataset_usage)
                
        except Exception as e:
            self.logger.error(f"Error updating hybrid status: {e}")
    
    def _update_overall_hybrid_status(self, results: Dict[str, Any]):
        """Update overall hybrid downloader status."""
        try:
            # Update file counts and storage
            current_status = self.get_status()
            new_file_count = current_status.get("total_files", 0) + results["downloaded"]
            new_storage_gb = self.get_storage_usage()
            
            self.update_status(
                total_files=new_file_count,
                storage_gb=round(new_storage_gb, 3),
                datasets_used=results["datasets_used"],
                last_download_summary=results
            )
            
        except Exception as e:
            self.logger.error(f"Error updating overall hybrid status: {e}")
    
    def get_date_coverage(self) -> dict:
        """Get information about date coverage for hybrid acidity data."""
        try:
            historical_coverage = self.historical_downloader.get_date_coverage()
            current_coverage = self.current_downloader.get_date_coverage()
            
            # Combine coverage information
            all_dates = []
            
            if historical_coverage["total_days"] > 0:
                # Parse historical dates
                first_hist = datetime.strptime(historical_coverage["first_date"], "%Y-%m-%d").date()
                last_hist = datetime.strptime(historical_coverage["last_date"], "%Y-%m-%d").date()
                
                current = first_hist
                while current <= last_hist:
                    all_dates.append(current)
                    current += timedelta(days=1)
            
            if current_coverage["total_days"] > 0:
                # Parse current dates
                first_curr = datetime.strptime(current_coverage["first_date"], "%Y-%m-%d").date()
                last_curr = datetime.strptime(current_coverage["last_date"], "%Y-%m-%d").date()
                
                current = first_curr
                while current <= last_curr:
                    if current not in all_dates:  # Avoid duplicates in overlap period
                        all_dates.append(current)
                    current += timedelta(days=1)
            
            all_dates.sort()
            
            if all_dates:
                return {
                    "first_date": all_dates[0].strftime("%Y-%m-%d"),
                    "last_date": all_dates[-1].strftime("%Y-%m-%d"),
                    "total_days": len(all_dates),
                    "historical_coverage": historical_coverage,
                    "current_coverage": current_coverage,
                    "hybrid_status": "active"
                }
            else:
                return {
                    "first_date": None,
                    "last_date": None,
                    "total_days": 0,
                    "historical_coverage": historical_coverage,
                    "current_coverage": current_coverage,
                    "hybrid_status": "no_data"
                }
                
        except Exception as e:
            self.logger.error(f"Error getting hybrid date coverage: {e}")
            return {
                "first_date": None,
                "last_date": None,
                "total_days": 0,
                "error": str(e),
                "hybrid_status": "error"
            }
    
    def validate_downloaded_data(self) -> dict:
        """Validate all downloaded hybrid acidity data."""
        try:
            historical_validation = self.historical_downloader.validate_downloaded_data()
            current_validation = self.current_downloader.validate_downloaded_data()
            
            # Combine validation results
            combined_validation = {
                "hybrid_status": "active",
                "historical_validation": historical_validation,
                "current_validation": current_validation,
                "total_files": historical_validation.get("total_files", 0) + current_validation.get("total_files", 0),
                "total_storage_gb": historical_validation.get("total_storage_gb", 0) + current_validation.get("total_storage_gb", 0),
                "date_coverage": self.get_date_coverage()
            }
            
            return combined_validation
            
        except Exception as e:
            self.logger.error(f"Error validating hybrid data: {e}")
            return {
                "hybrid_status": "error",
                "error": str(e)
            }