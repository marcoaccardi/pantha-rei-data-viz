#!/usr/bin/env python3
"""
Complete data audit to verify all available data has been processed
and check for any remaining corruption iteratively.
"""

import sys
import logging
from pathlib import Path
import xarray as xr
from typing import List, Dict, Tuple, Set
import json
from datetime import datetime
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CompleteDataAuditor:
    """Comprehensive audit of raw vs processed data and corruption check."""
    
    def __init__(self):
        """Initialize the auditor."""
        self.base_path = Path("/media/anecoica/ANECOICA_DEV/pantha-rei-data-viz/ocean-data")
        self.raw_path = self.base_path / "raw"
        self.processed_path = self.base_path / "processed" / "unified_coords"
        
        self.audit_results = {
            "timestamp": datetime.now().isoformat(),
            "datasets": {},
            "corruption_found": [],
            "processing_gaps": {},
            "summary": {
                "total_raw_files": 0,
                "total_processed_files": 0,
                "unprocessed_files": 0,
                "corrupted_files": 0
            }
        }
    
    def check_file_health(self, file_path: Path) -> Tuple[bool, str]:
        """Check if a file is corrupted with detailed error info."""
        try:
            with xr.open_dataset(file_path) as ds:
                # Try to access basic structure and some data
                dims = list(ds.dims.keys())
                coords = list(ds.coords.keys()) 
                vars = list(ds.data_vars.keys())
                
                # Try to access coordinate data
                if 'time' in ds.dims:
                    _ = len(ds.time)
                if 'lat' in ds.coords or 'latitude' in ds.coords:
                    lat_coord = ds.lat if 'lat' in ds.coords else ds.latitude
                    lat_vals = lat_coord.values
                    if len(lat_vals) == 0:
                        return False, "Empty latitude coordinate"
                
                # Try to access a data variable
                if vars:
                    first_var = vars[0]
                    try:
                        data = ds[first_var].values
                        if data.size == 0:
                            return False, f"Empty data array for {first_var}"
                    except Exception as e:
                        return False, f"Cannot access {first_var}: {str(e)[:50]}"
                
                return True, "OK"
        except Exception as e:
            error_str = str(e).lower()
            if 'hdf error' in error_str:
                return False, "HDF/NetCDF corruption"
            elif 'bad magic number' in error_str:
                return False, "File header corruption"
            elif 'did not find a match' in error_str:
                return False, "Backend format error"
            elif 'permission denied' in error_str:
                return False, "Permission denied"
            else:
                return False, f"Unknown error: {str(e)[:80]}"
    
    def get_file_identifier(self, file_path: Path, dataset_type: str) -> str:
        """Extract identifier from filename for matching raw to processed files."""
        filename = file_path.stem
        
        if dataset_type == "sst":
            # SST files: sst_YYYYMMDD.nc -> YYYYMMDD
            if filename.startswith("sst_"):
                return filename.replace("sst_", "")
        elif dataset_type == "acidity_historical":
            # Acidity historical: acidity_historical_YYYYMMDD.nc -> YYYYMMDD
            if filename.startswith("acidity_historical_"):
                return filename.replace("acidity_historical_", "")
        elif dataset_type == "acidity_current":
            # Acidity current: acidity_current_YYYYMMDD.nc -> YYYYMMDD
            if filename.startswith("acidity_current_"):
                return filename.replace("acidity_current_", "")
        elif dataset_type == "currents":
            # OSCAR files: oscar_currents_final_YYYYMMDD.nc4 -> YYYYMMDD
            # CMEMS files: currents_global_YYYYMMDD.nc -> YYYYMMDD
            if "oscar" in filename:
                parts = filename.split("_")
                for part in parts:
                    if len(part) == 8 and part.isdigit():
                        return part
            elif filename.startswith("currents_global_"):
                return filename.replace("currents_global_", "")
        elif dataset_type == "microplastics":
            # Microplastics: various formats
            return filename
        
        # Fallback: try to extract YYYYMMDD pattern
        import re
        date_match = re.search(r'(\d{8})', filename)
        if date_match:
            return date_match.group(1)
        
        return filename
    
    def get_processed_identifiers(self, dataset_type: str) -> Set[str]:
        """Get set of identifiers for processed files."""
        processed_dir = self.processed_path / dataset_type
        if not processed_dir.exists():
            return set()
        
        processed_files = list(processed_dir.rglob("*.nc"))
        identifiers = set()
        
        for proc_file in processed_files:
            identifier = self.get_file_identifier(proc_file, dataset_type)
            identifiers.add(identifier)
        
        return identifiers
    
    def audit_dataset(self, dataset_name: str, raw_dir: Path, check_corruption: bool = True) -> Dict:
        """Audit a specific dataset for processing gaps and corruption."""
        logger.info(f"\n{'='*60}")
        logger.info(f"AUDITING DATASET: {dataset_name}")
        logger.info(f"Raw path: {raw_dir}")
        
        if not raw_dir.exists():
            logger.warning(f"Raw directory does not exist: {raw_dir}")
            return {"exists": False}
        
        # Find all raw files
        raw_files = list(raw_dir.rglob("*.nc")) + list(raw_dir.rglob("*.nc4"))
        logger.info(f"Found {len(raw_files)} raw files")
        
        if not raw_files:
            return {"exists": True, "raw_files": 0, "message": "No files found"}
        
        # Get processed file identifiers
        processed_identifiers = self.get_processed_identifiers(dataset_name)
        logger.info(f"Found {len(processed_identifiers)} processed file identifiers")
        
        dataset_audit = {
            "raw_files": len(raw_files),
            "processed_files": len(processed_identifiers),
            "unprocessed_files": [],
            "corrupted_files": [],
            "healthy_raw_files": 0,
            "processing_rate": 0.0
        }
        
        # Check each raw file
        unprocessed_count = 0
        corrupted_count = 0
        
        for i, raw_file in enumerate(raw_files):
            # Progress for large datasets
            if (i + 1) % 1000 == 0:
                logger.info(f"Progress: {i+1}/{len(raw_files)} files checked...")
            
            # Check if processed
            identifier = self.get_file_identifier(raw_file, dataset_name)
            is_processed = identifier in processed_identifiers
            
            # Check corruption if requested
            is_healthy = True
            error_msg = "OK"
            if check_corruption:
                is_healthy, error_msg = self.check_file_health(raw_file)
                
                if not is_healthy:
                    corrupted_count += 1
                    dataset_audit["corrupted_files"].append({
                        "file": str(raw_file.relative_to(self.base_path)),
                        "error": error_msg,
                        "identifier": identifier,
                        "is_processed": is_processed
                    })
                    logger.warning(f"CORRUPTED: {raw_file.name} - {error_msg}")
                else:
                    dataset_audit["healthy_raw_files"] += 1
            else:
                dataset_audit["healthy_raw_files"] += 1
            
            # Check if unprocessed (only for healthy files)
            if is_healthy and not is_processed:
                unprocessed_count += 1
                dataset_audit["unprocessed_files"].append({
                    "file": str(raw_file.relative_to(self.base_path)),
                    "identifier": identifier,
                    "size_mb": raw_file.stat().st_size / (1024 * 1024)
                })
        
        # Calculate processing rate
        healthy_files = len(raw_files) - corrupted_count
        if healthy_files > 0:
            processed_healthy = healthy_files - unprocessed_count
            dataset_audit["processing_rate"] = (processed_healthy / healthy_files) * 100
        
        # Summary
        logger.info(f"\nDataset Summary: {dataset_name}")
        logger.info(f"  Raw files: {len(raw_files)}")
        logger.info(f"  Processed files: {len(processed_identifiers)}")
        logger.info(f"  Healthy raw files: {dataset_audit['healthy_raw_files']}")
        logger.info(f"  Corrupted files: {corrupted_count}")
        logger.info(f"  Unprocessed files: {unprocessed_count}")
        logger.info(f"  Processing rate: {dataset_audit['processing_rate']:.1f}%")
        
        # Update global counters
        self.audit_results["summary"]["total_raw_files"] += len(raw_files)
        self.audit_results["summary"]["total_processed_files"] += len(processed_identifiers)
        self.audit_results["summary"]["unprocessed_files"] += unprocessed_count
        self.audit_results["summary"]["corrupted_files"] += corrupted_count
        
        # Store corruption found
        self.audit_results["corruption_found"].extend(dataset_audit["corrupted_files"])
        
        # Store processing gaps
        if unprocessed_count > 0:
            self.audit_results["processing_gaps"][dataset_name] = dataset_audit["unprocessed_files"]
        
        return dataset_audit
    
    def run_complete_audit(self, check_corruption: bool = True):
        """Run complete audit of all datasets."""
        logger.info("="*80)
        logger.info("COMPLETE DATA PROCESSING AUDIT")
        logger.info("="*80)
        logger.info(f"Starting audit at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Define datasets to audit
        datasets = [
            ("sst", self.raw_path / "sst"),
            ("currents", self.raw_path / "currents"),
            ("acidity_historical", self.raw_path / "acidity_historical"),
            ("acidity_current", self.raw_path / "acidity_current"),
            ("microplastics", self.raw_path / "microplastics"),
        ]
        
        # Audit each dataset
        for dataset_name, raw_dir in datasets:
            self.audit_results["datasets"][dataset_name] = self.audit_dataset(
                dataset_name, raw_dir, check_corruption
            )
        
        # Final summary
        self.print_final_summary()
        self.save_audit_results()
        
        return self.audit_results
    
    def print_final_summary(self):
        """Print final audit summary."""
        logger.info("\n" + "="*80)
        logger.info("FINAL AUDIT SUMMARY")
        logger.info("="*80)
        
        summary = self.audit_results["summary"]
        
        logger.info(f"Total raw files: {summary['total_raw_files']}")
        logger.info(f"Total processed files: {summary['total_processed_files']}")
        logger.info(f"Unprocessed files: {summary['unprocessed_files']}")
        logger.info(f"Corrupted files: {summary['corrupted_files']}")
        
        # Overall processing rate
        if summary['total_raw_files'] > 0:
            healthy_raw = summary['total_raw_files'] - summary['corrupted_files']
            if healthy_raw > 0:
                overall_rate = ((healthy_raw - summary['unprocessed_files']) / healthy_raw) * 100
                logger.info(f"Overall processing rate: {overall_rate:.1f}%")
        
        # Processing gaps by dataset
        if self.audit_results["processing_gaps"]:
            logger.info("\n📋 PROCESSING GAPS FOUND:")
            for dataset, gaps in self.audit_results["processing_gaps"].items():
                logger.info(f"  {dataset}: {len(gaps)} unprocessed files")
                # Show sample of unprocessed files
                for gap in gaps[:3]:
                    logger.info(f"    - {gap['file']} ({gap['size_mb']:.1f} MB)")
                if len(gaps) > 3:
                    logger.info(f"    ... and {len(gaps) - 3} more")
        
        # Corruption found
        if self.audit_results["corruption_found"]:
            logger.info("\n⚠️ CORRUPTION FOUND:")
            error_counts = defaultdict(int)
            for corrupt in self.audit_results["corruption_found"]:
                error_counts[corrupt["error"]] += 1
            
            for error, count in error_counts.items():
                logger.info(f"  {error}: {count} files")
        
        # Action items
        logger.info("\n🎯 RECOMMENDED ACTIONS:")
        if summary['unprocessed_files'] > 0:
            logger.info(f"  ⚡ Process {summary['unprocessed_files']} remaining raw files")
        if summary['corrupted_files'] > 0:
            logger.info(f"  🔧 Repair {summary['corrupted_files']} corrupted files")
        if summary['unprocessed_files'] == 0 and summary['corrupted_files'] == 0:
            logger.info("  ✅ No action needed - all data is processed and healthy!")
    
    def save_audit_results(self):
        """Save audit results to file."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = self.base_path / "logs" / f"complete_audit_{timestamp}.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(self.audit_results, f, indent=2, default=str)
        
        logger.info(f"\nAudit results saved to: {output_file}")

def main():
    """Main function."""
    auditor = CompleteDataAuditor()
    
    # Run complete audit with corruption checking
    results = auditor.run_complete_audit(check_corruption=True)
    
    # Exit code based on findings
    if results["summary"]["corrupted_files"] > 0 or results["summary"]["unprocessed_files"] > 0:
        logger.warning("⚠️ Issues found that need attention!")
        sys.exit(1)
    else:
        logger.info("✅ All data is processed and healthy!")
        sys.exit(0)

if __name__ == "__main__":
    main()