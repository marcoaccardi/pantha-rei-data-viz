#!/usr/bin/env python3
"""
Validation script to verify processed data completeness vs raw data.
Checks if raw data has been properly processed to unified coordinates.
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any
import xarray as xr
import json
from datetime import datetime

# Add backend to path (script is in scripts/maintenance/, need to go up two levels to reach backend/)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProcessedDataValidator:
    """Validates processed data against raw data."""
    
    def __init__(self):
        """Initialize validator."""
        self.raw_path = Path("../ocean-data/raw")
        self.processed_path = Path("../ocean-data/processed/unified_coords")
        
    def get_dataset_files(self, dataset: str) -> Tuple[List[Path], List[Path]]:
        """Get raw and processed files for a dataset."""
        raw_files = []
        processed_files = []
        
        # Raw files
        raw_dataset_path = self.raw_path / dataset
        if raw_dataset_path.exists():
            raw_files = list(raw_dataset_path.rglob("*.nc"))
        
        # Processed files
        processed_dataset_path = self.processed_path / dataset
        if processed_dataset_path.exists():
            processed_files = list(processed_dataset_path.rglob("*.nc"))
            
        return raw_files, processed_files
    
    def extract_date_from_filename(self, filename: str) -> str:
        """Extract date from filename."""
        # Handle different patterns
        if "harmonized_" in filename:
            date_part = filename.split("harmonized_")[-1].split(".")[0]
        elif "processed_" in filename:
            date_part = filename.split("processed_")[-1].split(".")[0]
        else:
            # Try to find 8-digit date pattern
            import re
            match = re.search(r'(\d{8})', filename)
            if match:
                date_part = match.group(1)
            else:
                return "unknown"
        
        if len(date_part) == 8 and date_part.isdigit():
            return f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
        return "unknown"
    
    def validate_dataset(self, dataset: str) -> Dict[str, Any]:
        """Validate a specific dataset."""
        logger.info(f"Validating dataset: {dataset}")
        
        raw_files, processed_files = self.get_dataset_files(dataset)
        
        # Extract dates from filenames
        raw_dates = set()
        for f in raw_files:
            date = self.extract_date_from_filename(f.name)
            if date != "unknown":
                raw_dates.add(date)
        
        processed_dates = set()
        for f in processed_files:
            date = self.extract_date_from_filename(f.name)
            if date != "unknown":
                processed_dates.add(date)
        
        # Compare coverage
        missing_processed = raw_dates - processed_dates
        extra_processed = processed_dates - raw_dates
        
        # File integrity checks
        valid_processed = 0
        corrupted_processed = []
        
        for pf in processed_files:
            try:
                with xr.open_dataset(pf) as ds:
                    # Basic checks
                    if len(ds.coords) > 0 and len(ds.data_vars) > 0:
                        # Check for required coordinates
                        has_lat = any('lat' in coord.lower() for coord in ds.coords)
                        has_lon = any('lon' in coord.lower() for coord in ds.coords)
                        if has_lat and has_lon:
                            valid_processed += 1
                        else:
                            corrupted_processed.append(f"Missing coordinates: {pf.name}")
                    else:
                        corrupted_processed.append(f"No coords/vars: {pf.name}")
            except Exception as e:
                corrupted_processed.append(f"Read error {pf.name}: {str(e)}")
        
        # Calculate storage savings
        raw_size = sum(f.stat().st_size for f in raw_files if f.exists()) / (1024**3)  # GB
        processed_size = sum(f.stat().st_size for f in processed_files if f.exists()) / (1024**3)  # GB
        savings = raw_size - processed_size
        
        result = {
            'dataset': dataset,
            'raw_files': len(raw_files),
            'processed_files': len(processed_files),
            'raw_dates': len(raw_dates),
            'processed_dates': len(processed_dates),
            'missing_processed_dates': list(missing_processed),
            'extra_processed_dates': list(extra_processed),
            'valid_processed_files': valid_processed,
            'corrupted_processed_files': corrupted_processed,
            'raw_size_gb': round(raw_size, 2),
            'processed_size_gb': round(processed_size, 2),
            'storage_savings_gb': round(savings, 2),
            'coverage_complete': len(missing_processed) == 0,
            'integrity_good': len(corrupted_processed) == 0,
            'safe_to_delete_raw': len(missing_processed) == 0 and len(corrupted_processed) == 0
        }
        
        return result
    
    def validate_all_datasets(self, datasets: List[str] = None) -> Dict[str, Any]:
        """Validate all or specified datasets."""
        if datasets is None:
            # Auto-detect datasets that have both raw and processed data
            datasets = []
            for raw_dir in self.raw_path.iterdir():
                if raw_dir.is_dir() and (self.processed_path / raw_dir.name).exists():
                    datasets.append(raw_dir.name)
        
        results = {}
        total_savings = 0
        safe_deletions = []
        
        logger.info(f"Validating datasets: {datasets}")
        
        for dataset in datasets:
            try:
                result = self.validate_dataset(dataset)
                results[dataset] = result
                
                if result['safe_to_delete_raw']:
                    safe_deletions.append(dataset)
                    total_savings += result['storage_savings_gb']
                    
            except Exception as e:
                logger.error(f"Error validating {dataset}: {e}")
                results[dataset] = {'error': str(e)}
        
        summary = {
            'validation_timestamp': datetime.now().isoformat(),
            'datasets_validated': len(datasets),
            'safe_for_deletion': safe_deletions,
            'total_potential_savings_gb': round(total_savings, 2),
            'individual_results': results
        }
        
        return summary

def main():
    parser = argparse.ArgumentParser(description='Validate processed data completeness')
    parser.add_argument('--compare-raw-to-unified', action='store_true', 
                       help='Compare raw data coverage to unified coordinates')
    parser.add_argument('--datasets', type=str, 
                       help='Comma-separated list of datasets to check')
    parser.add_argument('--output', type=str, default='validation_report.json',
                       help='Output file for validation report')
    
    args = parser.parse_args()
    
    validator = ProcessedDataValidator()
    
    datasets = None
    if args.datasets:
        datasets = [d.strip() for d in args.datasets.split(',')]
    
    # Run validation
    results = validator.validate_all_datasets(datasets)
    
    # Save results
    output_path = Path(args.output)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("\n" + "="*60)
    print("PROCESSED DATA VALIDATION SUMMARY")
    print("="*60)
    
    print(f"Datasets validated: {results['datasets_validated']}")
    print(f"Safe for raw deletion: {len(results['safe_for_deletion'])}")
    print(f"Potential storage savings: {results['total_potential_savings_gb']:.1f} GB")
    
    if results['safe_for_deletion']:
        print(f"\nSAFE TO DELETE (raw folders):")
        for dataset in results['safe_for_deletion']:
            result = results['individual_results'][dataset]
            print(f"  • {dataset}: {result['storage_savings_gb']:.1f} GB savings")
            print(f"    Coverage: {result['processed_dates']}/{result['raw_dates']} dates")
            print(f"    Files: {result['valid_processed_files']}/{result['processed_files']} valid")
    
    # Show any issues
    issues = []
    for dataset, result in results['individual_results'].items():
        if not result.get('safe_to_delete_raw', False):
            if result.get('missing_processed_dates'):
                issues.append(f"{dataset}: Missing {len(result['missing_processed_dates'])} processed dates")
            if result.get('corrupted_processed_files'):
                issues.append(f"{dataset}: {len(result['corrupted_processed_files'])} corrupted files")
    
    if issues:
        print(f"\nISSUES FOUND:")
        for issue in issues:
            print(f"  ⚠ {issue}")
    
    print(f"\nDetailed report saved to: {output_path}")
    
    if results['safe_for_deletion']:
        print(f"\nTo delete safe raw folders:")
        for dataset in results['safe_for_deletion']:
            print(f"rm -rf ocean-data/raw/{dataset}")

if __name__ == "__main__":
    main()