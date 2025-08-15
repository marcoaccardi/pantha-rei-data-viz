#!/usr/bin/env python3
"""
Error Recovery Manager for Ocean Data

Handles comprehensive error recovery including:
- Redownloading corrupted files
- Reprocessing failed coordinate harmonization
- Cleaning up partial downloads
- Automatic retry with exponential backoff
"""

import sys
import logging
import time
import json
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
import shutil
import xarray as xr
from dataclasses import dataclass
import traceback

# Add backend to path (now two levels up since we're in scripts/production/)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.production.file_validator import FileValidator
from utils.status_manager import StatusManager
from downloaders.sst_downloader import SSTDownloader
from downloaders.sst_erddap_texture_downloader import SSTERDDAPTextureDownloader
from downloaders.currents_downloader import CurrentsDownloader
from downloaders.acidity_hybrid_downloader import AcidityHybridDownloader
from downloaders.microplastics_downloader import MicroplasticsDownloader
from processors.coordinate_harmonizer import CoordinateHarmonizer

@dataclass
class RecoveryTask:
    """Represents a recovery task."""
    task_id: str
    task_type: str  # 'redownload', 'reprocess', 'cleanup'
    dataset: str
    file_path: Path
    target_date: Optional[date] = None
    errors: List[str] = None
    attempts: int = 0
    max_attempts: int = 3
    created_at: datetime = None
    last_attempt: Optional[datetime] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.created_at is None:
            self.created_at = datetime.now()

class RecoveryManager:
    """Manages comprehensive error recovery for ocean data."""
    
    def __init__(self, base_path: Optional[Path] = None):
        """Initialize recovery manager."""
        self.base_path = base_path or Path(__file__).parent.parent.parent / "ocean-data"
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.file_validator = FileValidator(self.base_path)
        self.status_manager = StatusManager()
        self.coordinate_harmonizer = CoordinateHarmonizer()
        
        # Initialize downloaders (exclude acidity_historical and waves)
        self.downloaders = {
            "sst": SSTDownloader(),
            "sst_textures": SSTERDDAPTextureDownloader(),
            "currents": CurrentsDownloader(), 
            "acidity": AcidityHybridDownloader()
        }
        
        # Recovery tracking
        self.recovery_log_path = self.base_path / "logs" / "recovery"
        self.recovery_log_path.mkdir(parents=True, exist_ok=True)
        
        self.active_tasks: List[RecoveryTask] = []
        self.completed_tasks: List[RecoveryTask] = []
        self.failed_tasks: List[RecoveryTask] = []
        
        # Recovery statistics
        self.stats = {
            "started_at": datetime.now().isoformat(),
            "files_recovered": 0,
            "files_reprocessed": 0,
            "cleanup_operations": 0,
            "total_errors_fixed": 0
        }
    
    def scan_and_recover(self, datasets: List[str] = None, repair_mode: bool = False) -> Dict:
        """
        Scan for issues and recover automatically.
        
        Args:
            datasets: List of datasets to check (None for all)
            repair_mode: If True, revalidate all files aggressively
        
        Returns:
            Recovery results dictionary
        """
        if datasets is None:
            datasets = ["sst", "currents", "acidity", "sst_textures"]
        
        self.logger.info(f"Starting recovery scan for datasets: {datasets}")
        self.logger.info(f"Repair mode: {repair_mode}")
        
        # Step 1: Find corrupted files
        self.logger.info("Step 1: Scanning for corrupted files...")
        corrupted_files = self._find_corrupted_files(datasets)
        
        # Step 2: Find missing processed files
        self.logger.info("Step 2: Checking for missing processed files...")
        missing_processed = self._find_missing_processed_files(datasets)
        
        # Step 3: Clean up partial downloads
        self.logger.info("Step 3: Cleaning up partial downloads...")
        partial_downloads = self._find_partial_downloads(datasets)
        
        # Create recovery tasks
        self._create_recovery_tasks(corrupted_files, missing_processed, partial_downloads)
        
        if not self.active_tasks:
            self.logger.info("No recovery tasks needed - all data appears healthy")
            return self._generate_recovery_report()
        
        self.logger.info(f"Created {len(self.active_tasks)} recovery tasks")
        
        # Execute recovery tasks
        self._execute_recovery_tasks()
        
        # Final validation
        self.logger.info("Running final validation...")
        final_issues = self._final_validation_check(datasets)
        
        if final_issues:
            self.logger.warning(f"Some issues remain after recovery: {final_issues}")
        else:
            self.logger.info("Recovery completed successfully - all issues resolved")
        
        return self._generate_recovery_report()
    
    def _find_corrupted_files(self, datasets: List[str]) -> Dict[str, List[Path]]:
        """Find corrupted files across datasets."""
        corrupted_files = {}
        
        for dataset in datasets:
            self.logger.info(f"Scanning {dataset} for corrupted files...")
            
            corrupted_result = self.file_validator.find_corrupted_files(dataset)
            
            if dataset in corrupted_result:
                file_paths = []
                for file_info in corrupted_result[dataset]:
                    file_path = self.base_path / file_info["file_path"]
                    file_paths.append(file_path)
                
                corrupted_files[dataset] = file_paths
                self.logger.warning(f"Found {len(file_paths)} corrupted files in {dataset}")
        
        return corrupted_files
    
    def _find_missing_processed_files(self, datasets: List[str]) -> Dict[str, List[Tuple[Path, Path]]]:
        """Find raw files that don't have corresponding processed files."""
        missing_processed = {}
        
        for dataset in datasets:
            if dataset in ["sst_textures", "microplastics", "acidity_historical", "waves"]:
                continue  # These don't need processing or are excluded
                
            self.logger.info(f"Checking processed files for {dataset}...")
            
            raw_path = self.base_path / "raw" / dataset
            processed_path = self.base_path / "processed" / "unified_coords" / dataset
            
            if not raw_path.exists():
                continue
            
            missing_pairs = []
            
            # Find raw files without corresponding processed files
            for raw_file in raw_path.rglob("*.nc"):
                # Construct expected processed file path
                rel_path = raw_file.relative_to(raw_path)
                processed_file = processed_path / rel_path.parent / f"{rel_path.stem}_harmonized.nc"
                
                if not processed_file.exists():
                    missing_pairs.append((raw_file, processed_file))
            
            if missing_pairs:
                missing_processed[dataset] = missing_pairs
                self.logger.info(f"Found {len(missing_pairs)} files needing processing in {dataset}")
        
        return missing_processed
    
    def _find_partial_downloads(self, datasets: List[str]) -> Dict[str, List[Path]]:
        """Find partial or temporary download files."""
        partial_downloads = {}
        
        for dataset in datasets:
            self.logger.info(f"Scanning {dataset} for partial downloads...")
            
            dataset_paths = []
            
            # Check raw data directory
            raw_path = self.base_path / "raw" / dataset
            if raw_path.exists():
                dataset_paths.append(raw_path)
            
            # Check texture directory for sst_textures
            if dataset == "sst_textures":
                texture_path = self.base_path / "textures" / "sst"
                if texture_path.exists():
                    dataset_paths.append(texture_path)
            
            partial_files = []
            
            for search_path in dataset_paths:
                # Find temporary files
                temp_patterns = ["*.tmp", "*.temp", "*.partial", "*~", "*.downloading"]
                for pattern in temp_patterns:
                    partial_files.extend(search_path.rglob(pattern))
                
                # Find very small files that might be incomplete
                for file_path in search_path.rglob("*"):
                    if file_path.is_file() and file_path.stat().st_size < 1024:  # Less than 1KB
                        if file_path.suffix in [".nc", ".png"]:
                            partial_files.append(file_path)
            
            if partial_files:
                partial_downloads[dataset] = partial_files
                self.logger.warning(f"Found {len(partial_files)} partial downloads in {dataset}")
        
        return partial_downloads
    
    def _create_recovery_tasks(self, corrupted_files: Dict, missing_processed: Dict, partial_downloads: Dict):
        """Create recovery tasks from identified issues."""
        task_id_counter = 1
        
        # Tasks for corrupted files (redownload)
        for dataset, file_paths in corrupted_files.items():
            for file_path in file_paths:
                target_date = self._extract_date_from_path(file_path)
                
                task = RecoveryTask(
                    task_id=f"redown_{task_id_counter:04d}",
                    task_type="redownload",
                    dataset=dataset,
                    file_path=file_path,
                    target_date=target_date,
                    errors=["File corrupted or invalid"]
                )
                self.active_tasks.append(task)
                task_id_counter += 1
        
        # Tasks for missing processed files (reprocess)
        for dataset, file_pairs in missing_processed.items():
            for raw_file, processed_file in file_pairs:
                target_date = self._extract_date_from_path(raw_file)
                
                task = RecoveryTask(
                    task_id=f"reproc_{task_id_counter:04d}",
                    task_type="reprocess",
                    dataset=dataset,
                    file_path=processed_file,
                    target_date=target_date,
                    errors=["Missing processed file"]
                )
                self.active_tasks.append(task)
                task_id_counter += 1
        
        # Tasks for partial downloads (cleanup + redownload)
        for dataset, file_paths in partial_downloads.items():
            for file_path in file_paths:
                target_date = self._extract_date_from_path(file_path)
                
                task = RecoveryTask(
                    task_id=f"clean_{task_id_counter:04d}",
                    task_type="cleanup",
                    dataset=dataset,
                    file_path=file_path,
                    target_date=target_date,
                    errors=["Partial or incomplete download"]
                )
                self.active_tasks.append(task)
                task_id_counter += 1
    
    def _execute_recovery_tasks(self):
        """Execute all recovery tasks with retry logic."""
        self.logger.info(f"Executing {len(self.active_tasks)} recovery tasks...")
        
        while self.active_tasks:
            task = self.active_tasks.pop(0)
            
            self.logger.info(f"Executing task {task.task_id}: {task.task_type} for {task.dataset}")
            
            try:
                success = self._execute_single_task(task)
                
                if success:
                    self.completed_tasks.append(task)
                    self.logger.info(f"Task {task.task_id} completed successfully")
                else:
                    task.attempts += 1
                    task.last_attempt = datetime.now()
                    
                    if task.attempts < task.max_attempts:
                        # Exponential backoff
                        delay = 2 ** task.attempts
                        self.logger.warning(f"Task {task.task_id} failed (attempt {task.attempts}), retrying in {delay}s...")
                        time.sleep(delay)
                        self.active_tasks.append(task)  # Re-queue for retry
                    else:
                        self.failed_tasks.append(task)
                        self.logger.error(f"Task {task.task_id} failed after {task.max_attempts} attempts")
                        
            except Exception as e:
                self.logger.error(f"Critical error executing task {task.task_id}: {e}")
                task.errors.append(f"Critical error: {e}")
                self.failed_tasks.append(task)
    
    def _execute_single_task(self, task: RecoveryTask) -> bool:
        """Execute a single recovery task."""
        try:
            if task.task_type == "redownload":
                return self._handle_redownload(task)
            elif task.task_type == "reprocess":
                return self._handle_reprocess(task)
            elif task.task_type == "cleanup":
                return self._handle_cleanup(task)
            else:
                self.logger.error(f"Unknown task type: {task.task_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error executing task {task.task_id}: {e}")
            task.errors.append(str(e))
            return False
    
    def _handle_redownload(self, task: RecoveryTask) -> bool:
        """Handle redownloading a corrupted file."""
        if not task.target_date:
            self.logger.error(f"Cannot redownload - no date extracted from {task.file_path}")
            return False
        
        # Remove corrupted file
        if task.file_path.exists():
            self.logger.info(f"Removing corrupted file: {task.file_path}")
            task.file_path.unlink()
        
        # Redownload
        downloader = self.downloaders.get(task.dataset)
        if not downloader:
            self.logger.error(f"No downloader available for dataset: {task.dataset}")
            return False
        
        self.logger.info(f"Redownloading {task.dataset} for date {task.target_date}")
        
        try:
            if task.dataset == "sst_textures":
                # Special handling for textures
                result = downloader.download_texture_for_date(task.target_date)
            else:
                # Regular data download
                date_str = task.target_date.strftime('%Y-%m-%d')
                result = downloader.download_date_range(date_str, date_str)
            
            if result.get("downloaded", 0) > 0:
                self.stats["files_recovered"] += 1
                
                # Validate the redownloaded file
                if task.file_path.exists():
                    validation_result = self.file_validator.validate_file(task.file_path, task.dataset)
                    if validation_result["is_valid"]:
                        self.logger.info(f"Redownloaded file validated successfully")
                        return True
                    else:
                        self.logger.warning(f"Redownloaded file still invalid: {validation_result['errors']}")
                        return False
                else:
                    self.logger.warning(f"File not found after download: {task.file_path}")
                    return False
            else:
                self.logger.warning(f"Download reported 0 files downloaded")
                return False
                
        except Exception as e:
            self.logger.error(f"Redownload failed: {e}")
            task.errors.append(f"Redownload failed: {e}")
            return False
    
    def _handle_reprocess(self, task: RecoveryTask) -> bool:
        """Handle reprocessing coordinate harmonization."""
        # Find the raw file
        raw_dataset_path = self.base_path / "raw" / task.dataset
        raw_file = None
        
        if task.target_date:
            # Look for raw file by date
            date_str = task.target_date.strftime('%Y%m%d')
            year = task.target_date.strftime('%Y')
            month = task.target_date.strftime('%m')
            
            search_pattern = f"{year}/{month}/*{date_str}*.nc"
            raw_files = list(raw_dataset_path.glob(search_pattern))
            
            if raw_files:
                raw_file = raw_files[0]
        
        if not raw_file or not raw_file.exists():
            self.logger.error(f"Cannot find raw file to reprocess for {task.file_path}")
            return False
        
        # Create processed file directory
        task.file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Remove existing processed file if any
        if task.file_path.exists():
            task.file_path.unlink()
        
        try:
            self.logger.info(f"Reprocessing {raw_file} -> {task.file_path}")
            
            # Run coordinate harmonization
            self.coordinate_harmonizer.harmonize_file(raw_file, task.file_path)
            
            # Validate processed file
            if task.file_path.exists():
                validation_result = self.file_validator.validate_file(task.file_path, task.dataset)
                if validation_result["is_valid"]:
                    self.stats["files_reprocessed"] += 1
                    self.logger.info(f"Reprocessing completed successfully")
                    return True
                else:
                    self.logger.warning(f"Reprocessed file invalid: {validation_result['errors']}")
                    return False
            else:
                self.logger.error(f"Processed file not created: {task.file_path}")
                return False
                
        except Exception as e:
            self.logger.error(f"Reprocessing failed: {e}")
            task.errors.append(f"Reprocessing failed: {e}")
            return False
    
    def _handle_cleanup(self, task: RecoveryTask) -> bool:
        """Handle cleaning up partial downloads."""
        try:
            if task.file_path.exists():
                self.logger.info(f"Removing partial download: {task.file_path}")
                task.file_path.unlink()
                self.stats["cleanup_operations"] += 1
            
            # If we have a target date, try to redownload
            if task.target_date:
                return self._handle_redownload(task)
            else:
                return True  # Just cleanup, no redownload needed
                
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
            task.errors.append(f"Cleanup failed: {e}")
            return False
    
    def _extract_date_from_path(self, file_path: Path) -> Optional[date]:
        """Extract date from file path."""
        import re
        
        # Look for date pattern in filename
        date_patterns = [
            r"(\d{8})",  # YYYYMMDD
            r"(\d{4})-(\d{2})-(\d{2})",  # YYYY-MM-DD
            r"(\d{4})(\d{2})(\d{2})"  # YYYYMMDD
        ]
        
        file_str = str(file_path)
        
        for pattern in date_patterns:
            match = re.search(pattern, file_str)
            if match:
                try:
                    if len(match.groups()) == 1:
                        # YYYYMMDD format
                        date_str = match.group(1)
                        return datetime.strptime(date_str, "%Y%m%d").date()
                    elif len(match.groups()) == 3:
                        # YYYY-MM-DD or YYYYMMDD format
                        year, month, day = match.groups()
                        return date(int(year), int(month), int(day))
                except ValueError:
                    continue
        
        return None
    
    def _final_validation_check(self, datasets: List[str]) -> List[str]:
        """Run final validation to check if all issues are resolved."""
        remaining_issues = []
        
        for dataset in datasets:
            self.logger.info(f"Final validation check for {dataset}...")
            
            # Quick corruption check
            corrupted = self.file_validator.find_corrupted_files(dataset)
            if corrupted:
                remaining_issues.append(f"{dataset}: {len(corrupted[dataset])} corrupted files remain")
            
            # Check for partial downloads again
            partial = self._find_partial_downloads([dataset])
            if dataset in partial:
                remaining_issues.append(f"{dataset}: {len(partial[dataset])} partial downloads remain")
        
        return remaining_issues
    
    def _generate_recovery_report(self) -> Dict:
        """Generate comprehensive recovery report."""
        report = {
            "recovery_session": {
                "started_at": self.stats["started_at"],
                "completed_at": datetime.now().isoformat(),
                "duration_minutes": (datetime.now() - datetime.fromisoformat(self.stats["started_at"])).total_seconds() / 60
            },
            "statistics": self.stats,
            "tasks": {
                "total_tasks": len(self.completed_tasks) + len(self.failed_tasks),
                "completed_successfully": len(self.completed_tasks),
                "failed": len(self.failed_tasks),
                "success_rate": len(self.completed_tasks) / (len(self.completed_tasks) + len(self.failed_tasks)) if (len(self.completed_tasks) + len(self.failed_tasks)) > 0 else 1.0
            },
            "completed_tasks": [
                {
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "dataset": task.dataset,
                    "file_path": str(task.file_path),
                    "attempts": task.attempts
                }
                for task in self.completed_tasks
            ],
            "failed_tasks": [
                {
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "dataset": task.dataset,
                    "file_path": str(task.file_path),
                    "attempts": task.attempts,
                    "errors": task.errors
                }
                for task in self.failed_tasks
            ]
        }
        
        # Save report
        report_file = self.recovery_log_path / f"recovery_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"Recovery report saved to: {report_file}")
        
        return report


def main():
    """Command line interface for recovery manager."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Ocean Data Recovery Manager")
    parser.add_argument("--datasets", 
                       help="Comma-separated list of datasets to recover")
    parser.add_argument("--repair-mode", action="store_true",
                       help="Run aggressive repair mode")
    parser.add_argument("--base-path", type=Path,
                       help="Base path for ocean data")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output")
    
    args = parser.parse_args()
    
    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Parse datasets
    datasets = None
    if args.datasets:
        datasets = [d.strip() for d in args.datasets.split(",")]
    
    # Initialize recovery manager
    recovery_manager = RecoveryManager(args.base_path)
    
    try:
        # Run recovery
        results = recovery_manager.scan_and_recover(datasets, args.repair_mode)
        
        # Print summary
        print(f"\nRecovery Summary:")
        print(f"Files recovered: {results['statistics']['files_recovered']}")
        print(f"Files reprocessed: {results['statistics']['files_reprocessed']}")
        print(f"Cleanup operations: {results['statistics']['cleanup_operations']}")
        print(f"Success rate: {results['tasks']['success_rate']:.1%}")
        
        if results["failed_tasks"]:
            print(f"\nFailed tasks: {len(results['failed_tasks'])}")
            for task in results["failed_tasks"]:
                print(f"  {task['task_id']}: {task['errors']}")
            sys.exit(1)
        else:
            print("\nAll recovery tasks completed successfully!")
            sys.exit(0)
            
    except Exception as e:
        print(f"Recovery failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()