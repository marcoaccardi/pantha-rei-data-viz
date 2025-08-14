#!/usr/bin/env python3
"""
Comprehensive corruption check for all ocean data files.
Scans all raw and processed NetCDF files to identify any corruption.
"""

import sys
import logging
from pathlib import Path
import xarray as xr
from typing import List, Dict, Tuple
import json
from datetime import datetime
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ComprehensiveCorruptionChecker:
    """Performs comprehensive corruption check on ocean data files."""
    
    def __init__(self):
        """Initialize the corruption checker."""
        self.base_path = Path("/media/anecoica/ANECOICA_DEV/pantha-rei-data-viz/ocean-data")
        self.raw_path = self.base_path / "raw"
        self.processed_path = self.base_path / "processed"
        
        # Track results
        self.results = {
            "scan_timestamp": datetime.now().isoformat(),
            "datasets": {},
            "summary": {
                "total_files_scanned": 0,
                "total_corrupted": 0,
                "total_healthy": 0,
                "total_size_gb": 0
            }
        }
        
    def check_file_corruption(self, file_path: Path) -> Tuple[bool, str, Dict]:
        """
        Check if a NetCDF file is corrupted.
        
        Returns:
            Tuple of (is_healthy, error_message, file_info)
        """
        file_info = {
            "size_mb": file_path.stat().st_size / (1024 * 1024),
            "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
        }
        
        try:
            # Try to open with xarray
            with xr.open_dataset(file_path) as ds:
                # Basic validation checks
                checks = {
                    "has_dimensions": len(list(ds.dims.keys())) > 0,
                    "has_coordinates": len(list(ds.coords.keys())) > 0,
                    "has_variables": len(list(ds.data_vars)) > 0,
                }
                
                # Try to access actual data (not just metadata)
                if 'time' in ds.dims:
                    checks["time_accessible"] = len(ds.time) > 0
                    
                # Check for NaN-only variables (sign of corruption)
                for var_name in list(ds.data_vars)[:3]:  # Check first 3 variables
                    try:
                        data = ds[var_name].values
                        if np.isfinite(data).any():
                            checks[f"{var_name}_has_data"] = True
                        else:
                            checks[f"{var_name}_all_nan"] = True
                    except:
                        checks[f"{var_name}_error"] = True
                
                file_info["checks"] = checks
                
                # File is healthy if all basic checks pass
                if not all([checks.get("has_dimensions"), 
                           checks.get("has_coordinates"),
                           checks.get("has_variables")]):
                    return False, "Failed basic structure checks", file_info
                    
                return True, "OK", file_info
                
        except PermissionError:
            return False, "Permission denied", file_info
        except FileNotFoundError:
            return False, "File not found", file_info
        except Exception as e:
            error_str = str(e).lower()
            
            # Categorize the error
            if 'hdf' in error_str:
                return False, "HDF/NetCDF corruption", file_info
            elif 'did not find a match' in error_str:
                return False, "Backend format error", file_info
            elif 'bad magic number' in error_str:
                return False, "File header corruption", file_info
            elif 'not a valid netcdf' in error_str:
                return False, "Invalid NetCDF format", file_info
            else:
                return False, f"Unknown error: {str(e)[:100]}", file_info
    
    def scan_dataset(self, dataset_name: str, dataset_path: Path) -> Dict:
        """
        Scan all files in a dataset for corruption.
        
        Args:
            dataset_name: Name of the dataset
            dataset_path: Path to dataset directory
            
        Returns:
            Dictionary with scan results
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Scanning dataset: {dataset_name}")
        logger.info(f"Path: {dataset_path}")
        
        if not dataset_path.exists():
            logger.warning(f"Dataset path does not exist: {dataset_path}")
            return {
                "exists": False,
                "error": "Path does not exist"
            }
        
        # Find all NetCDF files
        nc_files = list(dataset_path.rglob("*.nc")) + list(dataset_path.rglob("*.nc4"))
        
        if not nc_files:
            logger.warning(f"No NetCDF files found in {dataset_path}")
            return {
                "exists": True,
                "total_files": 0,
                "message": "No NetCDF files found"
            }
        
        logger.info(f"Found {len(nc_files)} NetCDF files to check")
        
        dataset_results = {
            "total_files": len(nc_files),
            "healthy_files": 0,
            "corrupted_files": 0,
            "corrupted_list": [],
            "error_types": {},
            "total_size_gb": 0
        }
        
        # Check each file
        for i, nc_file in enumerate(nc_files, 1):
            # Progress indicator for large datasets
            if i % 500 == 0:
                logger.info(f"Progress: {i}/{len(nc_files)} files checked...")
            
            is_healthy, error_msg, file_info = self.check_file_corruption(nc_file)
            
            # Update totals
            self.results["summary"]["total_files_scanned"] += 1
            dataset_results["total_size_gb"] += file_info["size_mb"] / 1024
            
            if is_healthy:
                dataset_results["healthy_files"] += 1
                self.results["summary"]["total_healthy"] += 1
            else:
                dataset_results["corrupted_files"] += 1
                self.results["summary"]["total_corrupted"] += 1
                
                # Track error types
                if error_msg not in dataset_results["error_types"]:
                    dataset_results["error_types"][error_msg] = 0
                dataset_results["error_types"][error_msg] += 1
                
                # Add to corrupted list
                dataset_results["corrupted_list"].append({
                    "file": str(nc_file.relative_to(self.base_path)),
                    "error": error_msg,
                    "size_mb": file_info["size_mb"],
                    "modified": file_info["modified"]
                })
                
                # Log corrupted files immediately
                logger.warning(f"CORRUPTED: {nc_file.name} - {error_msg}")
        
        # Summary for this dataset
        corruption_rate = (dataset_results["corrupted_files"] / dataset_results["total_files"] * 100) if dataset_results["total_files"] > 0 else 0
        
        logger.info(f"\nDataset Summary: {dataset_name}")
        logger.info(f"  Total files: {dataset_results['total_files']}")
        logger.info(f"  Healthy: {dataset_results['healthy_files']}")
        logger.info(f"  Corrupted: {dataset_results['corrupted_files']} ({corruption_rate:.2f}%)")
        logger.info(f"  Total size: {dataset_results['total_size_gb']:.2f} GB")
        
        if dataset_results["error_types"]:
            logger.info(f"  Error types:")
            for error_type, count in dataset_results["error_types"].items():
                logger.info(f"    - {error_type}: {count}")
        
        self.results["summary"]["total_size_gb"] += dataset_results["total_size_gb"]
        
        return dataset_results
    
    def run_comprehensive_scan(self):
        """Run comprehensive corruption scan on all datasets."""
        logger.info("="*60)
        logger.info("COMPREHENSIVE CORRUPTION CHECK")
        logger.info("="*60)
        logger.info(f"Starting scan at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Define datasets to scan
        datasets_to_scan = [
            # Raw data
            ("raw/sst", self.raw_path / "sst"),
            ("raw/currents", self.raw_path / "currents"),
            ("raw/acidity", self.raw_path / "acidity"),
            ("raw/acidity_historical", self.raw_path / "acidity_historical"),
            ("raw/acidity_current", self.raw_path / "acidity_current"),
            ("raw/microplastics", self.raw_path / "microplastics"),
            
            # Processed data
            ("processed/sst", self.processed_path / "sst_downsampled"),
            ("processed/unified_coords/sst", self.processed_path / "unified_coords" / "sst"),
            ("processed/unified_coords/currents", self.processed_path / "unified_coords" / "currents"),
            ("processed/unified_coords/acidity", self.processed_path / "unified_coords" / "acidity"),
            ("processed/unified_coords/acidity_historical", self.processed_path / "unified_coords" / "acidity_historical"),
            ("processed/unified_coords/acidity_current", self.processed_path / "unified_coords" / "acidity_current"),
            ("processed/unified_coords/microplastics", self.processed_path / "unified_coords" / "microplastics"),
            ("processed/microplastics_filtered", self.processed_path / "microplastics_filtered"),
        ]
        
        # Scan each dataset
        for dataset_name, dataset_path in datasets_to_scan:
            self.results["datasets"][dataset_name] = self.scan_dataset(dataset_name, dataset_path)
        
        # Final summary
        self.print_final_summary()
        
        # Save results to file
        self.save_results()
        
        return self.results
    
    def print_final_summary(self):
        """Print final summary of corruption check."""
        logger.info("\n" + "="*60)
        logger.info("FINAL SUMMARY")
        logger.info("="*60)
        
        summary = self.results["summary"]
        corruption_rate = (summary["total_corrupted"] / summary["total_files_scanned"] * 100) if summary["total_files_scanned"] > 0 else 0
        
        logger.info(f"Total files scanned: {summary['total_files_scanned']}")
        logger.info(f"Total healthy files: {summary['total_healthy']}")
        logger.info(f"Total corrupted files: {summary['total_corrupted']}")
        logger.info(f"Overall corruption rate: {corruption_rate:.2f}%")
        logger.info(f"Total data size: {summary['total_size_gb']:.2f} GB")
        
        # List datasets with corruption
        logger.info("\nDatasets with corrupted files:")
        for dataset_name, dataset_info in self.results["datasets"].items():
            if isinstance(dataset_info, dict) and dataset_info.get("corrupted_files", 0) > 0:
                logger.info(f"  - {dataset_name}: {dataset_info['corrupted_files']} corrupted files")
        
        # Detailed corrupted file list
        if summary["total_corrupted"] > 0:
            logger.info("\n" + "="*60)
            logger.info("CORRUPTED FILES REQUIRING ATTENTION")
            logger.info("="*60)
            
            for dataset_name, dataset_info in self.results["datasets"].items():
                if isinstance(dataset_info, dict) and dataset_info.get("corrupted_list"):
                    logger.info(f"\n{dataset_name}:")
                    for corrupt_file in dataset_info["corrupted_list"][:10]:  # Show first 10
                        logger.info(f"  - {corrupt_file['file']}")
                        logger.info(f"    Error: {corrupt_file['error']}")
                        logger.info(f"    Size: {corrupt_file['size_mb']:.2f} MB")
                    
                    if len(dataset_info["corrupted_list"]) > 10:
                        logger.info(f"  ... and {len(dataset_info['corrupted_list']) - 10} more")
    
    def save_results(self):
        """Save scan results to JSON file."""
        output_file = self.base_path / "logs" / f"corruption_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"\nResults saved to: {output_file}")
        
        # Also save a summary report
        summary_file = self.base_path / "logs" / "corruption_summary_latest.txt"
        with open(summary_file, 'w') as f:
            f.write(f"Corruption Scan Summary - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*60 + "\n\n")
            
            f.write(f"Total files scanned: {self.results['summary']['total_files_scanned']}\n")
            f.write(f"Total corrupted: {self.results['summary']['total_corrupted']}\n")
            f.write(f"Total healthy: {self.results['summary']['total_healthy']}\n\n")
            
            f.write("Corrupted files by dataset:\n")
            for dataset_name, dataset_info in self.results["datasets"].items():
                if isinstance(dataset_info, dict) and dataset_info.get("corrupted_list"):
                    f.write(f"\n{dataset_name}: {len(dataset_info['corrupted_list'])} files\n")
                    for corrupt_file in dataset_info["corrupted_list"]:
                        f.write(f"  {corrupt_file['file']} - {corrupt_file['error']}\n")
        
        logger.info(f"Summary report saved to: {summary_file}")

def main():
    """Main function."""
    checker = ComprehensiveCorruptionChecker()
    results = checker.run_comprehensive_scan()
    
    # Return exit code based on corruption found
    if results["summary"]["total_corrupted"] > 0:
        logger.warning(f"\n⚠️  Found {results['summary']['total_corrupted']} corrupted files that need attention!")
        sys.exit(1)
    else:
        logger.info("\n✅ All files are healthy! No corruption detected.")
        sys.exit(0)

if __name__ == "__main__":
    main()