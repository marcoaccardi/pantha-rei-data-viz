#!/usr/bin/env python3
"""
Process acidity_current raw data files to unified coordinate system.
"""

import sys
import logging
from pathlib import Path

# Add backend to path (script is in scripts/processing/, need to go up two levels to reach backend/)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from processors.acidity_processor import AcidityProcessor

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_acidity_current_files():
    """Process all raw acidity_current files to unified coordinates."""
    logger.info("Processing acidity_current files...")
    
    processor = AcidityProcessor()
    
    # Find raw acidity_current files
    raw_acidity_path = Path("../ocean-data/raw/acidity_current")
    output_path = Path("../ocean-data/processed/unified_coords/acidity_current")
    
    if not raw_acidity_path.exists():
        logger.warning(f"No raw acidity_current directory found: {raw_acidity_path}")
        return 0
    
    # Find all NetCDF files
    raw_files = list(raw_acidity_path.rglob("*.nc"))
    logger.info(f"Found {len(raw_files)} raw acidity_current files")
    
    processed_count = 0
    
    for raw_file in raw_files:
        try:
            # Create output path maintaining directory structure
            relative_path = raw_file.relative_to(raw_acidity_path)
            output_file = output_path / relative_path.parent / f"acidity_current_harmonized_{raw_file.stem.split('_')[-1]}.nc"
            
            # Skip if already processed
            if output_file.exists():
                logger.info(f"Skipping already processed: {output_file.name}")
                continue
            
            logger.info(f"Processing: {raw_file.name}")
            
            # Ensure output directory exists
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            success = processor.process_file(raw_file, output_file, surface_only=True)
            
            if success:
                processed_count += 1
                logger.info(f"✓ Successfully processed: {output_file.name}")
            else:
                logger.error(f"✗ Failed to process: {raw_file.name}")
                
        except Exception as e:
            logger.error(f"Error processing {raw_file.name}: {e}")
    
    logger.info(f"Processed {processed_count} acidity_current files")
    return processed_count

def main():
    """Process acidity_current files."""
    logger.info("Starting acidity_current data processing...")
    
    total_processed = process_acidity_current_files()
    
    logger.info(f"Processing complete: {total_processed} files processed")
    
    return total_processed

if __name__ == "__main__":
    processed = main()
    sys.exit(0)