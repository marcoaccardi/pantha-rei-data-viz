#!/usr/bin/env python3
"""
Organize OSCAR currents files from 2003-2020 into proper year/month directory structure.
Processes 6,575 files in batches to avoid system overload.
"""

import os
import shutil
from pathlib import Path
import re
from collections import defaultdict

def organize_oscar_files():
    """Organize OSCAR files from currents_2003_2020 into year/month structure."""
    
    # Paths
    base_dir = Path("/Volumes/Backup/panta-rhei-data-map/ocean-data/raw/currents")
    source_dir = base_dir / "currents_2003_2020"
    
    if not source_dir.exists():
        print(f"ERROR: Source directory not found: {source_dir}")
        return False
    
    # Get all OSCAR files
    oscar_files = list(source_dir.glob("oscar_currents_final_*.nc4"))
    print(f"Found {len(oscar_files)} OSCAR files to organize")
    
    if len(oscar_files) == 0:
        print("No files found to organize")
        return False
    
    # Parse filenames and group by year/month
    file_groups = defaultdict(list)
    
    for file_path in oscar_files:
        # Extract date from filename: oscar_currents_final_20030101.nc4
        match = re.search(r'oscar_currents_final_(\d{8})\.nc4', file_path.name)
        if match:
            date_str = match.group(1)
            year = date_str[:4]
            month = date_str[4:6]
            file_groups[(year, month)].append(file_path)
        else:
            print(f"WARNING: Could not parse date from {file_path.name}")
    
    print(f"Files organized into {len(file_groups)} year/month groups")
    
    # Process files by year/month groups
    total_moved = 0
    total_errors = 0
    
    for (year, month), files in sorted(file_groups.items()):
        target_dir = base_dir / year / month
        target_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\nProcessing {year}/{month}: {len(files)} files")
        
        for i, file_path in enumerate(files, 1):
            try:
                target_file = target_dir / file_path.name
                
                # Check if target already exists
                if target_file.exists():
                    print(f"  SKIP: {file_path.name} (already exists)")
                    continue
                
                # Move file
                shutil.move(str(file_path), str(target_file))
                total_moved += 1
                
                if i % 50 == 0 or i == len(files):
                    print(f"  Progress: {i}/{len(files)} files moved")
                    
            except Exception as e:
                print(f"  ERROR moving {file_path.name}: {e}")
                total_errors += 1
    
    print(f"\n✅ Organization complete!")
    print(f"   Files moved: {total_moved}")
    print(f"   Errors: {total_errors}")
    print(f"   Total processed: {total_moved + total_errors}")
    
    # Check if source directory is now empty
    remaining_files = list(source_dir.glob("*"))
    if len(remaining_files) == 0:
        print(f"   Source directory is empty - ready for cleanup")
    else:
        print(f"   WARNING: {len(remaining_files)} files remain in source directory")
    
    return total_errors == 0

if __name__ == "__main__":
    success = organize_oscar_files()
    exit(0 if success else 1)