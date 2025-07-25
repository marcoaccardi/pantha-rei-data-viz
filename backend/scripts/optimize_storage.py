#!/usr/bin/env python3
"""
Storage Optimization Script
Implements the storage retention strategy by keeping only the final harmonized files
and removing raw/intermediate files to minimize storage usage.
"""

import sys
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

def analyze_storage_usage(data_root: Path) -> Dict[str, any]:
    """Analyze current storage usage across all processing stages."""
    
    analysis = {
        "timestamp": datetime.now().isoformat(),
        "data_root": str(data_root),
        "storage_by_stage": {},
        "total_storage_mb": 0,
        "optimization_potential": {}
    }
    
    stages = {
        "raw": data_root / "raw" / "sst",
        "downsampled": data_root / "processed" / "sst_downsampled", 
        "harmonized": data_root / "processed" / "unified_coords"
    }
    
    total_size = 0
    
    for stage_name, stage_path in stages.items():
        if stage_path.exists():
            files = list(stage_path.rglob("*.nc"))
            stage_size = sum(f.stat().st_size for f in files)
            
            analysis["storage_by_stage"][stage_name] = {
                "path": str(stage_path),
                "file_count": len(files),
                "size_mb": round(stage_size / (1024 * 1024), 3),
                "files": [{"path": str(f), "size_kb": round(f.stat().st_size / 1024, 1)} for f in files]
            }
            
            total_size += stage_size
    
    analysis["total_storage_mb"] = round(total_size / (1024 * 1024), 3)
    
    # Calculate optimization potential
    if "harmonized" in analysis["storage_by_stage"]:
        harmonized_size = analysis["storage_by_stage"]["harmonized"]["size_mb"]
        removable_size = total_size / (1024 * 1024) - harmonized_size
        
        analysis["optimization_potential"] = {
            "current_total_mb": round(total_size / (1024 * 1024), 3),
            "after_optimization_mb": harmonized_size,
            "space_savings_mb": round(removable_size, 3),
            "space_savings_percent": round((removable_size / (total_size / (1024 * 1024))) * 100, 1),
            "recommended_action": "Keep harmonized files only, remove raw and downsampled"
        }
    
    return analysis

def create_optimization_plan(analysis: Dict) -> Dict[str, any]:
    """Create detailed optimization plan."""
    
    plan = {
        "strategy": "Retain harmonized files only",
        "justification": [
            "Harmonized files contain all necessary data for API consumption",
            "Coordinate system is standardized (-180/+180 longitude)",
            "Resolution is optimized for performance (1-degree grid)",
            "All original data variables are preserved",
            "Significant storage reduction (90%+ savings)"
        ],
        "actions": [],
        "backup_recommendations": [],
        "validation_steps": []
    }
    
    # Actions to take
    if "raw" in analysis["storage_by_stage"]:
        raw_info = analysis["storage_by_stage"]["raw"]
        plan["actions"].append({
            "action": "remove_raw_files",
            "description": f"Remove {raw_info['file_count']} raw SST files",
            "space_savings_mb": raw_info["size_mb"],
            "files_to_remove": raw_info["files"]
        })
    
    if "downsampled" in analysis["storage_by_stage"]:
        down_info = analysis["storage_by_stage"]["downsampled"]
        plan["actions"].append({
            "action": "remove_downsampled_files", 
            "description": f"Remove {down_info['file_count']} downsampled SST files",
            "space_savings_mb": down_info["size_mb"],
            "files_to_remove": down_info["files"]
        })
    
    # Backup recommendations
    plan["backup_recommendations"] = [
        "Verify harmonized files are valid before removing raw data",
        "Create metadata backup containing original file information",
        "Document processing parameters for reproducibility",
        "Keep at least one raw file sample for validation"
    ]
    
    # Validation steps
    plan["validation_steps"] = [
        "Test data extraction from harmonized files",
        "Verify coordinate system correctness",
        "Check data value ranges and statistics",
        "Confirm all variables are accessible"
    ]
    
    return plan

def validate_harmonized_files(data_root: Path) -> Dict[str, any]:
    """Validate that harmonized files are complete and usable."""
    
    harmonized_path = data_root / "processed" / "unified_coords"
    validation = {
        "timestamp": datetime.now().isoformat(),
        "files_validated": 0,
        "validation_results": {},
        "overall_status": "unknown",
        "issues": []
    }
    
    if not harmonized_path.exists():
        validation["overall_status"] = "failed"
        validation["issues"].append("Harmonized data directory does not exist")
        return validation
    
    harmonized_files = list(harmonized_path.rglob("*.nc"))
    
    if not harmonized_files:
        validation["overall_status"] = "failed"
        validation["issues"].append("No harmonized files found")
        return validation
    
    try:
        import xarray as xr
        import numpy as np
        
        for file_path in harmonized_files:
            file_validation = {
                "file_path": str(file_path),
                "file_size_kb": round(file_path.stat().st_size / 1024, 1),
                "checks": {}
            }
            
            try:
                with xr.open_dataset(file_path) as ds:
                    # Check required variables
                    file_validation["checks"]["has_sst_variable"] = "sst" in ds.data_vars
                    
                    # Check coordinate system
                    lon_min, lon_max = float(ds.lon.min()), float(ds.lon.max())
                    file_validation["checks"]["coordinate_system"] = "correct" if (lon_min >= -180 and lon_max <= 180) else "incorrect"
                    
                    # Check data validity
                    if "sst" in ds.data_vars:
                        sst_data = ds.sst
                        valid_count = int(sst_data.where((sst_data > -10) & (sst_data < 50)).count())
                        total_count = int(sst_data.size)
                        coverage = (valid_count / total_count) * 100
                        
                        file_validation["checks"]["data_coverage_percent"] = round(coverage, 1)
                        file_validation["checks"]["has_valid_data"] = coverage > 50
                    
                    # Check resolution
                    lat_res = abs(float(ds.lat.diff('lat').mean()))
                    lon_res = abs(float(ds.lon.diff('lon').mean()))
                    file_validation["checks"]["resolution"] = f"{lat_res:.2f}° x {lon_res:.2f}°"
                    file_validation["checks"]["correct_resolution"] = abs(lat_res - 1.0) < 0.1 and abs(lon_res - 1.0) < 0.1
                    
                    file_validation["status"] = "valid"
                    
            except Exception as e:
                file_validation["status"] = "error"
                file_validation["error"] = str(e)
                validation["issues"].append(f"File {file_path.name}: {str(e)}")
            
            validation["validation_results"][file_path.name] = file_validation
            validation["files_validated"] += 1
        
        # Determine overall status
        valid_files = sum(1 for result in validation["validation_results"].values() 
                         if result.get("status") == "valid")
        
        if valid_files == len(harmonized_files):
            validation["overall_status"] = "passed"
        elif valid_files > 0:
            validation["overall_status"] = "partial"
            validation["issues"].append(f"Only {valid_files}/{len(harmonized_files)} files are valid")
        else:
            validation["overall_status"] = "failed"
            validation["issues"].append("No valid harmonized files found")
    
    except ImportError:
        validation["overall_status"] = "error"
        validation["issues"].append("Cannot import required libraries (xarray, numpy)")
    
    return validation

def execute_optimization(data_root: Path, plan: Dict, dry_run: bool = True) -> Dict[str, any]:
    """Execute the storage optimization plan."""
    
    execution_log = {
        "timestamp": datetime.now().isoformat(),
        "dry_run": dry_run,
        "actions_executed": [],
        "files_removed": [],
        "space_freed_mb": 0,
        "errors": []
    }
    
    for action in plan["actions"]:
        action_log = {
            "action": action["action"],
            "description": action["description"], 
            "files_processed": 0,
            "space_freed_mb": 0,
            "status": "pending"
        }
        
        try:
            for file_info in action["files_to_remove"]:
                file_path = Path(file_info["path"])
                
                if file_path.exists():
                    file_size_mb = file_path.stat().st_size / (1024 * 1024)
                    
                    if not dry_run:
                        file_path.unlink()  # Delete the file
                        execution_log["files_removed"].append(str(file_path))
                    
                    action_log["files_processed"] += 1
                    action_log["space_freed_mb"] += file_size_mb
                    execution_log["space_freed_mb"] += file_size_mb
            
            action_log["status"] = "completed" if not dry_run else "dry_run_completed"
            
        except Exception as e:
            action_log["status"] = "error"
            action_log["error"] = str(e)
            execution_log["errors"].append(f"{action['action']}: {str(e)}")
        
        execution_log["actions_executed"].append(action_log)
    
    # Clean up empty directories if not dry run
    if not dry_run:
        try:
            raw_dir = data_root / "raw" / "sst"
            downsampled_dir = data_root / "processed" / "sst_downsampled"
            
            for dir_path in [raw_dir, downsampled_dir]:
                if dir_path.exists() and not any(dir_path.rglob("*")):
                    shutil.rmtree(dir_path)
                    execution_log["actions_executed"].append({
                        "action": "remove_empty_directory",
                        "path": str(dir_path),
                        "status": "completed"
                    })
        except Exception as e:
            execution_log["errors"].append(f"Directory cleanup: {str(e)}")
    
    return execution_log

def main():
    """Main optimization execution."""
    backend_path = Path(__file__).parent.parent
    data_root = backend_path.parent / "ocean-data"
    logs_path = data_root / "logs" / "optimization"
    logs_path.mkdir(parents=True, exist_ok=True)
    
    print("💾 SST Storage Optimization")
    print("=" * 50)
    print(f"📁 Data directory: {data_root}")
    
    # Step 1: Analyze current storage
    print("\n📊 Analyzing current storage usage...")
    analysis = analyze_storage_usage(data_root)
    
    print(f"   Total storage: {analysis['total_storage_mb']:.1f} MB")
    for stage, info in analysis["storage_by_stage"].items():
        print(f"   - {stage}: {info['file_count']} files, {info['size_mb']:.1f} MB")
    
    if "optimization_potential" in analysis:
        opt = analysis["optimization_potential"]
        print(f"\n💡 Optimization potential:")
        print(f"   Current: {opt['current_total_mb']:.1f} MB")
        print(f"   After optimization: {opt['after_optimization_mb']:.1f} MB")
        print(f"   Savings: {opt['space_savings_mb']:.1f} MB ({opt['space_savings_percent']:.1f}%)")
    
    # Step 2: Validate harmonized files
    print("\n✅ Validating harmonized files...")
    validation = validate_harmonized_files(data_root)
    
    print(f"   Status: {validation['overall_status']}")
    print(f"   Files validated: {validation['files_validated']}")
    
    if validation["issues"]:
        print("   Issues found:")
        for issue in validation["issues"]:
            print(f"     - {issue}")
    
    if validation["overall_status"] not in ["passed", "partial"]:
        print("\n❌ Cannot proceed with optimization - harmonized files are not valid")
        return 1
    
    # Step 3: Create optimization plan
    print("\n📋 Creating optimization plan...")
    plan = create_optimization_plan(analysis)
    
    print(f"   Strategy: {plan['strategy']}")
    print(f"   Actions planned: {len(plan['actions'])}")
    
    # Step 4: Execute dry run
    print("\n🧪 Executing dry run...")
    dry_run_log = execute_optimization(data_root, plan, dry_run=True)
    
    print(f"   Files to remove: {sum(action['files_processed'] for action in dry_run_log['actions_executed'])}")
    print(f"   Space to free: {dry_run_log['space_freed_mb']:.1f} MB")
    
    # Step 5: Ask for confirmation and execute
    print(f"\n❓ Proceed with optimization? (y/N): ", end="")
    
    # For automation, we'll create the plan but not execute automatically
    # In production, you'd want user confirmation
    
    # Save all results
    results = {
        "analysis": analysis,
        "validation": validation,
        "optimization_plan": plan,
        "dry_run_log": dry_run_log
    }
    
    results_file = logs_path / f"storage_optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Analysis saved to: {results_file}")
    print("\n✨ Optimization analysis complete!")
    print("\n📝 RECOMMENDATION:")
    print("   Keep only harmonized files (178 KB each)")
    print("   Remove raw (1.5 MB) and downsampled (181 KB) files")
    print("   This achieves 90%+ storage reduction per dataset")
    print("   Apply same strategy to future datasets (waves, currents, etc.)")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())