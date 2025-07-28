#!/usr/bin/env python3
"""
OSCAR Currents Data Organization Script

Organizes existing OSCAR currents files from the Corals project into the proper
panta-rhei data structure with year/month directories.

Usage:
    python scripts/organize_oscar_currents.py
    python scripts/organize_oscar_currents.py --dry-run
"""

import argparse
import os
import shutil
import re
from pathlib import Path
from datetime import datetime


def organize_oscar_files():
    """Organize OSCAR currents files into proper structure."""
    
    # Source directory with existing OSCAR files
    source_dir = Path("/Volumes/Backup/WORK_2023/Corals/_ConsolidateTemp/ocean_datasets/currents_2021_2023")
    
    # Target directory in panta-rhei structure
    target_base = Path("/Volumes/Backup/panta-rhei-data-map/ocean-data/raw/currents_oscar")
    
    print("🔄 OSCAR Currents File Organization")
    print("=" * 50)
    print(f"Source: {source_dir}")
    print(f"Target: {target_base}")
    print()
    
    if not source_dir.exists():
        print(f"❌ ERROR: Source directory not found: {source_dir}")
        return False
    
    # Find all OSCAR files
    oscar_files = list(source_dir.glob("oscar_currents_nrt_*.nc4"))
    
    if not oscar_files:
        print("❌ ERROR: No OSCAR files found in source directory")
        return False
    
    print(f"📁 Found {len(oscar_files)} OSCAR files")
    print()
    
    # Pattern to extract date from filename
    date_pattern = re.compile(r'oscar_currents_nrt_(\d{8})\.dap\.nc4')
    
    organized_count = 0
    skipped_count = 0
    
    for file_path in sorted(oscar_files):
        filename = file_path.name
        
        # Extract date from filename
        match = date_pattern.match(filename)
        if not match:
            print(f"⚠️  Skipping file with unexpected format: {filename}")
            skipped_count += 1
            continue
        
        date_str = match.group(1)
        
        try:
            # Parse date
            file_date = datetime.strptime(date_str, "%Y%m%d")
            year = file_date.year
            month = f"{file_date.month:02d}"
            
            # Create target directory structure
            target_dir = target_base / str(year) / month
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Target filename (standardized)
            target_filename = f"oscar_currents_{date_str}.nc4"
            target_path = target_dir / target_filename
            
            # Check if file already exists
            if target_path.exists():
                print(f"⏭️  Already exists: {target_path.relative_to(target_base.parent)}")
                continue
            
            # Copy file
            print(f"📋 Copying: {filename} → {target_path.relative_to(target_base.parent)}")
            shutil.copy2(file_path, target_path)
            organized_count += 1
            
        except Exception as e:
            print(f"❌ Error processing {filename}: {e}")
            skipped_count += 1
    
    print()
    print("=" * 50)
    print("📊 ORGANIZATION SUMMARY")
    print("=" * 50)
    print(f"Files organized: {organized_count}")
    print(f"Files skipped: {skipped_count}")
    print(f"Total processed: {organized_count + skipped_count}")
    
    if organized_count > 0:
        print()
        print("✅ OSCAR files successfully organized!")
        print("📂 Directory structure:")
        
        # Show created directory structure
        for year_dir in sorted(target_base.glob("*")):
            if year_dir.is_dir():
                file_count = len(list(year_dir.glob("*/*.nc4")))
                print(f"   {year_dir.name}/: {file_count} files")
                for month_dir in sorted(year_dir.glob("*")):
                    if month_dir.is_dir():
                        month_files = len(list(month_dir.glob("*.nc4")))
                        print(f"     {month_dir.name}/: {month_files} files")
    
    return organized_count > 0


def main():
    parser = argparse.ArgumentParser(description='Organize OSCAR currents files')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be done without actually copying files')
    args = parser.parse_args()
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No files will be copied")
        print()
    
    success = organize_oscar_files()
    
    if success:
        print("\n🎯 Next steps:")
        print("1. Update sources.yaml to include OSCAR configuration")
        print("2. Create OSCAR currents downloader")
        print("3. Create hybrid currents system")
        return 0
    else:
        print("\n❌ Organization failed")
        return 1


if __name__ == "__main__":
    exit(main())