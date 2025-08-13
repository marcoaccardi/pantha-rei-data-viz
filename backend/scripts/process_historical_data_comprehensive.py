#!/usr/bin/env python3
"""
Comprehensive historical data processing script.
Processes all unprocessed raw data files into unified coordinate system.
Handles: acidity_historical, acidity_current, OSCAR currents (2003-2022), and CMEMS currents.
"""

import sys
import logging
from pathlib import Path
import time
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from processors.acidity_processor import AcidityProcessor
from processors.currents_processor import CurrentsProcessor

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_acidity_historical_files():
    """Process all raw acidity_historical files to unified coordinates."""
    logger.info("Processing acidity_historical files...")
    
    processor = AcidityProcessor()
    
    # Find raw acidity_historical files
    raw_acidity_path = Path("../ocean-data/raw/acidity_historical")
    output_path = Path("../ocean-data/processed/unified_coords/acidity_historical")
    
    if not raw_acidity_path.exists():
        logger.warning(f"No raw acidity_historical directory found: {raw_acidity_path}")
        return 0
    
    # Find all NetCDF files
    raw_files = list(raw_acidity_path.rglob("*.nc"))
    logger.info(f"Found {len(raw_files)} raw acidity_historical files")
    
    if len(raw_files) == 0:
        return 0
    
    processed_count = 0
    failed_count = 0
    
    for i, raw_file in enumerate(raw_files, 1):
        try:
            # Create output path maintaining directory structure
            relative_path = raw_file.relative_to(raw_acidity_path)
            output_file = output_path / relative_path.parent / f"acidity_historical_harmonized_{raw_file.stem.split('_')[-1]}.nc"
            
            # Skip if already processed
            if output_file.exists():
                if i % 100 == 0:  # Log every 100th skip
                    logger.info(f"Progress: {i}/{len(raw_files)} - Skipping already processed: {output_file.name}")
                continue
            
            # Ensure output directory exists
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Processing {i}/{len(raw_files)}: {raw_file.name}")
            
            success = processor.process_file(raw_file, output_file, surface_only=True)
            
            if success:
                processed_count += 1
                logger.info(f"✓ Successfully processed: {output_file.name}")
            else:
                failed_count += 1
                logger.error(f"✗ Failed to process: {raw_file.name}")
                
        except Exception as e:
            failed_count += 1
            logger.error(f"Error processing {raw_file.name}: {e}")
    
    logger.info(f"Acidity Historical: Processed {processed_count}, Failed {failed_count}, Total {len(raw_files)}")
    return processed_count

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
    
    if len(raw_files) == 0:
        return 0
    
    processed_count = 0
    failed_count = 0
    
    for i, raw_file in enumerate(raw_files, 1):
        try:
            # Create output path maintaining directory structure
            relative_path = raw_file.relative_to(raw_acidity_path)
            output_file = output_path / relative_path.parent / f"acidity_current_harmonized_{raw_file.stem.split('_')[-1]}.nc"
            
            # Skip if already processed
            if output_file.exists():
                logger.info(f"Skipping already processed: {output_file.name}")
                continue
            
            # Ensure output directory exists
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Processing {i}/{len(raw_files)}: {raw_file.name}")
            
            success = processor.process_file(raw_file, output_file, surface_only=True)
            
            if success:
                processed_count += 1
                logger.info(f"✓ Successfully processed: {output_file.name}")
            else:
                failed_count += 1
                logger.error(f"✗ Failed to process: {raw_file.name}")
                
        except Exception as e:
            failed_count += 1
            logger.error(f"Error processing {raw_file.name}: {e}")
    
    logger.info(f"Acidity Current: Processed {processed_count}, Failed {failed_count}, Total {len(raw_files)}")
    return processed_count

def process_currents_oscar_files():
    """Process all raw OSCAR currents files (2003-2022) to unified coordinates.""" 
    logger.info("Processing OSCAR currents files (2003-2022)...")
    
    processor = CurrentsProcessor()
    
    # Find raw currents files - specifically OSCAR files
    raw_currents_path = Path("../ocean-data/raw/currents")
    output_path = Path("../ocean-data/processed/unified_coords/currents")
    
    if not raw_currents_path.exists():
        logger.warning(f"No raw currents directory found: {raw_currents_path}")
        return 0
    
    # Find all OSCAR NetCDF files (oscar_currents_final_*.nc4)
    raw_files = list(raw_currents_path.rglob("oscar_*.nc4"))
    logger.info(f"Found {len(raw_files)} OSCAR currents files")
    
    if len(raw_files) == 0:
        return 0
    
    processed_count = 0
    failed_count = 0
    
    for i, raw_file in enumerate(raw_files, 1):
        try:
            # Extract date from filename (oscar_currents_final_YYYYMMDD.nc4)
            filename_parts = raw_file.stem.split('_')
            if len(filename_parts) >= 4:
                date_str = filename_parts[-1]  # YYYYMMDD
            else:
                logger.warning(f"Cannot extract date from {raw_file.name}")
                continue
            
            # Create output path maintaining directory structure
            relative_path = raw_file.relative_to(raw_currents_path)
            output_file = output_path / relative_path.parent / f"currents_oscar_harmonized_{date_str}.nc"
            
            # Skip if already processed
            if output_file.exists():
                if i % 1000 == 0:  # Log every 1000th skip for OSCAR files
                    logger.info(f"Progress: {i}/{len(raw_files)} - Skipping already processed: {output_file.name}")
                continue
            
            # Ensure output directory exists
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            if i % 100 == 0:  # Log progress every 100 files
                logger.info(f"Processing OSCAR {i}/{len(raw_files)}: {raw_file.name}")
            
            success = processor.process_file(raw_file, output_file, surface_only=True)
            
            if success:
                processed_count += 1
                if processed_count % 50 == 0:  # Log every 50 successful processes
                    logger.info(f"✓ Successfully processed {processed_count} OSCAR files")
            else:
                failed_count += 1
                logger.error(f"✗ Failed to process: {raw_file.name}")
                
        except Exception as e:
            failed_count += 1
            logger.error(f"Error processing {raw_file.name}: {e}")
    
    logger.info(f"OSCAR Currents: Processed {processed_count}, Failed {failed_count}, Total {len(raw_files)}")
    return processed_count

def process_currents_cmems_files():
    """Process remaining CMEMS currents files to unified coordinates.""" 
    logger.info("Processing CMEMS currents files...")
    
    processor = CurrentsProcessor()
    
    # Find raw currents files - specifically CMEMS files
    raw_currents_path = Path("../ocean-data/raw/currents")
    output_path = Path("../ocean-data/processed/unified_coords/currents")
    
    if not raw_currents_path.exists():
        logger.warning(f"No raw currents directory found: {raw_currents_path}")
        return 0
    
    # Find all CMEMS NetCDF files (currents_global_*.nc)
    raw_files = list(raw_currents_path.rglob("currents_global_*.nc"))
    logger.info(f"Found {len(raw_files)} CMEMS currents files")
    
    if len(raw_files) == 0:
        return 0
    
    processed_count = 0
    failed_count = 0
    
    for i, raw_file in enumerate(raw_files, 1):
        try:
            # Create output path maintaining directory structure
            relative_path = raw_file.relative_to(raw_currents_path)
            output_file = output_path / relative_path.parent / f"currents_harmonized_{raw_file.stem.split('_')[-1]}.nc"
            
            # Skip if already processed
            if output_file.exists():
                logger.info(f"Skipping already processed: {output_file.name}")
                continue
            
            # Ensure output directory exists
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Processing CMEMS {i}/{len(raw_files)}: {raw_file.name}")
            
            success = processor.process_file(raw_file, output_file, surface_only=True)
            
            if success:
                processed_count += 1
                logger.info(f"✓ Successfully processed: {output_file.name}")
            else:
                failed_count += 1
                logger.error(f"✗ Failed to process: {raw_file.name}")
                
        except Exception as e:
            failed_count += 1
            logger.error(f"Error processing {raw_file.name}: {e}")
    
    logger.info(f"CMEMS Currents: Processed {processed_count}, Failed {failed_count}, Total {len(raw_files)}")
    return processed_count

def main():
    """Process all raw data files comprehensively."""
    start_time = time.time()
    logger.info("=" * 60)
    logger.info("COMPREHENSIVE HISTORICAL DATA PROCESSING")
    logger.info("=" * 60)
    
    total_processed = 0
    
    # Phase 1: Process acidity historical files (2003-2016)
    logger.info("\n🧪 PHASE 1: Processing Acidity Historical Data (2003-2016)")
    total_processed += process_acidity_historical_files()
    
    # Phase 2: Process acidity current files (2023-2025)  
    logger.info("\n🧪 PHASE 2: Processing Acidity Current Data (2023-2025)")
    total_processed += process_acidity_current_files()
    
    # Phase 3: Process OSCAR currents files (2003-2022) - THE BIG ONE
    logger.info("\n🌊 PHASE 3: Processing OSCAR Currents Data (2003-2022)")
    logger.info("This will process ~7,300 files - may take several hours")
    total_processed += process_currents_oscar_files()
    
    # Phase 4: Process remaining CMEMS currents files (2023-2025)
    logger.info("\n🌊 PHASE 4: Processing CMEMS Currents Data (2023-2025)")
    total_processed += process_currents_cmems_files()
    
    # Final summary
    end_time = time.time()
    duration = end_time - start_time
    logger.info("\n" + "=" * 60)
    logger.info("COMPREHENSIVE PROCESSING COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Total files processed: {total_processed}")
    logger.info(f"Total processing time: {duration/60:.1f} minutes")
    logger.info(f"Average time per file: {duration/total_processed:.2f} seconds" if total_processed > 0 else "No files processed")
    
    return total_processed

if __name__ == "__main__":
    processed = main()
    sys.exit(0 if processed >= 0 else 1)