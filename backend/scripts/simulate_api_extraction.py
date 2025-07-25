#!/usr/bin/env python3
"""
API Data Extraction Simulation
Simulates how the future API will extract data at specific coordinates
and provides performance/storage optimization recommendations.
"""

import sys
import json
import time
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

import xarray as xr
import numpy as np
import pandas as pd

class APIDataExtractor:
    """Simulates API data extraction from processed SST data."""
    
    def __init__(self, data_root: Path):
        """Initialize with ocean data directory."""
        self.data_root = Path(data_root)
        self.harmonized_path = self.data_root / "processed" / "unified_coords"
        self.logs_path = self.data_root / "logs"
        
        # Create API simulation logs
        self.api_logs_path = self.logs_path / "api_simulation"
        self.api_logs_path.mkdir(parents=True, exist_ok=True)
        
        # Test coordinates for various ocean regions
        self.test_locations = self._define_test_locations()
        
    def _define_test_locations(self) -> Dict[str, Dict]:
        """Define test locations covering different ocean regions and use cases."""
        return {
            # Major Ocean Basins
            "atlantic_north": {
                "lat": 45.0, "lon": -30.0, 
                "name": "North Atlantic",
                "expected_temp_range": [8, 18],
                "use_case": "Shipping routes, weather forecasting"
            },
            "pacific_equatorial": {
                "lat": 0.0, "lon": 180.0,
                "name": "Equatorial Pacific", 
                "expected_temp_range": [26, 30],
                "use_case": "El Niño/La Niña monitoring"
            },
            "indian_ocean": {
                "lat": -20.0, "lon": 75.0,
                "name": "Southern Indian Ocean",
                "expected_temp_range": [22, 28],
                "use_case": "Monsoon prediction"
            },
            
            # Ocean Currents
            "gulf_stream": {
                "lat": 35.0, "lon": -75.0,
                "name": "Gulf Stream",
                "expected_temp_range": [18, 25],
                "use_case": "Current analysis, marine ecosystem"
            },
            "kuroshio": {
                "lat": 35.0, "lon": 140.0,
                "name": "Kuroshio Current",
                "expected_temp_range": [15, 22],
                "use_case": "Fisheries, regional climate"
            },
            "agulhas": {
                "lat": -35.0, "lon": 25.0,
                "name": "Agulhas Current", 
                "expected_temp_range": [16, 24],
                "use_case": "Marine biodiversity hotspot"
            },
            
            # Coastal Regions
            "california_coast": {
                "lat": 36.0, "lon": -122.0,
                "name": "California Coast",
                "expected_temp_range": [12, 18],
                "use_case": "Upwelling studies, fisheries"
            },
            "north_sea": {
                "lat": 56.0, "lon": 3.0,
                "name": "North Sea",
                "expected_temp_range": [6, 16],
                "use_case": "European marine ecosystem"
            },
            "great_barrier_reef": {
                "lat": -18.0, "lon": 147.0,
                "name": "Great Barrier Reef",
                "expected_temp_range": [24, 29],
                "use_case": "Coral bleaching monitoring"
            },
            
            # Extreme Regions  
            "arctic": {
                "lat": 75.0, "lon": 0.0,
                "name": "Arctic Ocean",
                "expected_temp_range": [-2, 2],
                "use_case": "Ice extent, climate change"
            },
            "antarctic": {
                "lat": -65.0, "lon": 0.0,
                "name": "Southern Ocean",
                "expected_temp_range": [-1, 4],
                "use_case": "Ice shelf monitoring"
            },
            
            # Small Seas
            "mediterranean": {
                "lat": 38.0, "lon": 15.0,
                "name": "Mediterranean Sea",
                "expected_temp_range": [15, 25],
                "use_case": "Regional climate, tourism"
            },
            "red_sea": {
                "lat": 20.0, "lon": 38.0,
                "name": "Red Sea",
                "expected_temp_range": [24, 30],
                "use_case": "Marine ecosystem, shipping"
            }
        }
    
    def find_latest_data_file(self) -> Optional[Path]:
        """Find the most recent harmonized SST file."""
        harmonized_files = list(self.harmonized_path.rglob("sst_harmonized_*.nc"))
        
        if not harmonized_files:
            return None
            
        # Sort by modification time
        return max(harmonized_files, key=lambda f: f.stat().st_mtime)
    
    def extract_point_data(self, file_path: Path, lat: float, lon: float) -> Dict[str, Any]:
        """Extract SST data at a specific coordinate (simulates API endpoint)."""
        start_time = time.time()
        
        try:
            with xr.open_dataset(file_path) as ds:
                # Find nearest grid point
                point_data = ds.sel(lat=lat, lon=lon, method='nearest')
                
                # Extract values
                result = {
                    "requested_coordinates": {"latitude": lat, "longitude": lon},
                    "actual_coordinates": {
                        "latitude": float(point_data.lat.values),
                        "longitude": float(point_data.lon.values)
                    },
                    "data": {},
                    "metadata": {
                        "extraction_time_ms": None,
                        "file_source": str(file_path.name),
                        "grid_resolution": f"{abs(float(ds.lat.diff('lat').mean())):.2f}°",
                        "coordinate_system": self._detect_coordinate_system(ds)
                    }
                }
                
                # Extract all available variables
                for var_name in point_data.data_vars:
                    var_data = point_data[var_name]
                    if var_data.size > 0:
                        value = float(var_data.values.flat[0]) if var_data.values.size > 0 else None
                        
                        result["data"][var_name] = {
                            "value": value,
                            "units": var_data.attrs.get("units", "unknown"),
                            "long_name": var_data.attrs.get("long_name", var_name),
                            "valid": not (np.isnan(value) if value is not None else True)
                        }
                
                # Calculate distance from requested point
                distance_km = self._calculate_distance(
                    lat, lon,
                    result["actual_coordinates"]["latitude"],
                    result["actual_coordinates"]["longitude"]
                )
                result["metadata"]["distance_km"] = round(distance_km, 2)
                
                # Record performance
                extraction_time = (time.time() - start_time) * 1000
                result["metadata"]["extraction_time_ms"] = round(extraction_time, 2)
                
                return result
                
        except Exception as e:
            return {
                "error": str(e),
                "extraction_time_ms": round((time.time() - start_time) * 1000, 2)
            }
    
    def extract_area_data(self, file_path: Path, lat_min: float, lat_max: float, 
                         lon_min: float, lon_max: float) -> Dict[str, Any]:
        """Extract SST data for a bounding box (simulates area API endpoint)."""
        start_time = time.time()
        
        try:
            with xr.open_dataset(file_path) as ds:
                # Select area
                area_data = ds.sel(
                    lat=slice(lat_min, lat_max),
                    lon=slice(lon_min, lon_max)
                )
                
                result = {
                    "requested_bounds": {
                        "lat_min": lat_min, "lat_max": lat_max,
                        "lon_min": lon_min, "lon_max": lon_max
                    },
                    "actual_bounds": {
                        "lat_min": float(area_data.lat.min()),
                        "lat_max": float(area_data.lat.max()),
                        "lon_min": float(area_data.lon.min()),
                        "lon_max": float(area_data.lon.max())
                    },
                    "grid_info": {
                        "lat_points": len(area_data.lat),
                        "lon_points": len(area_data.lon),
                        "total_points": len(area_data.lat) * len(area_data.lon)
                    },
                    "statistics": {},
                    "metadata": {
                        "extraction_time_ms": None,
                        "file_source": str(file_path.name),
                        "data_size_kb": None
                    }
                }
                
                # Calculate statistics for each variable
                for var_name in area_data.data_vars:
                    var_data = area_data[var_name]
                    valid_data = var_data.where(~np.isnan(var_data))
                    
                    if valid_data.count() > 0:
                        result["statistics"][var_name] = {
                            "mean": float(valid_data.mean()),
                            "std": float(valid_data.std()),
                            "min": float(valid_data.min()),
                            "max": float(valid_data.max()),
                            "valid_points": int(valid_data.count()),
                            "total_points": int(var_data.size),
                            "coverage_percent": float(valid_data.count() / var_data.size * 100)
                        }
                
                # Estimate data size if returned as JSON
                data_size_estimate = len(area_data.lat) * len(area_data.lon) * 4 * len(area_data.data_vars)  # 4 bytes per float
                result["metadata"]["data_size_kb"] = round(data_size_estimate / 1024, 2)
                
                extraction_time = (time.time() - start_time) * 1000
                result["metadata"]["extraction_time_ms"] = round(extraction_time, 2)
                
                return result
                
        except Exception as e:
            return {
                "error": str(e),
                "extraction_time_ms": round((time.time() - start_time) * 1000, 2)
            }
    
    def _detect_coordinate_system(self, ds) -> str:
        """Detect coordinate system."""
        lon_min, lon_max = float(ds.lon.min()), float(ds.lon.max())
        if lon_min >= -180 and lon_max <= 180:
            return "-180/+180"
        elif lon_min >= 0 and lon_max > 180:
            return "0/360"
        else:
            return f"custom ({lon_min:.1f}/{lon_max:.1f})"
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between coordinates in km."""
        from math import radians, cos, sin, asin, sqrt
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        return c * 6371  # Earth radius in km
    
    def validate_extraction_quality(self, location_key: str, extraction_result: Dict) -> Dict[str, Any]:
        """Validate extraction results against expected ranges."""
        location_info = self.test_locations[location_key]
        validation = {
            "location": location_info["name"],
            "quality_checks": {},
            "warnings": [],
            "status": "unknown"
        }
        
        if "error" in extraction_result:
            validation["status"] = "failed"
            validation["quality_checks"]["error"] = extraction_result["error"]
            return validation
        
        # Check SST value if available
        if "sst" in extraction_result.get("data", {}):
            sst_data = extraction_result["data"]["sst"]
            sst_value = sst_data.get("value")
            
            if sst_value is not None and sst_data.get("valid", False):
                expected_range = location_info["expected_temp_range"]
                
                validation["quality_checks"]["sst_value"] = sst_value
                validation["quality_checks"]["expected_range"] = expected_range
                validation["quality_checks"]["in_expected_range"] = expected_range[0] <= sst_value <= expected_range[1]
                
                # Distance check
                distance = extraction_result["metadata"].get("distance_km", 0)
                validation["quality_checks"]["grid_distance_km"] = distance
                validation["quality_checks"]["acceptable_distance"] = distance < 100  # Within 100km
                
                # Performance check
                extraction_time = extraction_result["metadata"].get("extraction_time_ms", 0)
                validation["quality_checks"]["extraction_time_ms"] = extraction_time
                validation["quality_checks"]["acceptable_performance"] = extraction_time < 100  # Under 100ms
                
                # Overall status
                if all([
                    validation["quality_checks"]["in_expected_range"],
                    validation["quality_checks"]["acceptable_distance"],
                    validation["quality_checks"]["acceptable_performance"]
                ]):
                    validation["status"] = "passed"
                else:
                    validation["status"] = "warning"
                    
                    if not validation["quality_checks"]["in_expected_range"]:
                        validation["warnings"].append(f"SST {sst_value:.1f}°C outside expected range {expected_range}")
                    if not validation["quality_checks"]["acceptable_distance"]:
                        validation["warnings"].append(f"Grid point {distance:.1f}km from requested location")
                    if not validation["quality_checks"]["acceptable_performance"]:
                        validation["warnings"].append(f"Extraction took {extraction_time:.1f}ms (>100ms)")
            else:
                validation["status"] = "failed"
                validation["warnings"].append("No valid SST data available")
        else:
            validation["status"] = "failed"
            validation["warnings"].append("SST variable not found")
        
        return validation
    
    def run_api_simulation(self) -> Dict[str, Any]:
        """Run complete API extraction simulation."""
        print("🌊 Starting API Data Extraction Simulation")
        print("=" * 60)
        
        # Find latest data file
        latest_file = self.find_latest_data_file()
        if not latest_file:
            return {"error": "No harmonized SST data files found"}
        
        print(f"📁 Using data file: {latest_file.name}")
        print(f"📊 File size: {latest_file.stat().st_size / 1024:.1f} KB")
        
        simulation_results = {
            "simulation_metadata": {
                "timestamp": datetime.now().isoformat(),
                "data_file": str(latest_file),
                "file_size_kb": round(latest_file.stat().st_size / 1024, 1),
                "test_locations": len(self.test_locations)
            },
            "point_extractions": {},
            "area_extractions": {},
            "validation_results": {},
            "performance_summary": {
                "total_extractions": 0,
                "successful_extractions": 0,
                "average_extraction_time_ms": 0,
                "max_extraction_time_ms": 0
            },
            "storage_analysis": {}
        }
        
        extraction_times = []
        
        print(f"\n🎯 Testing point extractions at {len(self.test_locations)} locations...")
        
        # Test point extractions
        for location_key, location_info in self.test_locations.items():
            print(f"  📍 {location_info['name']} ({location_info['lat']}, {location_info['lon']})")
            
            extraction_result = self.extract_point_data(
                latest_file, location_info["lat"], location_info["lon"]
            )
            
            simulation_results["point_extractions"][location_key] = extraction_result
            
            # Validate results
            validation = self.validate_extraction_quality(location_key, extraction_result)
            simulation_results["validation_results"][location_key] = validation
            
            # Track performance
            if "extraction_time_ms" in extraction_result.get("metadata", {}):
                extraction_times.append(extraction_result["metadata"]["extraction_time_ms"])
            
            # Print result
            status_emoji = {"passed": "✅", "warning": "⚠️", "failed": "❌"}.get(validation["status"], "❓")
            
            if "data" in extraction_result and "sst" in extraction_result["data"]:
                sst_val = extraction_result["data"]["sst"]["value"]
                print(f"    {status_emoji} SST: {sst_val:.2f}°C | Time: {extraction_result['metadata'].get('extraction_time_ms', 0):.1f}ms")
            else:
                print(f"    {status_emoji} No data available")
        
        print(f"\n📦 Testing area extractions...")
        
        # Test area extractions (bounding boxes)
        test_areas = {
            "north_atlantic_small": {"lat_min": 40, "lat_max": 50, "lon_min": -40, "lon_max": -20},
            "pacific_equatorial_band": {"lat_min": -5, "lat_max": 5, "lon_min": 160, "lon_max": 200},
            "mediterranean": {"lat_min": 30, "lat_max": 45, "lon_min": 0, "lon_max": 35}
        }
        
        for area_name, bounds in test_areas.items():
            print(f"  📍 {area_name.replace('_', ' ').title()}")
            
            area_result = self.extract_area_data(latest_file, **bounds)
            simulation_results["area_extractions"][area_name] = area_result
            
            if "extraction_time_ms" in area_result.get("metadata", {}):
                extraction_times.append(area_result["metadata"]["extraction_time_ms"])
            
            if "grid_info" in area_result:
                grid_info = area_result["grid_info"]
                time_ms = area_result["metadata"].get("extraction_time_ms", 0)
                print(f"    📊 {grid_info['total_points']} points | Time: {time_ms:.1f}ms")
        
        # Calculate performance summary
        if extraction_times:
            simulation_results["performance_summary"] = {
                "total_extractions": len(extraction_times),
                "successful_extractions": len([t for t in extraction_times if t > 0]),
                "average_extraction_time_ms": round(np.mean(extraction_times), 2),
                "max_extraction_time_ms": round(max(extraction_times), 2),
                "min_extraction_time_ms": round(min(extraction_times), 2)
            }
        
        # Analyze storage optimization
        simulation_results["storage_analysis"] = self._analyze_storage_optimization(latest_file)
        
        # Save results
        results_file = self.api_logs_path / f"api_simulation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(simulation_results, f, indent=2, default=str)
        
        print(f"\n💾 Results saved to: {results_file}")
        
        return simulation_results
    
    def _analyze_storage_optimization(self, data_file: Path) -> Dict[str, Any]:
        """Analyze storage requirements and optimization opportunities."""
        analysis = {
            "current_file_size_kb": round(data_file.stat().st_size / 1024, 1),
            "optimization_recommendations": [],
            "retention_strategy": {}
        }
        
        # Check if raw and intermediate files exist
        raw_files = list(self.data_root.glob("raw/sst/**/*.nc"))
        downsampled_files = list(self.data_root.glob("processed/sst_downsampled/**/*.nc"))
        harmonized_files = list(self.data_root.glob("processed/unified_coords/**/*.nc"))
        
        total_raw_size = sum(f.stat().st_size for f in raw_files) / 1024  # KB
        total_downsampled_size = sum(f.stat().st_size for f in downsampled_files) / 1024  # KB  
        total_harmonized_size = sum(f.stat().st_size for f in harmonized_files) / 1024  # KB
        
        analysis["storage_breakdown"] = {
            "raw_files": {"count": len(raw_files), "total_size_kb": round(total_raw_size, 1)},
            "downsampled_files": {"count": len(downsampled_files), "total_size_kb": round(total_downsampled_size, 1)},
            "harmonized_files": {"count": len(harmonized_files), "total_size_kb": round(total_harmonized_size, 1)}
        }
        
        # Optimization recommendations
        if total_raw_size > 0 and total_harmonized_size > 0:
            space_savings = total_raw_size + total_downsampled_size
            analysis["optimization_recommendations"].append(
                f"Remove raw and downsampled files after harmonization: Save {space_savings:.1f} KB per file"
            )
            
            analysis["retention_strategy"] = {
                "keep": "harmonized files only",
                "remove": "raw and downsampled files after successful harmonization",
                "space_savings_percent": round((space_savings / (total_raw_size + total_downsampled_size + total_harmonized_size)) * 100, 1),
                "final_size_per_file_kb": round(total_harmonized_size / max(len(harmonized_files), 1), 1)
            }
        
        return analysis
    
    def print_simulation_summary(self, results: Dict[str, Any]):
        """Print a comprehensive summary of simulation results."""
        print("\n" + "🌊" * 30)
        print("API EXTRACTION SIMULATION SUMMARY")
        print("🌊" * 30)
        
        # Performance summary
        perf = results.get("performance_summary", {})
        print(f"\n⚡ PERFORMANCE:")
        print(f"   Total extractions: {perf.get('total_extractions', 0)}")
        print(f"   Successful: {perf.get('successful_extractions', 0)}")
        print(f"   Average time: {perf.get('average_extraction_time_ms', 0):.1f}ms")
        print(f"   Max time: {perf.get('max_extraction_time_ms', 0):.1f}ms")
        
        # Validation summary
        validations = results.get("validation_results", {})
        status_counts = {}
        for validation in validations.values():
            status = validation.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"\n✅ VALIDATION:")
        for status, count in status_counts.items():
            emoji = {"passed": "✅", "warning": "⚠️", "failed": "❌"}.get(status, "❓")
            print(f"   {emoji} {status.title()}: {count}")
        
        # Storage analysis
        storage = results.get("storage_analysis", {})
        if "retention_strategy" in storage:
            strategy = storage["retention_strategy"]
            print(f"\n💾 STORAGE OPTIMIZATION:")
            print(f"   Current file size: {results['simulation_metadata']['file_size_kb']:.1f} KB")
            print(f"   Recommended: Keep {strategy.get('keep', 'N/A')}")
            print(f"   Space savings: {strategy.get('space_savings_percent', 0):.1f}%")
            print(f"   Final size per file: {strategy.get('final_size_per_file_kb', 0):.1f} KB")
        
        print(f"\n🚀 API READINESS: {'READY' if perf.get('average_extraction_time_ms', 999) < 100 else 'NEEDS OPTIMIZATION'}")
        print("🌊" * 30)


def main():
    """Main execution."""
    backend_path = Path(__file__).parent.parent
    data_root = backend_path.parent / "ocean-data"
    
    if not data_root.exists():
        print(f"❌ Error: Ocean data directory not found at {data_root}")
        return 1
    
    print("🌊 Ocean Data API Extraction Simulation")
    print(f"📁 Data directory: {data_root}")
    
    extractor = APIDataExtractor(data_root)
    results = extractor.run_api_simulation()
    
    if "error" in results:
        print(f"❌ Error: {results['error']}")
        return 1
    
    extractor.print_simulation_summary(results)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())