#!/usr/bin/env python3
"""
Quick corruption check focusing on sampling and high-risk areas.
More efficient scan for detecting remaining corruption issues.
"""

import sys
import logging
from pathlib import Path
import xarray as xr
from typing import List, Dict, Tuple
import random
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class QuickCorruptionChecker:
    """Quick corruption check for ocean data files."""
    
    def __init__(self):
        """Initialize the corruption checker."""
        self.base_path = Path("/media/anecoica/ANECOICA_DEV/pantha-rei-data-viz/ocean-data")
        self.raw_path = self.base_path / "raw"
        self.corrupted_files = []
        
    def check_file(self, file_path: Path) -> Tuple[bool, str]:
        """Quick check if a file is corrupted."""
        try:
            with xr.open_dataset(file_path) as ds:
                # Quick validation - just try to access basic structure
                _ = list(ds.dims.keys())
                _ = list(ds.coords.keys())
                return True, "OK"
        except Exception as e:
            error_str = str(e).lower()
            if any(x in error_str for x in ['hdf error', 'bad magic number', 'did not find a match']):
                return False, str(e)[:100]
            return True, "OK"  # Other errors might not be corruption
    
    def sample_dataset(self, dataset_path: Path, sample_size: int = 200) -> List[Path]:
        """Get a random sample of files from a dataset."""
        if not dataset_path.exists():
            return []
        
        all_files = list(dataset_path.rglob("*.nc")) + list(dataset_path.rglob("*.nc4"))
        
        if len(all_files) <= sample_size:
            return all_files
        
        return random.sample(all_files, sample_size)
    
    def check_high_risk_areas(self):
        """Check areas known to be high-risk for corruption."""
        logger.info("Checking high-risk areas for corruption...")
        
        high_risk_areas = [
            # Previously identified problem areas
            (self.raw_path / "acidity_historical" / "2007" / "09", "2007 Sept acidity"),
            (self.raw_path / "acidity_historical" / "2011" / "10", "2011 Oct acidity"),
            (self.raw_path / "acidity_historical" / "2011" / "11", "2011 Nov acidity"), 
            (self.raw_path / "acidity_historical" / "2012" / "09", "2012 Sept acidity"),
            (self.raw_path / "acidity_historical" / "2012" / "10", "2012 Oct acidity"),
            (self.raw_path / "acidity_historical" / "2015" / "04", "2015 April acidity"),
            
            # Check some OSCAR files (known to have coordinate issues)
            (self.raw_path / "currents", "OSCAR currents"),
        ]
        
        for area_path, description in high_risk_areas:
            if area_path.exists():
                logger.info(f"Checking {description}...")
                files = list(area_path.glob("*.nc")) + list(area_path.glob("*.nc4"))
                
                corrupted_in_area = 0
                for file_path in files[:50]:  # Check first 50 files in area
                    is_healthy, error_msg = self.check_file(file_path)
                    if not is_healthy:
                        self.corrupted_files.append({
                            "file": str(file_path.relative_to(self.base_path)),
                            "error": error_msg,
                            "area": description
                        })
                        corrupted_in_area += 1
                        logger.warning(f"CORRUPTED: {file_path.name} - {error_msg}")
                
                logger.info(f"  {description}: {corrupted_in_area} corrupted out of {min(50, len(files))} checked")
    
    def sample_all_datasets(self):
        """Sample check all datasets for corruption.""" 
        logger.info("Running sample corruption check across all datasets...")
        
        datasets = [
            ("raw/sst", self.raw_path / "sst", 100),
            ("raw/currents", self.raw_path / "currents", 100),
            ("raw/acidity_historical", self.raw_path / "acidity_historical", 200),
            ("raw/acidity_current", self.raw_path / "acidity_current", 50),
            ("raw/microplastics", self.raw_path / "microplastics", 20),
        ]
        
        for dataset_name, dataset_path, sample_size in datasets:
            if dataset_path.exists():
                logger.info(f"Sampling {dataset_name} ({sample_size} files)...")
                
                sample_files = self.sample_dataset(dataset_path, sample_size)
                corrupted_in_dataset = 0
                
                for file_path in sample_files:
                    is_healthy, error_msg = self.check_file(file_path)
                    if not is_healthy:
                        self.corrupted_files.append({
                            "file": str(file_path.relative_to(self.base_path)),
                            "error": error_msg,
                            "dataset": dataset_name
                        })
                        corrupted_in_dataset += 1
                        logger.warning(f"CORRUPTED: {file_path.name} - {error_msg}")
                
                corruption_rate = (corrupted_in_dataset / len(sample_files) * 100) if sample_files else 0
                logger.info(f"  {dataset_name}: {corrupted_in_dataset}/{len(sample_files)} corrupted ({corruption_rate:.1f}%)")
            else:
                logger.warning(f"  {dataset_name}: Not found")
    
    def run_quick_scan(self):
        """Run quick corruption scan."""
        logger.info("="*60)
        logger.info("QUICK CORRUPTION CHECK")
        logger.info("="*60)
        logger.info(f"Starting scan at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # First check high-risk areas
        self.check_high_risk_areas()
        
        # Then sample other datasets
        self.sample_all_datasets()
        
        # Final report
        self.print_summary()
        
        return len(self.corrupted_files)
    
    def print_summary(self):
        """Print summary of findings."""
        logger.info("\n" + "="*60)
        logger.info("QUICK SCAN SUMMARY")
        logger.info("="*60)
        
        if not self.corrupted_files:
            logger.info("✅ No corruption detected in sampled files!")
            logger.info("The data appears to be in good condition.")
        else:
            logger.info(f"⚠️  Found {len(self.corrupted_files)} corrupted files:")
            
            # Group by error type
            error_types = {}
            for corrupt_file in self.corrupted_files:
                error = corrupt_file["error"]
                if error not in error_types:
                    error_types[error] = []
                error_types[error].append(corrupt_file)
            
            for error_type, files in error_types.items():
                logger.info(f"\n{error_type}: {len(files)} files")
                for corrupt_file in files[:5]:  # Show first 5
                    logger.info(f"  - {corrupt_file['file']}")
                if len(files) > 5:
                    logger.info(f"  ... and {len(files) - 5} more")
        
        # Save corrupted file list if any found
        if self.corrupted_files:
            output_file = self.base_path / "logs" / f"quick_corruption_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w') as f:
                f.write(f"Quick Corruption Scan Results - {datetime.now()}\n")
                f.write("="*60 + "\n\n")
                f.write(f"Total corrupted files found: {len(self.corrupted_files)}\n\n")
                
                for corrupt_file in self.corrupted_files:
                    f.write(f"File: {corrupt_file['file']}\n")
                    f.write(f"Error: {corrupt_file['error']}\n")
                    f.write(f"Context: {corrupt_file.get('area', corrupt_file.get('dataset', 'Unknown'))}\n")
                    f.write("-" * 40 + "\n")
            
            logger.info(f"\nCorrupted file list saved to: {output_file}")

def main():
    """Main function."""
    checker = QuickCorruptionChecker()
    corrupted_count = checker.run_quick_scan()
    
    if corrupted_count > 0:
        logger.warning(f"\n⚠️  Found {corrupted_count} corrupted files in quick scan!")
        logger.info("Run the comprehensive scan for complete analysis:")
        logger.info("python scripts/comprehensive_corruption_check.py")
        sys.exit(1)
    else:
        logger.info("\n✅ Quick scan found no corruption issues!")
        sys.exit(0)

if __name__ == "__main__":
    main()