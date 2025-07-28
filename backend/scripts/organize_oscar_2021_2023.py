#!/usr/bin/env python3
"""
Organize OSCAR currents files from currents_2021_2023 into proper year/month directory structure.
Processes 885 files covering 2021-2023 period.
"""

import os
import shutil
from pathlib import Path
import re
from collections import defaultdict

def organize_oscar_2021_2023_files():
    """Organize OSCAR files from currents_2021_2023 into year/month structure."""
    
    # Paths
    base_dir = Path("/Volumes/Backup/panta-rhei-data-map/ocean-data/raw/currents")
    source_dir = base_dir / "currents_2021_2023"
    
    if not source_dir.exists():
        print(f"ERROR: Source directory not found: {source_dir}")
        return False
    
    # Get all OSCAR files
    oscar_files = list(source_dir.glob("oscar_currents_nrt_*.nc4"))
    print(f"Found {len(oscar_files)} OSCAR files to organize")
    
    if len(oscar_files) == 0:
        print("No files found to organize")
        return False
    
    # Parse filenames and group by year/month
    file_groups = defaultdict(list)
    
    for file_path in oscar_files:
        # Extract date from filename: oscar_currents_nrt_20210101.dap.nc4
        match = re.search(r'oscar_currents_nrt_(\d{8})\.dap\.nc4', file_path.name)
        if match:
            date_str = match.group(1)
            year = date_str[:4]
            month = date_str[4:6]
            file_groups[(year, month)].append(file_path)
        else:
            print(f"WARNING: Could not parse date from {file_path.name}")
    
    print(f"Files organized into {len(file_groups)} year/month groups")
    
    # Check for date range
    dates = []
    for (year, month), files in file_groups.items():
        for file_path in files:
            match = re.search(r'oscar_currents_nrt_(\d{8})\.dap\.nc4', file_path.name)
            if match:
                dates.append(match.group(1))
    
    if dates:
        dates.sort()
        print(f"Date range: {dates[0]} to {dates[-1]}")
    
    # Process files by year/month groups
    total_moved = 0
    total_errors = 0
    total_skipped = 0
    
    for (year, month), files in sorted(file_groups.items()):
        target_dir = base_dir / year / month
        target_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\nProcessing {year}/{month}: {len(files)} files")
        
        for i, file_path in enumerate(files, 1):
            try:
                # Rename to standard format: remove 'nrt_' and '.dap' parts
                original_name = file_path.name  # oscar_currents_nrt_20210101.dap.nc4
                # Extract date and create new name: oscar_currents_final_20210101.nc4
                match = re.search(r'oscar_currents_nrt_(\d{8})\.dap\.nc4', original_name)
                if match:
                    date_str = match.group(1)
                    new_name = f"oscar_currents_final_{date_str}.nc4"
                else:
                    # Fallback: just clean up the name
                    new_name = original_name.replace('_nrt_', '_final_').replace('.dap.nc4', '.nc4')
                
                target_file = target_dir / new_name
                
                # Check if target already exists
                if target_file.exists():
                    print(f"  SKIP: {new_name} (already exists)")
                    total_skipped += 1
                    continue
                
                # Move and rename file
                shutil.move(str(file_path), str(target_file))
                total_moved += 1
                
                if i % 50 == 0 or i == len(files):
                    print(f"  Progress: {i}/{len(files)} files processed")
                    
            except Exception as e:
                print(f"  ERROR processing {file_path.name}: {e}")
                total_errors += 1
    
    print(f"\n✅ Organization complete!")
    print(f"   Files moved: {total_moved}")
    print(f"   Files skipped: {total_skipped}")
    print(f"   Errors: {total_errors}")
    print(f"   Total processed: {total_moved + total_skipped + total_errors}")
    
    # Check if source directory is now empty
    remaining_files = list(source_dir.glob("*"))
    if len(remaining_files) == 0:
        print(f"   Source directory is empty - ready for cleanup")
    else:
        print(f"   WARNING: {len(remaining_files)} files remain in source directory")
    
    return total_errors == 0

if __name__ == "__main__":
    success = organize_oscar_2021_2023_files()
    exit(0 if success else 1)