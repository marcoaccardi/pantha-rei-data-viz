#!/usr/bin/env python3
"""
Complete Microplastics Dataset Generation Pipeline

This script runs the complete pipeline to generate a unified microplastics dataset
combining real data (1993-2019) with synthetically generated data (2019-2025).

Usage:
    python scripts/generate_microplastics_dataset.py [options]

Options:
    --data-only         Generate only the unified dataset (no textures)
    --textures-only     Generate only textures (requires existing dataset)
    --resolution LEVEL  Texture resolution: low, medium, high (default: medium)
    --epochs N          GAN training epochs (default: 100)
    --output-dir DIR    Custom output directory
"""

import sys
import os
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Add processors to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'processors'))

from microplastics_unified_processor import MicroplasticsUnifiedProcessor
from microplastics_texture_generator import MicroplasticsTextureGenerator


def setup_logging(log_level: str = 'INFO'):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                f'/Volumes/Backup/panta-rhei-data-map/ocean-data/logs/microplastics_pipeline_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
            )
        ]
    )


def generate_dataset(epochs: int = 100, output_dir: str = None) -> tuple:
    """
    Generate the complete unified microplastics dataset
    
    Args:
        epochs: Number of GAN training epochs
        output_dir: Custom output directory
        
    Returns:
        Tuple of (unified_data, quality_report, processor)
    """
    print("🌊 Microplastics Dataset Generation Pipeline")
    print("=" * 50)
    
    # Initialize processor
    processor_kwargs = {}
    if output_dir:
        processor_kwargs['output_dir'] = output_dir
    
    processor = MicroplasticsUnifiedProcessor(**processor_kwargs)
    
    # Phase 1: Load and analyze data
    print("\n[Phase 1] 📊 Data Loading and Analysis")
    print("-" * 40)
    analysis = processor.load_and_analyze_data()
    print(f"✅ Total records available: {analysis['total_records']:,}")
    print(f"✅ Real data period: {analysis['real_data_available']:,} records available")
    
    # Phase 2: Extract real data
    print("\n[Phase 2] 🔍 Real Data Extraction (1993-2019)")
    print("-" * 40)  
    real_data = processor.extract_real_data()
    print(f"✅ Extracted {len(real_data):,} real data records")
    
    # Phase 3: Train GAN model
    print("\n[Phase 3] 🤖 Enhanced GAN Training")
    print("-" * 40)
    print(f"⏳ Training GAN model with {epochs} epochs...")
    training_metrics = processor.train_enhanced_gan(real_data, epochs=epochs)
    print(f"✅ GAN training completed - Final D_loss: {training_metrics['d_losses'][-1]:.4f}")
    
    # Phase 4: Generate synthetic data
    print("\n[Phase 4] 🎯 Synthetic Data Generation (2019-2025)")
    print("-" * 40)
    print("⏳ Generating synthetic microplastics data...")
    synthetic_data = processor.generate_synthetic_data(n_years=6)
    print(f"✅ Generated {len(synthetic_data):,} synthetic records")
    
    # Phase 5: Create unified dataset
    print("\n[Phase 5] 🔗 Unified Dataset Creation")
    print("-" * 40)
    print("⏳ Combining real and synthetic data...")
    unified_data = processor.create_unified_dataset()
    print(f"✅ Created unified dataset with {len(unified_data):,} total records")
    
    # Phase 6: Quality assessment
    print("\n[Phase 6] 📋 Quality Assessment")
    print("-" * 40)
    quality_report = processor.generate_quality_report()
    print(f"✅ Real data concentration mean: {quality_report['concentration_comparison']['real_mean']:.6f} pieces/m³")
    print(f"✅ Synthetic data concentration mean: {quality_report['concentration_comparison']['synthetic_mean']:.6f} pieces/m³")
    
    # Phase 7: Save to NetCDF
    print("\n[Phase 7] 💾 NetCDF Export")
    print("-" * 40)
    netcdf_path = processor.save_to_netcdf()
    print(f"✅ NetCDF file saved: {os.path.basename(netcdf_path)}")
    
    return unified_data, quality_report, processor


def generate_textures(resolution: str = 'medium', data_path: str = None, output_dir: str = None) -> dict:
    """
    Generate visualization textures from unified dataset
    
    Args:
        resolution: Texture resolution level
        data_path: Path to unified dataset CSV
        output_dir: Custom output directory
        
    Returns:
        Dictionary of generated textures
    """
    print("\n🎨 Microplastics Texture Generation")
    print("=" * 50)
    
    # Initialize generator
    generator_kwargs = {'resolution': resolution}
    if data_path:
        generator_kwargs['data_path'] = data_path
    if output_dir:
        generator_kwargs['output_dir'] = os.path.join(output_dir, 'textures')
    
    generator = MicroplasticsTextureGenerator(**generator_kwargs)
    
    # Phase 1: Load data
    print("\n[Phase 1] 📥 Loading Unified Dataset")
    print("-" * 40)
    data = generator.load_data()
    print(f"✅ Loaded {len(data):,} microplastics records")
    
    # Phase 2: Generate texture series
    print(f"\n[Phase 2] 🖼️  Generating {resolution.title()} Resolution Textures")
    print("-" * 40)
    print("⏳ Generating textures for 1993-2025...")
    all_textures = generator.generate_complete_texture_series(resolution=resolution)
    
    total_textures = sum(len(paths) for paths in all_textures.values())
    print(f"✅ Generated {total_textures:,} texture files")
    
    # Phase 3: Create preview montages
    print("\n[Phase 3] 🖼️  Creating Preview Montages")
    print("-" * 40)
    preview_years = [1993, 2000, 2010, 2019, 2025]
    montages_created = 0
    
    for year in preview_years:
        if year in all_textures:
            try:
                generator.create_preview_montage(year, resolution)
                montages_created += 1
                print(f"✅ Created montage for {year}")
            except Exception as e:
                print(f"⚠️  Warning: Could not create montage for {year}: {e}")
    
    # Phase 4: Create legend
    print("\n[Phase 4] 📖 Creating Concentration Legend")
    print("-" * 40)
    try:
        legend_path = generator.create_concentration_legend()
        print(f"✅ Created concentration legend")
    except Exception as e:
        print(f"⚠️  Warning: Could not create legend: {e}")
    
    return all_textures


def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(
        description='Generate complete microplastics dataset and textures',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--data-only', action='store_true',
                       help='Generate only the unified dataset (no textures)')
    parser.add_argument('--textures-only', action='store_true',
                       help='Generate only textures (requires existing dataset)')
    parser.add_argument('--resolution', choices=['low', 'medium', 'high'], default='medium',
                       help='Texture resolution level (default: medium)')
    parser.add_argument('--epochs', type=int, default=100,
                       help='GAN training epochs (default: 100)')
    parser.add_argument('--output-dir', type=str,
                       help='Custom output directory')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO',
                       help='Logging level (default: INFO)')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    start_time = datetime.now()
    
    try:
        if args.textures_only:
            # Generate only textures
            print("🎨 Running texture-only generation...")
            
            # Check if unified dataset exists
            default_data_path = "/Volumes/Backup/panta-rhei-data-map/ocean-data/processed/unified_coords/microplastics/unified/microplastics_complete_1993_2025.csv"
            
            if not os.path.exists(default_data_path):
                print(f"❌ Error: Unified dataset not found at {default_data_path}")
                print("Please run the complete pipeline first or specify --data-path")
                sys.exit(1)
            
            all_textures = generate_textures(
                resolution=args.resolution,
                data_path=default_data_path,
                output_dir=args.output_dir
            )
            
            total_textures = sum(len(paths) for paths in all_textures.values())
            
        elif args.data_only:
            # Generate only dataset
            print("📊 Running data-only generation...")
            unified_data, quality_report, processor = generate_dataset(
                epochs=args.epochs,
                output_dir=args.output_dir
            )
            
            total_textures = 0
            
        else:
            # Generate complete pipeline
            print("🚀 Running complete pipeline...")
            
            # Generate dataset
            unified_data, quality_report, processor = generate_dataset(
                epochs=args.epochs,
                output_dir=args.output_dir
            )
            
            # Generate textures
            unified_csv_path = os.path.join(
                processor.output_dir, 'unified', 'microplastics_complete_1993_2025.csv'
            )
            
            all_textures = generate_textures(
                resolution=args.resolution,
                data_path=unified_csv_path,
                output_dir=processor.output_dir
            )
            
            total_textures = sum(len(paths) for paths in all_textures.values())
        
        # Success summary
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\n🎉 Pipeline Complete!")
        print("=" * 50)
        print(f"⏱️  Total runtime: {duration}")
        print(f"📁 Output directory: {args.output_dir or 'default'}")
        
        if not args.textures_only:
            print(f"📊 Dataset records: {len(unified_data):,}")
            print(f"   - Real data (1993-2019): {quality_report['data_coverage']['real_records']:,}")
            print(f"   - Synthetic data (2019-2025): {quality_report['data_coverage']['synthetic_records']:,}")
        
        if not args.data_only:
            print(f"🎨 Textures generated: {total_textures:,}")
            print(f"   - Resolution: {args.resolution}")
            print(f"   - Years covered: 1993-2025 (33 years)")
            print(f"   - Monthly frequency: {total_textures // 33:.0f} per year")
        
        print(f"\n✅ All tasks completed successfully!")
        
    except KeyboardInterrupt:
        print(f"\n⏹️  Pipeline interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Pipeline failed with error: {e}")
        logging.exception("Pipeline failed")
        sys.exit(1)


if __name__ == "__main__":
    main()