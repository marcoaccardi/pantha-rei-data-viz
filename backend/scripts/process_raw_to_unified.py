#!/usr/bin/env python3
"""
Script to process raw data files into unified coordinate system.
"""

import sys
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from processors.acidity_processor import AcidityProcessor
from processors.currents_processor import CurrentsProcessor
from processors.waves_processor import WavesProcessor

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_acidity_files():
    """Process all raw acidity files to unified coordinates."""
    logger.info("Processing acidity files...")
    
    processor = AcidityProcessor()
    
    # Find raw acidity files
    raw_acidity_path = Path("/Volumes/Backup/panta-rhei-data-map/ocean-data/raw/acidity")
    output_path = Path("/Volumes/Backup/panta-rhei-data-map/ocean-data/processed/unified_coords/acidity")
    
    if not raw_acidity_path.exists():
        logger.warning(f"No raw acidity directory found: {raw_acidity_path}")
        return 0
    
    # Find all NetCDF files
    raw_files = list(raw_acidity_path.rglob("*.nc"))
    logger.info(f"Found {len(raw_files)} raw acidity files")
    
    processed_count = 0
    
    for raw_file in raw_files:
        try:
            # Create output path maintaining directory structure
            relative_path = raw_file.relative_to(raw_acidity_path)
            output_file = output_path / relative_path.parent / f"acidity_harmonized_{raw_file.stem.split('_')[-1]}.nc"
            
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
    
    logger.info(f"Processed {processed_count} acidity files")
    return processed_count

def process_currents_files():
    """Process all raw currents files to unified coordinates.""" 
    logger.info("Processing currents files...")
    
    processor = CurrentsProcessor()
    
    # Find raw currents files
    raw_currents_path = Path("/Volumes/Backup/panta-rhei-data-map/ocean-data/raw/currents")
    output_path = Path("/Volumes/Backup/panta-rhei-data-map/ocean-data/processed/unified_coords/currents")
    
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

def process_waves_files():
    """Process all raw waves files to unified coordinates."""
    logger.info("Processing waves files...")
    
    processor = WavesProcessor()
    
    # Find raw waves files
    raw_waves_path = Path("/Volumes/Backup/panta-rhei-data-map/ocean-data/raw/waves")
    output_path = Path("/Volumes/Backup/panta-rhei-data-map/ocean-data/processed/unified_coords/waves")
    
    if not raw_waves_path.exists():
        logger.warning(f"No raw waves directory found: {raw_waves_path}")
        return 0
    
    # Find all NetCDF files
    raw_files = list(raw_waves_path.rglob("*.nc"))
    logger.info(f"Found {len(raw_files)} raw waves files")
    
    processed_count = 0
    
    for raw_file in raw_files:
        try:
            # Create output path maintaining directory structure
            relative_path = raw_file.relative_to(raw_waves_path)
            output_file = output_path / relative_path.parent / f"waves_processed_{raw_file.stem.split('_')[-1]}.nc"
            
            # Skip if already processed
            if output_file.exists():
                logger.info(f"Skipping already processed: {output_file.name}")
                continue
            
            logger.info(f"Processing: {raw_file.name}")
            
            success = processor.process_file(raw_file, output_file)
            
            if success:
                processed_count += 1
                logger.info(f"✓ Successfully processed: {output_file.name}")
            else:
                logger.error(f"✗ Failed to process: {raw_file.name}")
                
        except Exception as e:
            logger.error(f"Error processing {raw_file.name}: {e}")
    
    logger.info(f"Processed {processed_count} waves files")
    return processed_count

def main():
    """Process all raw data files."""
    logger.info("Starting raw data processing...")
    
    total_processed = 0
    
    # Process acidity files
    total_processed += process_acidity_files()
    
    # Process currents files  
    total_processed += process_currents_files()
    
    # Process waves files
    total_processed += process_waves_files()
    
    logger.info(f"Processing complete: {total_processed} files processed total")
    
    return total_processed

if __name__ == "__main__":
    processed = main()
    sys.exit(0)