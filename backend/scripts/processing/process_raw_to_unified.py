#!/usr/bin/env python3
"""
Script to process raw data files into unified coordinate system.
"""

import sys
import logging
from pathlib import Path

# Add backend to path (script is in scripts/processing/, need to go up two levels to reach backend/)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from processors.acidity_processor import AcidityProcessor
from processors.currents_processor import CurrentsProcessor

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_acidity_files():
    """Process all raw acidity files to unified coordinates."""
    logger.info("Processing acidity files...")
    
    processor = AcidityProcessor()
    total_processed_count = 0
    
    # Process both acidity_current and acidity_historical directories
    acidity_dirs = [
        ("acidity_current", "acidity_current"),
        ("acidity_historical", "acidity_historical")
    ]
    
    for raw_dir_name, output_dir_name in acidity_dirs:
        raw_acidity_path = Path(f"../ocean-data/raw/{raw_dir_name}")
        output_path = Path(f"../ocean-data/processed/unified_coords/{output_dir_name}")
        
        if not raw_acidity_path.exists():
            logger.warning(f"No raw {raw_dir_name} directory found: {raw_acidity_path}")
            continue
        
        # Find all NetCDF files
        raw_files = list(raw_acidity_path.rglob("*.nc"))
        logger.info(f"Found {len(raw_files)} raw {raw_dir_name} files")
        
        processed_count = 0
        
        for raw_file in raw_files:
            try:
                # Create output path maintaining directory structure
                relative_path = raw_file.relative_to(raw_acidity_path)
                output_file = output_path / relative_path.parent / f"{raw_dir_name}_harmonized_{raw_file.stem.split('_')[-1]}.nc"
                
                # Skip if already processed
                if output_file.exists():
                    logger.info(f"Skipping already processed: {output_file.name}")
                    continue
                
                logger.info(f"Processing: {raw_file.name}")
                
                success = processor.process_file(raw_file, output_file, surface_only=True)
                
                if success:
                    processed_count += 1
                    logger.info(f"✓ Successfully processed: {output_file.name}")
                else:
                    logger.error(f"✗ Failed to process: {raw_file.name}")
                    
            except Exception as e:
                logger.error(f"Error processing {raw_file.name}: {e}")
        
        logger.info(f"Processed {processed_count} {raw_dir_name} files")
        total_processed_count += processed_count
    
    logger.info(f"Total processed acidity files: {total_processed_count}")
    return total_processed_count

def process_currents_files():
    """Process all raw currents files to unified coordinates.""" 
    logger.info("Processing currents files...")
    
    processor = CurrentsProcessor()
    
    # Find raw currents files
    raw_currents_path = Path("../ocean-data/raw/currents")
    output_path = Path("../ocean-data/processed/unified_coords/currents")
    
    if not raw_currents_path.exists():
        logger.warning(f"No raw currents directory found: {raw_currents_path}")
        return 0
    
    # Find all NetCDF files
    raw_files = list(raw_currents_path.rglob("*.nc"))
    logger.info(f"Found {len(raw_files)} raw currents files")
    
    processed_count = 0
    
    for raw_file in raw_files:
        try:
            # Create output path maintaining directory structure
            relative_path = raw_file.relative_to(raw_currents_path)
            output_file = output_path / relative_path.parent / f"currents_harmonized_{raw_file.stem.split('_')[-1]}.nc"
            
            # Skip if already processed
            if output_file.exists():
                logger.info(f"Skipping already processed: {output_file.name}")
                continue
            
            logger.info(f"Processing: {raw_file.name}")
            
            success = processor.process_file(raw_file, output_file, surface_only=True)
            
            if success:
                processed_count += 1
                logger.info(f"✓ Successfully processed: {output_file.name}")
            else:
                logger.error(f"✗ Failed to process: {raw_file.name}")
                
        except Exception as e:
            logger.error(f"Error processing {raw_file.name}: {e}")
    
    logger.info(f"Processed {processed_count} currents files")
    return processed_count


def main():
    """Process all raw data files."""
    logger.info("Starting raw data processing...")
    
    total_processed = 0
    
    # Process acidity files
    total_processed += process_acidity_files()
    
    # Process currents files  
    total_processed += process_currents_files()
    
    
    logger.info(f"Processing complete: {total_processed} files processed total")
    
    return total_processed

if __name__ == "__main__":
    processed = main()
    sys.exit(0)