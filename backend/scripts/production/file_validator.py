#!/usr/bin/env python3
"""
Comprehensive File Validation Module

Validates integrity of ocean data files including NetCDF files and PNG textures.
Provides detailed validation reports and identifies corrupted files for recovery.
"""

import sys
import logging
import xarray as xr
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from datetime import datetime
import json
from PIL import Image
import os

# Add backend to path (now two levels up since we're in scripts/production/)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

class FileValidator:
    """Comprehensive file validation for ocean data files."""
    
    def __init__(self, base_path: Optional[Path] = None):
        """Initialize file validator."""
        self.base_path = base_path or Path(__file__).parent.parent.parent / "ocean-data"
        self.logger = logging.getLogger(__name__)
        
        # Validation thresholds and expectations
        self.validation_config = {
            "sst": {
                "expected_variables": ["sst", "anom", "err", "ice"],
                "expected_dims": ["time", "lat", "lon"],
                "min_file_size_kb": 800,
                "max_file_size_kb": 3000,
                "lat_range": (-90, 90),
                "lon_range": (0, 360),  # OISST uses 0-360
                "time_tolerance_days": 1
            },
            "currents": {
                "expected_variables": ["u", "v"],
                "expected_dims": ["time", "latitude", "longitude"],
                "min_file_size_kb": 1000,
                "max_file_size_kb": 50000,
                "lat_range": (-90, 90),
                "lon_range": (-180, 180),
                "time_tolerance_days": 1
            },
            "acidity": {
                "expected_variables": ["ph", "no3", "po4", "si", "o2"],  # May vary
                "expected_dims": ["time", "latitude", "longitude"],
                "min_file_size_kb": 500,
                "max_file_size_kb": 100000,
                "lat_range": (-90, 90),
                "lon_range": (-180, 180),
                "time_tolerance_days": 1
            },
            "sst_textures": {
                "expected_format": "PNG",
                "min_file_size_kb": 100,
                "max_file_size_kb": 5000,
                "expected_dimensions": (720, 360),  # Typical global texture size
                "allow_transparency": True
            }
        }
    
    def validate_file(self, file_path: Path, dataset: str) -> Dict:
        """
        Validate a single file comprehensively.
        
        Args:
            file_path: Path to file to validate
            dataset: Dataset type (sst, currents, acidity, sst_textures)
        
        Returns:
            Dictionary with validation results
        """
        result = {
            "file_path": str(file_path),
            "dataset": dataset,
            "is_valid": False,
            "errors": [],
            "warnings": [],
            "file_info": {},
            "validation_timestamp": datetime.now().isoformat()
        }
        
        # Check if file exists
        if not file_path.exists():
            result["errors"].append("File does not exist")
            return result
        
        # Get file info
        try:
            stat = file_path.stat()
            result["file_info"] = {
                "size_bytes": stat.st_size,
                "size_kb": stat.st_size / 1024,
                "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat()
            }
        except Exception as e:
            result["errors"].append(f"Cannot read file metadata: {e}")
            return result
        
        # Validate based on file type
        if dataset == "sst_textures":
            return self._validate_texture_file(file_path, result)
        else:
            return self._validate_netcdf_file(file_path, dataset, result)
    
    def _validate_netcdf_file(self, file_path: Path, dataset: str, result: Dict) -> Dict:
        """Validate NetCDF file comprehensively."""
        config = self.validation_config.get(dataset, {})
        
        # Basic file size check
        size_kb = result["file_info"]["size_kb"]
        min_size = config.get("min_file_size_kb", 100)
        max_size = config.get("max_file_size_kb", 100000)
        
        if size_kb < min_size:
            result["errors"].append(f"File too small: {size_kb:.1f} KB (minimum: {min_size} KB)")
        elif size_kb > max_size:
            result["warnings"].append(f"File larger than expected: {size_kb:.1f} KB (maximum: {max_size} KB)")
        
        # Try to open with xarray
        try:
            with xr.open_dataset(file_path) as ds:
                # Check dimensions
                result["file_info"]["dimensions"] = dict(ds.dims)
                result["file_info"]["variables"] = list(ds.data_vars.keys())
                result["file_info"]["coordinates"] = list(ds.coords.keys())
                
                # Validate dimensions
                expected_dims = config.get("expected_dims", [])
                missing_dims = set(expected_dims) - set(ds.dims.keys())
                if missing_dims:
                    result["errors"].append(f"Missing dimensions: {missing_dims}")
                
                # Validate variables (at least some expected variables should exist)
                expected_vars = config.get("expected_variables", [])
                if expected_vars:
                    available_vars = set(ds.data_vars.keys())
                    if not any(var in available_vars for var in expected_vars):
                        result["errors"].append(f"No expected variables found. Expected: {expected_vars}, Found: {list(available_vars)}")
                
                # Validate coordinate ranges
                self._validate_coordinates(ds, config, result)
                
                # Validate data integrity
                self._validate_data_integrity(ds, result)
                
                # Validate time dimension if present
                if "time" in ds.dims:
                    self._validate_time_dimension(ds, file_path, config, result)
                
        except Exception as e:
            result["errors"].append(f"Cannot open NetCDF file: {e}")
            return result
        
        # Set overall validity
        result["is_valid"] = len(result["errors"]) == 0
        return result
    
    def _validate_texture_file(self, file_path: Path, result: Dict) -> Dict:
        """Validate PNG texture file."""
        config = self.validation_config.get("sst_textures", {})
        
        # Basic file size check
        size_kb = result["file_info"]["size_kb"]
        min_size = config.get("min_file_size_kb", 50)
        max_size = config.get("max_file_size_kb", 10000)
        
        if size_kb < min_size:
            result["errors"].append(f"Texture too small: {size_kb:.1f} KB (minimum: {min_size} KB)")
        elif size_kb > max_size:
            result["warnings"].append(f"Texture larger than expected: {size_kb:.1f} KB (maximum: {max_size} KB)")
        
        # Try to open with PIL
        try:
            with Image.open(file_path) as img:
                result["file_info"]["format"] = img.format
                result["file_info"]["mode"] = img.mode
                result["file_info"]["size"] = img.size
                
                # Validate format
                expected_format = config.get("expected_format", "PNG")
                if img.format != expected_format:
                    result["errors"].append(f"Wrong format: {img.format} (expected: {expected_format})")
                
                # Validate dimensions
                expected_dims = config.get("expected_dimensions")
                if expected_dims and img.size != expected_dims:
                    result["warnings"].append(f"Unexpected dimensions: {img.size} (expected: {expected_dims})")
                
                # Check for corruption by trying to load pixel data
                try:
                    img.load()
                except Exception as e:
                    result["errors"].append(f"Cannot load image data: {e}")
                
                # Validate transparency if expected
                if config.get("allow_transparency") and img.mode not in ["RGBA", "LA", "P"]:
                    result["warnings"].append(f"Expected transparency support, got mode: {img.mode}")
                
        except Exception as e:
            result["errors"].append(f"Cannot open image file: {e}")
            return result
        
        # Set overall validity
        result["is_valid"] = len(result["errors"]) == 0
        return result
    
    def _validate_coordinates(self, ds: xr.Dataset, config: Dict, result: Dict):
        """Validate coordinate ranges."""
        # Check latitude range
        if "lat" in ds.coords or "latitude" in ds.coords:
            lat_coord = ds.coords.get("lat", ds.coords.get("latitude"))
            lat_min, lat_max = float(lat_coord.min()), float(lat_coord.max())
            
            expected_lat_range = config.get("lat_range", (-90, 90))
            if lat_min < expected_lat_range[0] or lat_max > expected_lat_range[1]:
                result["errors"].append(f"Latitude out of range: [{lat_min:.2f}, {lat_max:.2f}] (expected: {expected_lat_range})")
            
            result["file_info"]["lat_range"] = [lat_min, lat_max]
        
        # Check longitude range
        if "lon" in ds.coords or "longitude" in ds.coords:
            lon_coord = ds.coords.get("lon", ds.coords.get("longitude"))
            lon_min, lon_max = float(lon_coord.min()), float(lon_coord.max())
            
            expected_lon_range = config.get("lon_range", (-180, 180))
            # Allow some tolerance for longitude ranges
            if (lon_min < expected_lon_range[0] - 1) or (lon_max > expected_lon_range[1] + 1):
                result["warnings"].append(f"Longitude range unusual: [{lon_min:.2f}, {lon_max:.2f}] (expected: {expected_lon_range})")
            
            result["file_info"]["lon_range"] = [lon_min, lon_max]
    
    def _validate_data_integrity(self, ds: xr.Dataset, result: Dict):
        """Validate data integrity by checking for obvious corruption."""
        for var_name, var_data in ds.data_vars.items():
            try:
                # Check for NaN patterns that might indicate corruption
                if var_data.dtype.kind in ['f', 'c']:  # float or complex
                    nan_count = int(np.isnan(var_data).sum())
                    total_count = int(var_data.size)
                    nan_ratio = nan_count / total_count if total_count > 0 else 0
                    
                    result["file_info"][f"{var_name}_nan_ratio"] = nan_ratio
                    
                    if nan_ratio > 0.9:  # More than 90% NaN might indicate corruption
                        result["warnings"].append(f"Variable {var_name} has {nan_ratio:.1%} NaN values")
                    
                    # Check for infinite values
                    inf_count = int(np.isinf(var_data).sum())
                    if inf_count > 0:
                        result["warnings"].append(f"Variable {var_name} has {inf_count} infinite values")
                
                # Check data ranges for obvious corruption
                if var_data.dtype.kind in ['f', 'i']:  # numeric data
                    data_min = float(var_data.min())
                    data_max = float(var_data.max())
                    
                    result["file_info"][f"{var_name}_range"] = [data_min, data_max]
                    
                    # Basic sanity checks for common variables
                    if var_name.lower() in ["sst", "temperature"]:
                        if data_min < -5 or data_max > 50:  # Celsius range check
                            result["warnings"].append(f"Temperature {var_name} out of expected range: [{data_min:.2f}, {data_max:.2f}]")
                    elif var_name.lower() == "ph":
                        if data_min < 5 or data_max > 10:
                            result["warnings"].append(f"pH out of expected range: [{data_min:.2f}, {data_max:.2f}]")
                
            except Exception as e:
                result["warnings"].append(f"Cannot validate variable {var_name}: {e}")
    
    def _validate_time_dimension(self, ds: xr.Dataset, file_path: Path, config: Dict, result: Dict):
        """Validate time dimension consistency."""
        if "time" not in ds.coords:
            return
        
        try:
            time_coord = ds.coords["time"]
            
            # Extract expected date from filename
            from datetime import datetime
            import re
            
            date_match = re.search(r"(\d{8})", file_path.name)
            if date_match:
                expected_date = datetime.strptime(date_match.group(1), "%Y%m%d")
                
                # Check if time coordinate matches expected date
                if hasattr(time_coord, 'values'):
                    time_values = time_coord.values
                    if len(time_values) > 0:
                        actual_time = time_values[0]
                        
                        # Convert to datetime if needed
                        if hasattr(actual_time, 'item'):
                            actual_time = actual_time.item()
                        
                        # Simple date comparison (allowing for some timezone/format differences)
                        time_diff_days = abs((actual_time - expected_date).total_seconds()) / 86400
                        tolerance = config.get("time_tolerance_days", 1)
                        
                        if time_diff_days > tolerance:
                            result["warnings"].append(f"Time coordinate mismatch: file suggests {expected_date.date()}, data has {actual_time}")
                        
                        result["file_info"]["time_coordinate"] = str(actual_time)
                        result["file_info"]["expected_date"] = expected_date.date().isoformat()
        
        except Exception as e:
            result["warnings"].append(f"Cannot validate time dimension: {e}")
    
    def validate_dataset(self, dataset: str, file_paths: List[Path] = None) -> Dict:
        """
        Validate multiple files for a dataset.
        
        Args:
            dataset: Dataset name
            file_paths: List of specific files to validate (None for all files)
        
        Returns:
            Dictionary with validation results for all files
        """
        self.logger.info(f"Starting validation for dataset: {dataset}")
        
        if file_paths is None:
            file_paths = self._discover_dataset_files(dataset)
        
        results = {
            "dataset": dataset,
            "validation_timestamp": datetime.now().isoformat(),
            "total_files": len(file_paths),
            "valid_files": 0,
            "invalid_files": 0,
            "files_with_warnings": 0,
            "files": {}
        }
        
        for file_path in file_paths:
            self.logger.debug(f"Validating: {file_path}")
            
            file_result = self.validate_file(file_path, dataset)
            file_key = str(file_path.relative_to(self.base_path))
            results["files"][file_key] = file_result
            
            if file_result["is_valid"]:
                results["valid_files"] += 1
            else:
                results["invalid_files"] += 1
            
            if file_result["warnings"]:
                results["files_with_warnings"] += 1
        
        self.logger.info(f"Validation complete: {results['valid_files']}/{results['total_files']} files valid")
        
        return results
    
    def _discover_dataset_files(self, dataset: str) -> List[Path]:
        """Discover all files for a dataset."""
        files = []
        
        if dataset == "sst_textures":
            texture_path = self.base_path / "textures" / "sst"
            if texture_path.exists():
                files = list(texture_path.rglob("*.png"))
        else:
            # Check processed/unified_coords directory first (priority)
            processed_path = self.base_path / "processed/unified_coords" / dataset
            if processed_path.exists():
                files.extend(list(processed_path.rglob("*.nc")))
            
            # Also check for acidity variants in processed
            if dataset == "acidity":
                for variant in ["acidity_current", "acidity_historical"]:
                    variant_path = self.base_path / "processed/unified_coords" / variant
                    if variant_path.exists():
                        files.extend(list(variant_path.rglob("*.nc")))
            
            # If no processed files found, check raw directory as fallback
            if not files:
                raw_path = self.base_path / "raw" / dataset  
                if raw_path.exists():
                    files.extend(list(raw_path.rglob("*.nc")))
                    
                # Also check for acidity variants in raw
                if dataset == "acidity":
                    for variant in ["acidity_current", "acidity_historical"]:
                        variant_path = self.base_path / "raw" / variant
                        if variant_path.exists():
                            files.extend(list(variant_path.rglob("*.nc")))
        
        return sorted(files)
    
    def find_corrupted_files(self, dataset: str = None) -> Dict:
        """
        Find all corrupted files across datasets.
        
        Args:
            dataset: Specific dataset to check (None for all)
        
        Returns:
            Dictionary mapping datasets to lists of corrupted files
        """
        datasets_to_check = [dataset] if dataset else ["sst", "currents", "acidity", "sst_textures"]
        
        corrupted_files = {}
        
        for ds in datasets_to_check:
            self.logger.info(f"Checking for corrupted files in {ds}...")
            
            validation_result = self.validate_dataset(ds)
            
            corrupted_list = []
            for file_key, file_result in validation_result["files"].items():
                if not file_result["is_valid"]:
                    corrupted_list.append({
                        "file_path": file_key,
                        "errors": file_result["errors"]
                    })
            
            if corrupted_list:
                corrupted_files[ds] = corrupted_list
                self.logger.warning(f"Found {len(corrupted_list)} corrupted files in {ds}")
            else:
                self.logger.info(f"No corrupted files found in {ds}")
        
        return corrupted_files
    
    def generate_validation_report(self, output_path: Path = None) -> Path:
        """Generate comprehensive validation report."""
        if output_path is None:
            output_path = self.base_path / "logs" / f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        report = {
            "report_timestamp": datetime.now().isoformat(),
            "datasets": {}
        }
        
        datasets = ["sst", "currents", "acidity", "sst_textures"]
        
        for dataset in datasets:
            self.logger.info(f"Generating report for {dataset}...")
            report["datasets"][dataset] = self.validate_dataset(dataset)
        
        # Write report
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"Validation report saved to: {output_path}")
        return output_path


def main():
    """Command line interface for file validation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Ocean Data File Validator")
    parser.add_argument("--dataset", choices=["sst", "currents", "acidity", "sst_textures", "microplastics"], 
                       help="Dataset to validate")
    parser.add_argument("--file", type=Path, help="Specific file to validate")
    parser.add_argument("--find-corrupted", action="store_true", 
                       help="Find all corrupted files")
    parser.add_argument("--generate-report", action="store_true",
                       help="Generate comprehensive validation report")
    parser.add_argument("--base-path", type=Path, 
                       help="Base path for ocean data")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output")
    
    args = parser.parse_args()
    
    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Initialize validator
    validator = FileValidator(args.base_path)
    
    try:
        if args.file:
            # Validate single file
            if not args.dataset:
                print("Error: --dataset required when validating single file")
                sys.exit(1)
            
            result = validator.validate_file(args.file, args.dataset)
            print(json.dumps(result, indent=2))
            
            if not result["is_valid"]:
                sys.exit(1)
                
        elif args.find_corrupted:
            # Find corrupted files
            corrupted = validator.find_corrupted_files(args.dataset)
            
            if corrupted:
                print("Corrupted files found:")
                for dataset, files in corrupted.items():
                    print(f"\n{dataset}:")
                    for file_info in files:
                        print(f"  {file_info['file_path']}: {file_info['errors']}")
                sys.exit(1)
            else:
                print("No corrupted files found")
                
        elif args.generate_report:
            # Generate full report
            report_path = validator.generate_validation_report()
            print(f"Validation report generated: {report_path}")
            
        elif args.dataset:
            # Validate specific dataset
            result = validator.validate_dataset(args.dataset)
            print(json.dumps(result, indent=2))
            
            if result["invalid_files"] > 0:
                sys.exit(1)
                
        else:
            print("Error: Specify --dataset, --file, --find-corrupted, or --generate-report")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()