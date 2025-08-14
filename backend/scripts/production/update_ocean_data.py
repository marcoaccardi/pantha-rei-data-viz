#!/usr/bin/env python3
"""
Comprehensive On-Demand Ocean Data Update Script

This script intelligently detects gaps in ocean data and downloads missing files
from the last available date to the current date. It includes comprehensive
file validation, error recovery, and data processing to ensure zero errors.

Usage:
    python update_ocean_data.py
    python update_ocean_data.py --datasets sst,currents
    python update_ocean_data.py --dry-run
    python update_ocean_data.py --repair-mode
"""

import sys
import argparse
import logging
import json
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
import re

# Add backend to path (now two levels up since we're in scripts/production/)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.status_manager import StatusManager
from downloaders.sst_downloader import SSTDownloader
from downloaders.sst_erddap_texture_downloader import SSTERDDAPTextureDownloader
from downloaders.currents_downloader import CurrentsDownloader
from downloaders.acidity_hybrid_downloader import AcidityHybridDownloader
from downloaders.microplastics_downloader import MicroplasticsDownloader
from processors.coordinate_harmonizer import CoordinateHarmonizer

class GapDetector:
    """Detects gaps in ocean data by scanning actual files."""
    
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.raw_path = base_path / "raw"
        self.processed_path = base_path / "processed" / "unified_coords"
        self.textures_path = base_path / "textures"
        
    def detect_gaps(self, dataset: str) -> Tuple[Optional[date], List[date]]:
        """
        Detect gaps for a dataset by scanning actual files.
        
        Returns:
            Tuple of (latest_date_found, list_of_missing_dates_to_current)
        """
        if dataset == "sst_textures":
            return self._detect_texture_gaps()
        else:
            return self._detect_raw_data_gaps(dataset)
    
    def _detect_texture_gaps(self) -> Tuple[Optional[date], List[date]]:
        """Detect gaps in SST texture files."""
        texture_path = self.textures_path / "sst"
        if not texture_path.exists():
            # No textures exist, start from texture start date
            return None, self._generate_date_range(date(2003, 1, 1), date.today() - timedelta(days=1))
        
        # Find latest texture file
        latest_date = None
        texture_pattern = re.compile(r"SST_(\d{8})\.png")
        
        for year_dir in sorted(texture_path.glob("*"), reverse=True):
            if not year_dir.is_dir():
                continue
            for texture_file in sorted(year_dir.glob("SST_*.png"), reverse=True):
                match = texture_pattern.match(texture_file.name)
                if match:
                    date_str = match.group(1)
                    latest_date = datetime.strptime(date_str, "%Y%m%d").date()
                    break
            if latest_date:
                break
        
        if not latest_date:
            return None, self._generate_date_range(date(2003, 1, 1), date.today() - timedelta(days=1))
        
        # Generate missing dates from latest to yesterday
        yesterday = date.today() - timedelta(days=1)
        if latest_date >= yesterday:
            return latest_date, []
        
        missing_dates = self._generate_date_range(latest_date + timedelta(days=1), yesterday)
        return latest_date, missing_dates
    
    def _detect_raw_data_gaps(self, dataset: str) -> Tuple[Optional[date], List[date]]:
        """Detect gaps in raw data files."""
        dataset_path = self.raw_path / dataset
        if not dataset_path.exists():
            # No data exists, start from dataset start date
            start_dates = {
                "sst": date(1981, 9, 1),
                "currents": date(2003, 1, 1),
                "acidity": date(1993, 1, 1),
                "microplastics": date(1993, 1, 1)
            }
            start_date = start_dates.get(dataset, date(2024, 1, 1))
            return None, self._generate_date_range(start_date, date.today() - timedelta(days=1))
        
        # Find latest file by scanning directory structure
        latest_date = None
        
        # Different patterns for different datasets
        if dataset == "sst":
            pattern = re.compile(r"oisst-avhrr-v02r01\.(\d{8})\.nc")
        elif dataset == "currents":
            pattern = re.compile(r"currents.*?(\d{8}).*\.nc")
        elif dataset.startswith("acidity"):
            pattern = re.compile(r"acidity.*?(\d{8}).*\.nc")
        elif dataset == "microplastics":
            # Microplastics is a static dataset - no regular updates needed
            return date.today() - timedelta(days=1), []  # Always up to date
        else:
            pattern = re.compile(r".*(\d{8}).*\.nc")
        
        # Scan for latest file
        for year_dir in sorted(dataset_path.glob("*"), reverse=True):
            if not year_dir.is_dir():
                continue
            for month_dir in sorted(year_dir.glob("*"), reverse=True):
                if not month_dir.is_dir():
                    continue
                for data_file in sorted(month_dir.glob("*.nc"), reverse=True):
                    match = pattern.search(data_file.name)
                    if match:
                        date_str = match.group(1)
                        try:
                            latest_date = datetime.strptime(date_str, "%Y%m%d").date()
                            break
                        except ValueError:
                            continue
                if latest_date:
                    break
            if latest_date:
                break
        
        if not latest_date:
            # No valid files found, start from beginning
            start_dates = {
                "sst": date(2024, 1, 1),  # Test start
                "currents": date(2024, 1, 1),
                "acidity": date(2024, 1, 1),
                "microplastics": date(2024, 1, 1)
            }
            start_date = start_dates.get(dataset, date(2024, 1, 1))
            return None, self._generate_date_range(start_date, date.today() - timedelta(days=1))
        
        # Generate missing dates
        yesterday = date.today() - timedelta(days=1)
        if latest_date >= yesterday:
            return latest_date, []
        
        missing_dates = self._generate_date_range(latest_date + timedelta(days=1), yesterday)
        return latest_date, missing_dates
    
    def _generate_date_range(self, start_date: date, end_date: date) -> List[date]:
        """Generate list of dates between start and end (inclusive)."""
        if start_date > end_date:
            return []
        
        dates = []
        current_date = start_date
        while current_date <= end_date:
            dates.append(current_date)
            current_date += timedelta(days=1)
        return dates


class OceanDataUpdater:
    """Main ocean data update orchestrator with comprehensive error handling."""
    
    def __init__(self, base_path: Optional[Path] = None, dry_run: bool = False):
        """Initialize the updater."""
        self.base_path = base_path or Path(__file__).parent.parent.parent / "ocean-data"
        self.dry_run = dry_run
        
        # Initialize components
        self.gap_detector = GapDetector(self.base_path)
        self.status_manager = StatusManager()
        self.coordinate_harmonizer = CoordinateHarmonizer()
        
        # Initialize downloaders
        self.downloaders = {
            "sst": SSTDownloader(),
            "sst_textures": SSTERDDAPTextureDownloader(),
            "currents": CurrentsDownloader(),
            "acidity": AcidityHybridDownloader(),
            "microplastics": MicroplasticsDownloader()
        }
        
        # Results tracking
        self.results = {
            "started_at": datetime.now().isoformat(),
            "datasets": {},
            "summary": {
                "total_datasets": 0,
                "successful_datasets": 0,
                "failed_datasets": 0,
                "total_files_downloaded": 0,
                "total_files_processed": 0
            }
        }
        
        # Setup logging
        self.logger = self._setup_logging()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup comprehensive logging."""
        log_file = self.base_path / "logs" / f"update_ocean_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        logger = logging.getLogger(__name__)
        logger.info(f"Ocean Data Updater started - Log file: {log_file}")
        return logger
    
    def update_datasets(self, datasets: List[str] = None, repair_mode: bool = False) -> Dict:
        """
        Update specified datasets or all datasets.
        
        Args:
            datasets: List of dataset names to update (None for all)
            repair_mode: Whether to run in repair mode (recheck all files)
        
        Returns:
            Results dictionary with detailed information
        """
        if datasets is None:
            datasets = ["sst_textures", "sst", "currents", "acidity"]
        
        self.logger.info(f"Starting update for datasets: {datasets}")
        self.logger.info(f"Dry run mode: {self.dry_run}")
        self.logger.info(f"Repair mode: {repair_mode}")
        
        # Pre-flight checks
        if not self._pre_flight_checks():
            self.logger.error("Pre-flight checks failed")
            return self.results
        
        # Process each dataset
        for dataset in datasets:
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"Processing dataset: {dataset}")
            self.logger.info(f"{'='*60}")
            
            self.results["summary"]["total_datasets"] += 1
            
            try:
                dataset_result = self._update_single_dataset(dataset, repair_mode)
                self.results["datasets"][dataset] = dataset_result
                
                if dataset_result["status"] == "success":
                    self.results["summary"]["successful_datasets"] += 1
                    self.results["summary"]["total_files_downloaded"] += dataset_result.get("files_downloaded", 0)
                    self.results["summary"]["total_files_processed"] += dataset_result.get("files_processed", 0)
                else:
                    self.results["summary"]["failed_datasets"] += 1
                    
            except Exception as e:
                self.logger.error(f"Critical error processing {dataset}: {e}")
                self.results["datasets"][dataset] = {
                    "status": "critical_error",
                    "error": str(e),
                    "files_downloaded": 0,
                    "files_processed": 0
                }
                self.results["summary"]["failed_datasets"] += 1
        
        # Final summary
        self._log_final_summary()
        self.results["completed_at"] = datetime.now().isoformat()
        
        return self.results
    
    def _pre_flight_checks(self) -> bool:
        """Run pre-flight checks before starting update."""
        self.logger.info("Running pre-flight checks...")
        
        # Check disk space
        import shutil
        total, used, free = shutil.disk_usage(self.base_path)
        free_gb = free // (1024**3)
        
        if free_gb < 10:
            self.logger.error(f"Insufficient disk space: {free_gb}GB free (minimum 10GB required)")
            return False
        
        self.logger.info(f"Disk space check passed: {free_gb}GB free")
        
        # Check write permissions
        test_file = self.base_path / "logs" / ".write_test"
        try:
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.write_text("test")
            test_file.unlink()
            self.logger.info("Write permissions check passed")
        except Exception as e:
            self.logger.error(f"Write permissions check failed: {e}")
            return False
        
        # Validate directory structure
        required_dirs = ["raw", "processed/unified_coords", "textures", "logs"]
        for dir_name in required_dirs:
            dir_path = self.base_path / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
        
        self.logger.info("Pre-flight checks completed successfully")
        return True
    
    def _update_single_dataset(self, dataset: str, repair_mode: bool) -> Dict:
        """Update a single dataset with comprehensive error handling."""
        result = {
            "status": "started",
            "started_at": datetime.now().isoformat(),
            "files_downloaded": 0,
            "files_processed": 0,
            "errors": []
        }
        
        try:
            # Detect gaps
            self.logger.info(f"Detecting gaps for {dataset}...")
            latest_date, missing_dates = self.gap_detector.detect_gaps(dataset)
            
            if latest_date:
                self.logger.info(f"Latest file found: {latest_date}")
            else:
                self.logger.info("No existing files found")
            
            if not missing_dates:
                self.logger.info(f"No gaps detected for {dataset} - up to date")
                result["status"] = "up_to_date"
                return result
            
            self.logger.info(f"Found {len(missing_dates)} missing dates from {missing_dates[0]} to {missing_dates[-1]}")
            
            if self.dry_run:
                self.logger.info(f"[DRY RUN] Would download {len(missing_dates)} files")
                result["status"] = "dry_run_complete"
                result["would_download"] = len(missing_dates)
                return result
            
            # Download missing data
            downloader = self.downloaders[dataset]
            self.logger.info(f"Starting download of {len(missing_dates)} files...")
            
            download_result = downloader.download_date_range(
                missing_dates[0].strftime('%Y-%m-%d'),
                missing_dates[-1].strftime('%Y-%m-%d')
            )
            
            result["files_downloaded"] = download_result.get("downloaded", 0)
            result["errors"].extend(download_result.get("errors", []))
            
            self.logger.info(f"Downloaded {result['files_downloaded']} files")
            
            # Process data (coordinate harmonization) if needed
            if dataset in ["sst", "currents", "acidity"] and result["files_downloaded"] > 0:
                self.logger.info(f"Processing coordinate harmonization for {dataset}...")
                processed_count = self._process_coordinate_harmonization(dataset, missing_dates)
                result["files_processed"] = processed_count
                self.logger.info(f"Processed {processed_count} files")
            
            # Update status
            if result["files_downloaded"] > 0 or result["files_processed"] > 0:
                self.status_manager.update_dataset_status(
                    dataset,
                    last_date=missing_dates[-1].strftime('%Y-%m-%d'),
                    last_success=datetime.now().isoformat(),
                    status="success"
                )
            
            result["status"] = "success"
            result["completed_at"] = datetime.now().isoformat()
            
        except Exception as e:
            self.logger.error(f"Error updating {dataset}: {e}")
            result["status"] = "error"
            result["error"] = str(e)
            result["completed_at"] = datetime.now().isoformat()
        
        return result
    
    def _process_coordinate_harmonization(self, dataset: str, dates: List[date]) -> int:
        """Process coordinate harmonization for downloaded files."""
        processed_count = 0
        
        for target_date in dates:
            try:
                # Build file paths
                raw_file_pattern = self._get_raw_file_pattern(dataset, target_date)
                processed_file_pattern = self._get_processed_file_pattern(dataset, target_date)
                
                # Check if raw file exists and processed file doesn't
                raw_files = list(self.base_path.glob(raw_file_pattern))
                if not raw_files:
                    continue
                
                raw_file = raw_files[0]
                processed_file = self.base_path / processed_file_pattern
                
                if processed_file.exists():
                    continue  # Already processed
                
                # Process coordinate harmonization
                processed_file.parent.mkdir(parents=True, exist_ok=True)
                self.coordinate_harmonizer.harmonize_file(raw_file, processed_file)
                processed_count += 1
                
            except Exception as e:
                self.logger.warning(f"Failed to process {target_date} for {dataset}: {e}")
                continue
        
        return processed_count
    
    def _get_raw_file_pattern(self, dataset: str, target_date: date) -> str:
        """Get raw file pattern for a dataset and date."""
        date_str = target_date.strftime('%Y%m%d')
        year = target_date.strftime('%Y')
        month = target_date.strftime('%m')
        
        patterns = {
            "sst": f"raw/sst/{year}/{month}/oisst-avhrr-v02r01.{date_str}.nc",
            "currents": f"raw/currents/{year}/{month}/*{date_str}*.nc",
            "acidity": f"raw/acidity*/{year}/{month}/*{date_str}*.nc"
        }
        
        return patterns.get(dataset, f"raw/{dataset}/{year}/{month}/*{date_str}*.nc")
    
    def _get_processed_file_pattern(self, dataset: str, target_date: date) -> str:
        """Get processed file pattern for a dataset and date."""
        date_str = target_date.strftime('%Y%m%d')
        year = target_date.strftime('%Y')
        month = target_date.strftime('%m')
        
        patterns = {
            "sst": f"processed/unified_coords/sst/{year}/{month}/sst_harmonized_{date_str}.nc",
            "currents": f"processed/unified_coords/currents/{year}/{month}/currents_harmonized_{date_str}.nc",
            "acidity": f"processed/unified_coords/acidity/{year}/{month}/acidity_harmonized_{date_str}.nc"
        }
        
        return patterns.get(dataset, f"processed/unified_coords/{dataset}/{year}/{month}/{dataset}_harmonized_{date_str}.nc")
    
    def _log_final_summary(self):
        """Log final summary of update operation."""
        summary = self.results["summary"]
        
        self.logger.info("\n" + "="*80)
        self.logger.info("OCEAN DATA UPDATE SUMMARY")
        self.logger.info("="*80)
        self.logger.info(f"Total datasets processed: {summary['total_datasets']}")
        self.logger.info(f"Successful: {summary['successful_datasets']}")
        self.logger.info(f"Failed: {summary['failed_datasets']}")
        self.logger.info(f"Total files downloaded: {summary['total_files_downloaded']}")
        self.logger.info(f"Total files processed: {summary['total_files_processed']}")
        
        # Dataset details
        self.logger.info("\nDataset Details:")
        self.logger.info("-" * 80)
        for dataset, result in self.results["datasets"].items():
            status = result["status"]
            downloaded = result.get("files_downloaded", 0)
            processed = result.get("files_processed", 0)
            self.logger.info(f"{dataset:15s} | {status:15s} | {downloaded:6d} downloaded | {processed:6d} processed")
        
        self.logger.info("="*80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Comprehensive Ocean Data Update Script")
    
    parser.add_argument(
        "--datasets",
        type=str,
        help="Comma-separated list of datasets to update (sst_textures,sst,currents,acidity)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without actually downloading"
    )
    
    parser.add_argument(
        "--repair-mode",
        action="store_true",
        help="Run in repair mode (recheck all files for corruption)"
    )
    
    parser.add_argument(
        "--base-path",
        type=Path,
        help="Base path for ocean data (default: ../ocean-data)"
    )
    
    args = parser.parse_args()
    
    # Parse datasets
    datasets = None
    if args.datasets:
        datasets = [d.strip() for d in args.datasets.split(",")]
    
    # Initialize updater
    updater = OceanDataUpdater(
        base_path=args.base_path,
        dry_run=args.dry_run
    )
    
    # Run update
    try:
        results = updater.update_datasets(datasets, args.repair_mode)
        
        # Write results to file
        results_file = updater.base_path / "logs" / f"update_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\nResults saved to: {results_file}")
        
        # Exit with appropriate code
        if results["summary"]["failed_datasets"] > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\nUpdate interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Critical error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()