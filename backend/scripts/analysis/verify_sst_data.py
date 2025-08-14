#!/usr/bin/env python3
"""
SST Data Verification Script
Systematically verifies SST data quality at different ocean coordinates
and generates detailed logs for data assessment.
"""

import sys
import json
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Tuple, Any
import warnings

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

import xarray as xr
import numpy as np
import pandas as pd

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=RuntimeWarning)

class SSTDataVerifier:
    """Comprehensive SST data verification and analysis."""
    
    def __init__(self, data_root: Path):
        """Initialize with path to ocean data root."""
        self.data_root = Path(data_root)
        self.sst_raw_path = self.data_root / "raw" / "sst"
        self.sst_processed_path = self.data_root / "processed"
        self.logs_path = self.data_root / "logs"
        
        # Create verification logs directory
        self.verification_logs_path = self.logs_path / "verification"
        self.verification_logs_path.mkdir(parents=True, exist_ok=True)
        
        # Set up logging
        self.logger = self._setup_logging()
        
        # Define key ocean coordinates for testing
        self.test_coordinates = self._define_test_coordinates()
        
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for verification."""
        logger = logging.getLogger("sst_verifier")
        logger.setLevel(logging.INFO)
        
        # Remove existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # File handler
        log_file = self.verification_logs_path / f"sst_verification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def _define_test_coordinates(self) -> Dict[str, Dict[str, float]]:
        """Define key ocean coordinates for testing."""
        return {
            # Atlantic Ocean
            "North_Atlantic": {"lat": 45.0, "lon": -30.0, "description": "Mid North Atlantic"},
            "South_Atlantic": {"lat": -25.0, "lon": -15.0, "description": "South Atlantic Basin"},
            "Equatorial_Atlantic": {"lat": 0.0, "lon": -25.0, "description": "Equatorial Atlantic"},
            
            # Pacific Ocean
            "North_Pacific": {"lat": 35.0, "lon": 150.0, "description": "North Pacific"},
            "South_Pacific": {"lat": -20.0, "lon": -120.0, "description": "South Pacific"},
            "Equatorial_Pacific": {"lat": 0.0, "lon": 180.0, "description": "Central Pacific"},
            
            # Indian Ocean
            "North_Indian": {"lat": 20.0, "lon": 70.0, "description": "Arabian Sea"},
            "South_Indian": {"lat": -30.0, "lon": 90.0, "description": "Southern Indian Ocean"},
            
            # Arctic and Antarctic
            "Arctic_Ocean": {"lat": 80.0, "lon": 0.0, "description": "Arctic Ocean"},
            "Antarctic_Ocean": {"lat": -65.0, "lon": 0.0, "description": "Southern Ocean"},
            
            # Specific regions of interest
            "Gulf_Stream": {"lat": 36.0, "lon": -75.0, "description": "Gulf Stream region"},
            "Kuroshio": {"lat": 35.0, "lon": 140.0, "description": "Kuroshio Current"},
            "Agulhas": {"lat": -35.0, "lon": 25.0, "description": "Agulhas Current"},
            "Mediterranean": {"lat": 35.0, "lon": 15.0, "description": "Mediterranean Sea"},
            "Baltic_Sea": {"lat": 58.0, "lon": 20.0, "description": "Baltic Sea"},
        }
    
    def find_all_sst_files(self) -> List[Path]:
        """Find all SST files in the data directory."""
        files = []
        
        # Raw files
        raw_files = list(self.sst_raw_path.rglob("*.nc"))
        files.extend([(f, "raw") for f in raw_files])
        
        # Processed files
        if (self.sst_processed_path / "sst_downsampled").exists():
            downsampled_files = list((self.sst_processed_path / "sst_downsampled").rglob("*.nc"))
            files.extend([(f, "downsampled") for f in downsampled_files])
        
        if (self.sst_processed_path / "unified_coords").exists():
            harmonized_files = list((self.sst_processed_path / "unified_coords").rglob("*.nc"))
            files.extend([(f, "harmonized") for f in harmonized_files])
        
        return files
    
    def analyze_file_structure(self, file_path: Path) -> Dict[str, Any]:
        """Analyze NetCDF file structure and metadata."""
        try:
            with xr.open_dataset(file_path) as ds:
                return {
                    "dimensions": dict(ds.dims),
                    "variables": list(ds.data_vars.keys()),
                    "coordinates": list(ds.coords.keys()),
                    "attributes": dict(ds.attrs),
                    "coordinate_ranges": {
                        "lat": {"min": float(ds.lat.min()), "max": float(ds.lat.max())},
                        "lon": {"min": float(ds.lon.min()), "max": float(ds.lon.max())}
                    },
                    "resolution": {
                        "lat": float(abs(ds.lat.diff('lat').mean())),
                        "lon": float(abs(ds.lon.diff('lon').mean()))
                    },
                    "time_coverage": {
                        "time_values": [str(t) for t in ds.time.values],
                        "time_range": str(ds.time.values[0]) if len(ds.time.values) > 0 else "N/A"
                    }
                }
        except Exception as e:
            return {"error": str(e)}
    
    def extract_data_at_coordinates(self, file_path: Path, coord_name: str, coord_info: Dict) -> Dict[str, Any]:
        """Extract SST data at specific coordinates."""
        try:
            with xr.open_dataset(file_path) as ds:
                lat, lon = coord_info["lat"], coord_info["lon"]
                
                # Find nearest grid point
                nearest_data = ds.sel(lat=lat, lon=lon, method='nearest')
                
                # Extract SST value
                if 'sst' in nearest_data.data_vars:
                    sst_value = float(nearest_data.sst.values)
                    actual_lat = float(nearest_data.lat.values)
                    actual_lon = float(nearest_data.lon.values)
                    
                    return {
                        "requested_coordinates": {"lat": lat, "lon": lon},
                        "actual_coordinates": {"lat": actual_lat, "lon": actual_lon},
                        "sst_celsius": sst_value,
                        "sst_kelvin": sst_value + 273.15 if not np.isnan(sst_value) else np.nan,
                        "is_valid": not np.isnan(sst_value),
                        "distance_km": self._calculate_distance(lat, lon, actual_lat, actual_lon)
                    }
                else:
                    return {"error": "SST variable not found"}
                    
        except Exception as e:
            return {"error": str(e)}
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two coordinates in km."""
        from math import radians, cos, sin, asin, sqrt
        
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371  # Radius of Earth in km
        return c * r
    
    def generate_sst_statistics(self, file_path: Path) -> Dict[str, Any]:
        """Generate comprehensive statistics for SST data."""
        try:
            with xr.open_dataset(file_path) as ds:
                if 'sst' not in ds.data_vars:
                    return {"error": "SST variable not found"}
                
                sst_data = ds.sst
                
                # Remove fill values and invalid data
                valid_sst = sst_data.where((sst_data > -5) & (sst_data < 50))  # Reasonable SST range
                
                return {
                    "global_statistics": {
                        "mean": float(valid_sst.mean()),
                        "std": float(valid_sst.std()),
                        "min": float(valid_sst.min()),
                        "max": float(valid_sst.max()),
                        "median": float(valid_sst.median()),
                        "percentile_5": float(valid_sst.quantile(0.05)),
                        "percentile_95": float(valid_sst.quantile(0.95))
                    },
                    "data_coverage": {
                        "total_points": int(sst_data.size),
                        "valid_points": int(valid_sst.count()),
                        "missing_points": int(sst_data.size - valid_sst.count()),
                        "coverage_percentage": float(valid_sst.count() / sst_data.size * 100)
                    },
                    "temperature_distribution": {
                        "tropical": float(valid_sst.where((ds.lat > -23.5) & (ds.lat < 23.5)).mean()),
                        "temperate_north": float(valid_sst.where((ds.lat >= 23.5) & (ds.lat < 66.5)).mean()),
                        "temperate_south": float(valid_sst.where((ds.lat <= -23.5) & (ds.lat > -66.5)).mean()),
                        "polar_north": float(valid_sst.where(ds.lat >= 66.5).mean()),
                        "polar_south": float(valid_sst.where(ds.lat <= -66.5).mean())
                    }
                }
        except Exception as e:
            return {"error": str(e)}
    
    def verify_coordinate_systems(self, files: List[Tuple[Path, str]]) -> Dict[str, Any]:
        """Verify coordinate systems across different processing stages."""
        coord_analysis = {}
        
        for file_path, file_type in files:
            try:
                with xr.open_dataset(file_path) as ds:
                    coord_analysis[f"{file_type}_{file_path.name}"] = {
                        "longitude_system": self._detect_longitude_system(ds.lon),
                        "latitude_range": {"min": float(ds.lat.min()), "max": float(ds.lat.max())},
                        "longitude_range": {"min": float(ds.lon.min()), "max": float(ds.lon.max())},
                        "grid_type": self._detect_grid_type(ds),
                        "resolution": {
                            "lat": float(abs(ds.lat.diff('lat').mean())),
                            "lon": float(abs(ds.lon.diff('lon').mean()))
                        }
                    }
            except Exception as e:
                coord_analysis[f"{file_type}_{file_path.name}"] = {"error": str(e)}
        
        return coord_analysis
    
    def _detect_longitude_system(self, lon_coord) -> str:
        """Detect if longitude is in 0-360 or -180-180 system."""
        lon_min, lon_max = float(lon_coord.min()), float(lon_coord.max())
        
        if lon_min >= 0 and lon_max > 180:
            return "0-360"
        elif lon_min >= -180 and lon_max <= 180:
            return "-180-180"
        else:
            return f"custom ({lon_min:.1f} to {lon_max:.1f})"
    
    def _detect_grid_type(self, ds) -> str:
        """Detect grid type (regular, irregular, etc.)."""
        try:
            lat_diff = ds.lat.diff('lat')
            lon_diff = ds.lon.diff('lon')
            
            lat_regular = abs(lat_diff.std()) < 0.001
            lon_regular = abs(lon_diff.std()) < 0.001
            
            if lat_regular and lon_regular:
                return "regular"
            else:
                return "irregular"
        except:
            return "unknown"
    
    def run_comprehensive_verification(self) -> Dict[str, Any]:
        """Run complete verification suite."""
        self.logger.info("Starting comprehensive SST data verification")
        
        verification_results = {
            "verification_metadata": {
                "timestamp": datetime.now().isoformat(),
                "data_root": str(self.data_root),
                "test_coordinates_count": len(self.test_coordinates)
            },
            "file_discovery": {},
            "coordinate_analysis": {},
            "data_quality": {},
            "coordinate_extraction": {}
        }
        
        # 1. Discover all SST files
        self.logger.info("Discovering SST files...")
        all_files = self.find_all_sst_files()
        verification_results["file_discovery"] = {
            "total_files": len(all_files),
            "files_by_type": {},
            "file_list": []
        }
        
        file_types = {}
        for file_path, file_type in all_files:
            if file_type not in file_types:
                file_types[file_type] = 0
            file_types[file_type] += 1
            
            verification_results["file_discovery"]["file_list"].append({
                "path": str(file_path),
                "type": file_type,
                "size_mb": round(file_path.stat().st_size / (1024*1024), 2) if file_path.exists() else 0
            })
        
        verification_results["file_discovery"]["files_by_type"] = file_types
        self.logger.info(f"Found {len(all_files)} SST files: {file_types}")
        
        # 2. Verify coordinate systems
        self.logger.info("Analyzing coordinate systems...")
        verification_results["coordinate_analysis"] = self.verify_coordinate_systems(all_files)
        
        # 3. Analyze each file
        self.logger.info("Analyzing file structures and data quality...")
        for file_path, file_type in all_files:
            file_key = f"{file_type}_{file_path.name}"
            
            # File structure analysis
            structure = self.analyze_file_structure(file_path)
            verification_results["data_quality"][file_key] = {
                "structure": structure,
                "statistics": self.generate_sst_statistics(file_path)
            }
            
            # Coordinate extraction
            verification_results["coordinate_extraction"][file_key] = {}
            
            for coord_name, coord_info in self.test_coordinates.items():
                self.logger.info(f"Extracting SST at {coord_name} ({coord_info['description']})")
                coord_data = self.extract_data_at_coordinates(file_path, coord_name, coord_info)
                verification_results["coordinate_extraction"][file_key][coord_name] = coord_data
                
                # Log results
                if "error" not in coord_data:
                    sst_val = coord_data.get("sst_celsius", "N/A")
                    is_valid = coord_data.get("is_valid", False)
                    self.logger.info(
                        f"  {coord_name}: SST = {sst_val:.2f}°C, Valid = {is_valid}"
                    )
                else:
                    self.logger.warning(f"  {coord_name}: Error - {coord_data['error']}")
        
        # 4. Save detailed results
        results_file = self.verification_logs_path / f"sst_verification_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(verification_results, f, indent=2, default=str)
        
        self.logger.info(f"Verification complete. Results saved to {results_file}")
        
        return verification_results
    
    def print_summary(self, results: Dict[str, Any]):
        """Print a summary of verification results."""
        print("\n" + "="*80)
        print("SST DATA VERIFICATION SUMMARY")
        print("="*80)
        
        # File discovery summary
        discovery = results["file_discovery"]
        print(f"\n📁 FILE DISCOVERY:")
        print(f"   Total files found: {discovery['total_files']}")
        for file_type, count in discovery["files_by_type"].items():
            print(f"   - {file_type}: {count} files")
        
        # Coordinate system summary
        print(f"\n🌍 COORDINATE SYSTEMS:")
        coord_systems = set()
        for file_analysis in results["coordinate_analysis"].values():
            if "longitude_system" in file_analysis:
                coord_systems.add(file_analysis["longitude_system"])
        print(f"   Longitude systems detected: {', '.join(coord_systems)}")
        
        # Data quality summary
        print(f"\n📊 DATA QUALITY:")
        for file_key, quality_data in results["data_quality"].items():
            if "statistics" in quality_data and "global_statistics" in quality_data["statistics"]:
                stats = quality_data["statistics"]["global_statistics"]
                coverage = quality_data["statistics"]["data_coverage"]
                print(f"   {file_key}:")
                print(f"     - SST range: {stats['min']:.2f}°C to {stats['max']:.2f}°C")
                print(f"     - Global mean: {stats['mean']:.2f}°C")
                print(f"     - Data coverage: {coverage['coverage_percentage']:.1f}%")
        
        # Coordinate extraction summary
        print(f"\n🎯 COORDINATE SAMPLING:")
        valid_extractions = 0
        total_extractions = 0
        
        for file_key, coord_data in results["coordinate_extraction"].items():
            for coord_name, extraction in coord_data.items():
                total_extractions += 1
                if extraction.get("is_valid", False):
                    valid_extractions += 1
        
        print(f"   Valid extractions: {valid_extractions}/{total_extractions} ({100*valid_extractions/total_extractions:.1f}%)")
        
        print("\n" + "="*80)


def main():
    """Main execution function."""
    # Set up paths
    backend_path = Path(__file__).parent.parent
    data_root = backend_path.parent / "ocean-data"
    
    if not data_root.exists():
        print(f"Error: Ocean data directory not found at {data_root}")
        return 1
    
    print(f"SST Data Verification")
    print(f"Data root: {data_root}")
    print(f"Starting verification at {datetime.now()}")
    
    # Create verifier and run
    verifier = SSTDataVerifier(data_root)
    results = verifier.run_comprehensive_verification()
    verifier.print_summary(results)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())