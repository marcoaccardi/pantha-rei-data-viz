#!/usr/bin/env python3
"""
Safe bulk rename script for currents files standardization.
Renames all currents_oscar_harmonized_*.nc files to currents_harmonized_*.nc
to create uniform naming across all historical and current data.
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple
import shutil
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('currents_rename.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def find_oscar_files(base_path: Path) -> List[Path]:
    """Find all files with OSCAR naming pattern."""
    pattern = "**/currents_oscar_harmonized_*.nc"
    oscar_files = list(base_path.rglob(pattern))
    logger.info(f"Found {len(oscar_files)} files with OSCAR naming pattern")
    return oscar_files

def generate_new_name(oscar_file: Path) -> Path:
    """Generate the new standardized filename."""
    old_name = oscar_file.name
    new_name = old_name.replace("currents_oscar_harmonized_", "currents_harmonized_")
    new_path = oscar_file.parent / new_name
    return new_path

def dry_run_rename(oscar_files: List[Path]) -> List[Tuple[Path, Path]]:
    """Perform dry run to check what will be renamed."""
    rename_operations = []
    conflicts = []
    
    for oscar_file in oscar_files:
        new_path = generate_new_name(oscar_file)
        
        if new_path.exists():
            conflicts.append((oscar_file, new_path))
            logger.warning(f"CONFLICT: Target already exists: {new_path}")
        else:
            rename_operations.append((oscar_file, new_path))
    
    logger.info(f"DRY RUN RESULTS:")
    logger.info(f"  - Files to rename: {len(rename_operations)}")
    logger.info(f"  - Conflicts found: {len(conflicts)}")
    
    if conflicts:
        logger.error("Cannot proceed with conflicts. Please resolve manually.")
        return []
    
    return rename_operations

def verify_file_integrity(old_path: Path, new_path: Path) -> bool:
    """Verify file was renamed correctly."""
    if not new_path.exists():
        logger.error(f"New file doesn't exist: {new_path}")
        return False
    
    if old_path.exists():
        logger.error(f"Old file still exists: {old_path}")
        return False
    
    # Check file size is reasonable (> 100MB for currents files)
    file_size = new_path.stat().st_size
    if file_size < 100 * 1024 * 1024:  # Less than 100MB
        logger.warning(f"File size seems small: {new_path} ({file_size / 1024 / 1024:.1f}MB)")
    
    return True

def execute_rename_operation(rename_operations: List[Tuple[Path, Path]], test_mode: bool = False) -> bool:
    """Execute the rename operations."""
    if test_mode:
        logger.info("TEST MODE: Only renaming first 10 files")
        rename_operations = rename_operations[:10]
    
    success_count = 0
    failed_operations = []
    
    for i, (old_path, new_path) in enumerate(rename_operations, 1):
        try:
            logger.info(f"[{i}/{len(rename_operations)}] Renaming: {old_path.name} → {new_path.name}")
            
            # Perform the rename
            old_path.rename(new_path)
            
            # Verify the operation
            if verify_file_integrity(old_path, new_path):
                success_count += 1
                if i % 100 == 0:  # Progress update every 100 files
                    logger.info(f"Progress: {i}/{len(rename_operations)} files renamed")
            else:
                failed_operations.append((old_path, new_path))
                # Try to restore if verification failed
                if new_path.exists() and not old_path.exists():
                    logger.warning(f"Restoring failed rename: {new_path} → {old_path}")
                    new_path.rename(old_path)
                
        except Exception as e:
            logger.error(f"Failed to rename {old_path}: {e}")
            failed_operations.append((old_path, new_path))
    
    logger.info(f"RENAME OPERATION COMPLETE:")
    logger.info(f"  - Successfully renamed: {success_count}")
    logger.info(f"  - Failed operations: {len(failed_operations)}")
    
    if failed_operations:
        logger.error("Failed operations:")
        for old_path, new_path in failed_operations:
            logger.error(f"  - {old_path} → {new_path}")
        return False
    
    return True

def verify_final_state(base_path: Path) -> bool:
    """Verify the final state after rename operations."""
    # Count remaining OSCAR files
    remaining_oscar = list(base_path.rglob("**/currents_oscar_harmonized_*.nc"))
    total_currents = list(base_path.rglob("**/currents_harmonized_*.nc"))
    
    logger.info(f"FINAL STATE VERIFICATION:")
    logger.info(f"  - Remaining OSCAR files: {len(remaining_oscar)}")
    logger.info(f"  - Total harmonized files: {len(total_currents)}")
    
    if remaining_oscar:
        logger.error("Some OSCAR files were not renamed:")
        for oscar_file in remaining_oscar[:10]:  # Show first 10
            logger.error(f"  - {oscar_file}")
        return False
    
    logger.info("✅ All files successfully standardized to currents_harmonized_*.nc pattern")
    return True

def main():
    """Main execution function."""
    base_path = Path("/media/anecoica/ANECOICA_DEV/pantha-rei-data-viz/ocean-data/processed/unified_coords/currents")
    
    if not base_path.exists():
        logger.error(f"Base path does not exist: {base_path}")
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("CURRENTS FILES STANDARDIZATION SCRIPT")
    logger.info("=" * 60)
    
    # Find all OSCAR files
    oscar_files = find_oscar_files(base_path)
    if not oscar_files:
        logger.info("No OSCAR files found. Nothing to rename.")
        return
    
    # Perform dry run
    logger.info("\nPerforming dry run...")
    rename_operations = dry_run_rename(oscar_files)
    if not rename_operations:
        logger.error("Dry run failed or conflicts found. Exiting.")
        sys.exit(1)
    
    # Ask for confirmation
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logger.info("\nRunning in TEST MODE (first 10 files only)")
        test_mode = True
    elif len(sys.argv) > 1 and sys.argv[1] == "--execute":
        logger.info("\nExecuting full rename operation...")
        test_mode = False
    else:
        print(f"\nReady to rename {len(rename_operations)} files.")
        print("Usage:")
        print("  --test     : Rename only first 10 files (test mode)")
        print("  --execute  : Execute full rename operation")
        sys.exit(0)
    
    # Execute rename operation
    success = execute_rename_operation(rename_operations, test_mode)
    
    if success:
        # Verify final state
        verify_final_state(base_path)
        logger.info("✅ Rename operation completed successfully!")
    else:
        logger.error("❌ Rename operation completed with errors.")
        sys.exit(1)

if __name__ == "__main__":
    main()