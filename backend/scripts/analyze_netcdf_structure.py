#!/usr/bin/env python3
"""
Analyze NetCDF file structure for texture generation planning.
"""
import xarray as xr
import numpy as np
import sys
from pathlib import Path

def analyze_netcdf_file(file_path):
    """Analyze a single NetCDF file and return detailed structure information."""
    print(f"\n{'='*80}")
    print(f"ANALYZING: {file_path}")
    print(f"{'='*80}")
    
    try:
        # Load the dataset
        ds = xr.open_dataset(file_path)
        
        print(f"\nFILE SIZE: {Path(file_path).stat().st_size / (1024*1024):.2f} MB")
        
        # Dimensions
        print(f"\nDIMENSIONS:")
        for dim_name, dim_size in ds.sizes.items():
            print(f"  {dim_name}: {dim_size}")
        
        # Coordinates
        print(f"\nCOORDINATE VARIABLES:")
        for coord_name, coord in ds.coords.items():
            coord_data = coord.values
            if coord_data.size > 0:
                try:
                    min_val = np.nanmin(coord_data)
                    max_val = np.nanmax(coord_data)
                    print(f"  {coord_name}: {coord.dims} | Range: [{min_val:.6f}, {max_val:.6f}] | Shape: {coord.shape}")
                except (TypeError, ValueError):
                    print(f"  {coord_name}: {coord.dims} | Non-numeric data | Shape: {coord.shape}")
                if hasattr(coord, 'units'):
                    print(f"    Units: {coord.units}")
                if hasattr(coord, 'long_name'):
                    print(f"    Description: {coord.long_name}")
        
        # Data variables
        print(f"\nDATA VARIABLES:")
        for var_name, var in ds.data_vars.items():
            var_data = var.values
            if var_data.size > 0:
                try:
                    min_val = np.nanmin(var_data)
                    max_val = np.nanmax(var_data)
                    mean_val = np.nanmean(var_data)
                    valid_count = np.sum(~np.isnan(var_data))
                    total_count = var_data.size
                    print(f"  {var_name}: {var.dims}")
                    print(f"    Shape: {var.shape}")
                    print(f"    Data Range: [{min_val:.6f}, {max_val:.6f}]")
                    print(f"    Mean: {mean_val:.6f}")
                    print(f"    Valid Points: {valid_count}/{total_count} ({100*valid_count/total_count:.1f}%)")
                except (TypeError, ValueError):
                    print(f"  {var_name}: {var.dims}")
                    print(f"    Shape: {var.shape}")
                    print(f"    Non-numeric or complex data type")
                
                if hasattr(var, 'units'):
                    print(f"    Units: {var.units}")
                if hasattr(var, 'long_name'):
                    print(f"    Description: {var.long_name}")
                if hasattr(var, 'standard_name'):
                    print(f"    Standard Name: {var.standard_name}")
        
        # Global attributes
        print(f"\nGLOBAL ATTRIBUTES:")
        for attr_name, attr_value in ds.attrs.items():
            if len(str(attr_value)) < 100:  # Only show short attributes
                print(f"  {attr_name}: {attr_value}")
        
        # Memory usage estimate
        total_size = sum(var.nbytes for var in ds.data_vars.values())
        print(f"\nMEMORY USAGE: {total_size / (1024*1024):.2f} MB in memory")
        
        ds.close()
        return True
        
    except Exception as e:
        print(f"ERROR analyzing {file_path}: {e}")
        return False

def main():
    """Analyze all NetCDF files for texture generation."""
    files_to_analyze = [
        "/Volumes/Backup/panta-rhei-data-map/ocean-data/processed/unified_coords/sst/2024/01/sst_harmonized_20240115.nc",
        "/Volumes/Backup/panta-rhei-data-map/ocean-data/processed/unified_coords/acidity/2024/01/acidity_harmonized_20240106.nc",
        "/Volumes/Backup/panta-rhei-data-map/ocean-data/processed/unified_coords/currents/2024/07/currents_harmonized_20240725.nc",
        "/Volumes/Backup/panta-rhei-data-map/ocean-data/processed/unified_coords/waves/2024/07/waves_processed_20240723.nc"
    ]
    
    print("NetCDF File Structure Analysis for Texture Generation")
    print("=" * 60)
    
    success_count = 0
    for file_path in files_to_analyze:
        if Path(file_path).exists():
            if analyze_netcdf_file(file_path):
                success_count += 1
        else:
            print(f"\nFILE NOT FOUND: {file_path}")
    
    print(f"\n{'='*80}")
    print(f"ANALYSIS COMPLETE: {success_count}/{len(files_to_analyze)} files analyzed successfully")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()