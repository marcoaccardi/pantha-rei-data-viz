#!/usr/bin/env python3
"""
Repair script for corrupted NetCDF files.
Identifies corrupted files from processing logs and redownloads them.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, date
import re
import xarray as xr
from typing import List, Dict, Set

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from downloaders.acidity_historical_downloader import AcidityHistoricalDownloader
from downloaders.acidity_current_downloader import AcidityCurrentDownloader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CorruptedFileRepairer:
    """Repairs corrupted NetCDF files by redownloading them."""
    
    def __init__(self):
        """Initialize the repairer."""
        self.raw_data_path = Path("../ocean-data/raw")
        self.processed_data_path = Path("../ocean-data/processed")
        
        # Initialize downloaders
        try:
            self.acidity_historical_downloader = AcidityHistoricalDownloader()
            self.acidity_current_downloader = AcidityCurrentDownloader()
            logger.info("Initialized downloaders successfully")
        except Exception as e:
            logger.error(f"Failed to initialize downloaders: {e}")
            raise
    
    def identify_corrupted_files(self, dataset: str = "acidity_historical") -> List[Path]:
        """
        Identify corrupted NetCDF files by trying to open them.
        
        Args:
            dataset: Dataset name to check
            
        Returns:
            List of corrupted file paths
        """
        logger.info(f"Scanning for corrupted {dataset} files...")
        
        dataset_path = self.raw_data_path / dataset
        if not dataset_path.exists():
            logger.warning(f"Dataset path does not exist: {dataset_path}")
            return []
        
        corrupted_files = []
        all_nc_files = list(dataset_path.rglob("*.nc"))
        
        logger.info(f"Found {len(all_nc_files)} NetCDF files to check")
        
        for i, nc_file in enumerate(all_nc_files, 1):
            try:
                # Try to open the file with xarray
                with xr.open_dataset(nc_file) as ds:
                    # Basic validation - try to access coordinate info
                    _ = list(ds.dims.keys())
                    _ = list(ds.coords.keys())
                    
                # If we get here, file is readable
                if i % 1000 == 0:
                    logger.info(f"Progress: {i}/{len(all_nc_files)} - File OK: {nc_file.name}")
                    
            except Exception as e:
                error_str = str(e)
                if any(x in error_str.lower() for x in ['hdf error', 'netcdf', 'did not find a match', 'bad magic number']):
                    corrupted_files.append(nc_file)
                    logger.warning(f"Corrupted file detected: {nc_file.name} - {error_str[:100]}...")
                else:
                    logger.error(f"Unexpected error reading {nc_file.name}: {error_str[:100]}...")
        
        logger.info(f"Found {len(corrupted_files)} corrupted files out of {len(all_nc_files)}")
        return corrupted_files
    
    def extract_date_from_filename(self, file_path: Path) -> date:
        """
        Extract date from acidity filename.
        
        Args:
            file_path: Path to the NetCDF file
            
        Returns:
            Date object
        """
        # Pattern: acidity_historical_YYYYMMDD.nc or similar
        filename = file_path.name
        
        # Look for YYYYMMDD pattern
        date_match = re.search(r'(\d{8})', filename)
        if date_match:
            date_str = date_match.group(1)
            try:
                return datetime.strptime(date_str, '%Y%m%d').date()
            except ValueError:
                pass
        
        # Alternative patterns
        date_match = re.search(r'(\d{4})(\d{2})(\d{2})', filename)
        if date_match:
            year, month, day = date_match.groups()
            try:
                return date(int(year), int(month), int(day))
            except ValueError:
                pass
        
        raise ValueError(f"Cannot extract date from filename: {filename}")
    
    def backup_corrupted_file(self, file_path: Path) -> Path:
        """
        Backup a corrupted file before redownloading.
        
        Args:
            file_path: Path to corrupted file
            
        Returns:
            Path to backup file
        """
        backup_dir = file_path.parent / "corrupted_backup"
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"{file_path.stem}_{timestamp}.corrupted"
        
        file_path.rename(backup_path)
        logger.info(f"Backed up corrupted file: {backup_path}")
        
        return backup_path
    
    def redownload_file(self, file_path: Path, target_date: date) -> bool:
        """
        Redownload a specific file.
        
        Args:
            file_path: Original file path
            target_date: Date to download
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Determine which downloader to use based on path
            if "acidity_historical" in str(file_path):
                downloader = self.acidity_historical_downloader
                logger.info(f"Using historical downloader for {target_date}")
            elif "acidity_current" in str(file_path) or "acidity" in str(file_path):
                downloader = self.acidity_current_downloader  
                logger.info(f"Using current downloader for {target_date}")
            else:
                logger.error(f"Unknown dataset type for file: {file_path}")
                return False
            
            # Download the file
            success = downloader.download_date(target_date)
            
            if success:
                logger.info(f"✓ Successfully redownloaded data for {target_date}")
                
                # Verify the new file is not corrupted
                new_file_candidates = list(file_path.parent.glob(f"*{target_date.strftime('%Y%m%d')}*"))
                for candidate in new_file_candidates:
                    try:
                        with xr.open_dataset(candidate) as ds:
                            _ = list(ds.dims.keys())
                        logger.info(f"✓ Verified new file is readable: {candidate.name}")
                        return True
                    except Exception as e:
                        logger.warning(f"New file still corrupted: {candidate.name} - {e}")
                        
            else:
                logger.error(f"✗ Failed to redownload data for {target_date}")
                return False
                
        except Exception as e:
            logger.error(f"Error redownloading {target_date}: {e}")
            return False
        
        return False
    
    def repair_corrupted_files(self, dataset: str = "acidity_historical", 
                              max_files: int = None) -> Dict[str, int]:
        """
        Repair all corrupted files in a dataset.
        
        Args:
            dataset: Dataset name to repair
            max_files: Maximum number of files to repair (None for all)
            
        Returns:
            Dictionary with repair statistics
        """
        logger.info("="*60)
        logger.info(f"CORRUPTED FILE REPAIR - {dataset.upper()}")
        logger.info("="*60)
        
        # Find corrupted files
        corrupted_files = self.identify_corrupted_files(dataset)
        
        if not corrupted_files:
            logger.info("No corrupted files found!")
            return {"total": 0, "successful": 0, "failed": 0}
        
        # Limit number of files if specified
        if max_files:
            corrupted_files = corrupted_files[:max_files]
            logger.info(f"Limited repair to first {max_files} corrupted files")
        
        results = {
            "total": len(corrupted_files),
            "successful": 0,
            "failed": 0,
            "errors": []
        }
        
        for i, corrupted_file in enumerate(corrupted_files, 1):
            logger.info(f"Repairing {i}/{len(corrupted_files)}: {corrupted_file.name}")
            
            try:
                # Extract date from filename
                target_date = self.extract_date_from_filename(corrupted_file)
                logger.info(f"Extracted date: {target_date}")
                
                # Backup the corrupted file
                backup_path = self.backup_corrupted_file(corrupted_file)
                
                # Redownload the file
                success = self.redownload_file(corrupted_file, target_date)
                
                if success:
                    results["successful"] += 1
                    logger.info(f"✓ Repaired: {corrupted_file.name}")
                    
                    # Remove backup if repair successful
                    if backup_path.exists():
                        backup_path.unlink()
                        logger.info(f"Removed backup: {backup_path}")
                else:
                    results["failed"] += 1
                    results["errors"].append(f"Failed to repair {corrupted_file.name}")
                    logger.error(f"✗ Failed to repair: {corrupted_file.name}")
                    
                    # Restore from backup if repair failed
                    if backup_path.exists() and not corrupted_file.exists():
                        backup_path.rename(corrupted_file)
                        logger.info(f"Restored from backup: {corrupted_file.name}")
                        
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"Error processing {corrupted_file.name}: {str(e)}")
                logger.error(f"Error processing {corrupted_file.name}: {e}")
        
        # Summary
        logger.info("="*60)
        logger.info("REPAIR SUMMARY")
        logger.info("="*60)
        logger.info(f"Total files processed: {results['total']}")
        logger.info(f"Successfully repaired: {results['successful']}")
        logger.info(f"Failed repairs: {results['failed']}")
        
        if results["errors"]:
            logger.info("Errors encountered:")
            for error in results["errors"][:10]:  # Show first 10 errors
                logger.error(f"  - {error}")
        
        return results

def main():
    """Main function."""
    repairer = CorruptedFileRepairer()
    
    # Repair acidity_historical files
    logger.info("Starting corrupted file repair process...")
    
    # Start with a small batch for testing
    results = repairer.repair_corrupted_files(
        dataset="acidity_historical", 
        max_files=10  # Start with 10 files for testing
    )
    
    if results["successful"] > 0:
        logger.info(f"Successfully repaired {results['successful']} files!")
        
        # Ask if user wants to continue with all files
        logger.info("Test repair successful. To repair all corrupted files, run:")
        logger.info("python scripts/maintenance/repair_corrupted_files.py --all")
    else:
        logger.warning("No files were successfully repaired. Check credentials and network connection.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Repair corrupted NetCDF files")
    parser.add_argument("--all", action="store_true", help="Repair all corrupted files (not just first 10)")
    parser.add_argument("--dataset", default="acidity_historical", help="Dataset to repair")
    parser.add_argument("--max-files", type=int, help="Maximum files to repair")
    
    args = parser.parse_args()
    
    repairer = CorruptedFileRepairer()
    
    max_files = None if args.all else (args.max_files or 10)
    
    results = repairer.repair_corrupted_files(
        dataset=args.dataset,
        max_files=max_files
    )