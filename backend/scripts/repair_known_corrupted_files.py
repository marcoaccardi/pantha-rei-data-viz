#!/usr/bin/env python3
"""
Quick repair script for known corrupted NetCDF files.
Uses the error patterns from processing logs to identify and repair specific files.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, date
import xarray as xr
from typing import List

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from downloaders.acidity_historical_downloader import AcidityHistoricalDownloader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class QuickFileRepairer:
    """Quick repair for known corrupted files."""
    
    def __init__(self):
        """Initialize the repairer."""
        self.raw_data_path = Path("../ocean-data/raw")
        
        # Initialize downloader
        try:
            self.downloader = AcidityHistoricalDownloader()
            logger.info("Initialized acidity historical downloader")
        except Exception as e:
            logger.error(f"Failed to initialize downloader: {e}")
            raise
        
        # Known corrupted files from processing logs
        self.known_corrupted_files = [
            "acidity_historical_20070917.nc",
            "acidity_historical_20070918.nc", 
            "acidity_historical_20111030.nc",
            "acidity_historical_20111031.nc",
            "acidity_historical_20111101.nc",
            "acidity_historical_20120929.nc",
            "acidity_historical_20120930.nc",
            "acidity_historical_20121001.nc",
            "acidity_historical_20150402.nc",
            "acidity_historical_20150403.nc",
            "acidity_historical_20150404.nc"
        ]
    
    def extract_date_from_filename(self, filename: str) -> date:
        """Extract date from filename."""
        # Pattern: acidity_historical_YYYYMMDD.nc
        date_str = filename.replace("acidity_historical_", "").replace(".nc", "")
        try:
            return datetime.strptime(date_str, '%Y%m%d').date()
        except ValueError:
            raise ValueError(f"Cannot extract date from filename: {filename}")
    
    def find_file_path(self, filename: str) -> Path:
        """Find the full path of a corrupted file."""
        # Search in acidity_historical directory
        search_path = self.raw_data_path / "acidity_historical"
        
        # Search recursively
        for file_path in search_path.rglob(filename):
            return file_path
        
        raise FileNotFoundError(f"File not found: {filename}")
    
    def backup_and_redownload(self, filename: str) -> bool:
        """Backup corrupted file and redownload."""
        try:
            # Find the file
            file_path = self.find_file_path(filename)
            logger.info(f"Found file: {file_path}")
            
            # Extract date
            target_date = self.extract_date_from_filename(filename)
            logger.info(f"Target date: {target_date}")
            
            # Create backup directory
            backup_dir = file_path.parent / "corrupted_backup"
            backup_dir.mkdir(exist_ok=True)
            
            # Backup the corrupted file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"{file_path.stem}_{timestamp}.corrupted"
            file_path.rename(backup_path)
            logger.info(f"Backed up to: {backup_path}")
            
            # Redownload
            logger.info(f"Redownloading data for {target_date}...")
            success = self.downloader.download_date(target_date)
            
            if success:
                # Verify new file
                new_file_candidates = list(file_path.parent.glob(f"*{target_date.strftime('%Y%m%d')}*"))
                for candidate in new_file_candidates:
                    try:
                        with xr.open_dataset(candidate) as ds:
                            _ = list(ds.coords.keys())
                        logger.info(f"✓ Successfully repaired: {filename}")
                        
                        # Remove backup since repair was successful
                        backup_path.unlink()
                        logger.info(f"Removed backup: {backup_path}")
                        return True
                    except Exception as e:
                        logger.warning(f"New file still corrupted: {candidate.name}")
            
            # If we reach here, redownload failed - restore backup
            if backup_path.exists():
                backup_path.rename(file_path)
                logger.warning(f"Restored backup - redownload failed")
            
            return False
            
        except FileNotFoundError:
            logger.warning(f"File not found (may already be processed): {filename}")
            return False
        except Exception as e:
            logger.error(f"Error repairing {filename}: {e}")
            return False
    
    def repair_known_files(self) -> dict:
        """Repair all known corrupted files."""
        logger.info("="*60)
        logger.info("QUICK REPAIR FOR KNOWN CORRUPTED FILES")
        logger.info("="*60)
        
        results = {
            "total": len(self.known_corrupted_files),
            "successful": 0,
            "failed": 0,
            "not_found": 0
        }
        
        for i, filename in enumerate(self.known_corrupted_files, 1):
            logger.info(f"Repairing {i}/{len(self.known_corrupted_files)}: {filename}")
            
            try:
                success = self.backup_and_redownload(filename)
                if success:
                    results["successful"] += 1
                    logger.info(f"✓ Successfully repaired: {filename}")
                else:
                    results["failed"] += 1
                    logger.error(f"✗ Failed to repair: {filename}")
                    
            except FileNotFoundError:
                results["not_found"] += 1
                logger.warning(f"? File not found: {filename}")
            except Exception as e:
                results["failed"] += 1
                logger.error(f"✗ Error with {filename}: {e}")
        
        # Summary
        logger.info("="*60)
        logger.info("REPAIR SUMMARY")
        logger.info("="*60)
        logger.info(f"Total files: {results['total']}")
        logger.info(f"Successfully repaired: {results['successful']}")
        logger.info(f"Failed repairs: {results['failed']}")
        logger.info(f"Files not found: {results['not_found']}")
        
        return results

def main():
    """Main function."""
    repairer = QuickFileRepairer()
    results = repairer.repair_known_files()
    
    if results["successful"] > 0:
        logger.info(f"Successfully repaired {results['successful']} corrupted files!")
        logger.info("You can now re-run the comprehensive processing script.")
    else:
        logger.warning("No files were repaired. Check logs for details.")

if __name__ == "__main__":
    main()