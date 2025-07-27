#!/usr/bin/env python3
"""
Batch texture generation script for all available ocean data.
Processes all NetCDF files in unified_coords and generates PNG textures.
"""

import sys
import os
from pathlib import Path
import logging
import argparse
from typing import Dict, List, Any
import json
from datetime import datetime

# Add backend to Python path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from processors.dataset_texture_generators import (
    SSTTextureGenerator,
    AcidityTextureGenerator, 
    CurrentsTextureGenerator,
    MicroplasticsTextureGenerator
)

class TextureBatchProcessor:
    """Batch processor for generating textures from all ocean datasets."""
    
    def __init__(self, unified_coords_path: str = None, textures_output_path: str = None):
        """
        Initialize batch processor.
        
        Args:
            unified_coords_path: Path to unified_coords directory
            textures_output_path: Path to textures output directory
        """
        self.logger = self._setup_logging()
        
        if unified_coords_path is None:
            self.unified_coords_path = Path("/Volumes/Backup/panta-rhei-data-map/ocean-data/processed/unified_coords")
        else:
            self.unified_coords_path = Path(unified_coords_path)
            
        if textures_output_path is None:
            self.textures_output_path = Path("/Volumes/Backup/panta-rhei-data-map/ocean-data/textures")
        else:
            self.textures_output_path = Path(textures_output_path)
            
        # Initialize generators
        self.generators = {
            'sst': SSTTextureGenerator(self.textures_output_path),
            'acidity': AcidityTextureGenerator(self.textures_output_path),
            'currents': CurrentsTextureGenerator(self.textures_output_path),
            'microplastics': MicroplasticsTextureGenerator(self.textures_output_path)
        }
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('/Volumes/Backup/panta-rhei-data-map/ocean-data/logs/texture_generation.log')
            ]
        )
        return logging.getLogger(__name__)
        
    def find_netcdf_files(self, dataset: str = None) -> Dict[str, List[Path]]:
        """
        Find all NetCDF files in unified_coords directory.
        
        Args:
            dataset: Specific dataset to process (optional)
            
        Returns:
            Dictionary mapping dataset names to lists of NetCDF file paths
        """
        files_by_dataset = {}
        
        datasets_to_process = [dataset] if dataset else self.generators.keys()
        
        for dataset_name in datasets_to_process:
            dataset_path = self.unified_coords_path / dataset_name
            if not dataset_path.exists():
                self.logger.warning(f"Dataset directory not found: {dataset_path}")
                continue
                
            # Find all .nc files recursively
            nc_files = list(dataset_path.rglob("*.nc"))
            
            # Filter out empty files
            valid_files = []
            for nc_file in nc_files:
                try:
                    file_size = nc_file.stat().st_size
                    if file_size > 1000:  # Files larger than 1KB (empty files are ~4KB of metadata)
                        valid_files.append(nc_file)
                    else:
                        self.logger.warning(f"Skipping small/empty file: {nc_file} ({file_size} bytes)")
                except Exception as e:
                    self.logger.warning(f"Error checking file {nc_file}: {e}")
                    
            files_by_dataset[dataset_name] = valid_files
            self.logger.info(f"Found {len(valid_files)} valid files for {dataset_name}")
            
        return files_by_dataset
        
    def check_existing_texture(self, dataset: str, nc_file: Path) -> bool:
        """
        Check if texture already exists and is newer than source file.
        
        Args:
            dataset: Dataset name
            nc_file: Source NetCDF file
            
        Returns:
            True if texture exists and is up to date
        """
        try:
            # Extract date from NetCDF filename
            import re
            date_match = re.search(r'(\d{8})', nc_file.name)
            if not date_match:
                return False
                
            date_str = date_match.group(1)
            year = date_str[:4]
            
            # Check for existing texture
            texture_filename = f"{dataset}_texture_{date_str}_medium.png"
            texture_path = self.textures_output_path / dataset / year / texture_filename
            
            if not texture_path.exists():
                return False
                
            # Check if texture is newer than source file
            texture_mtime = texture_path.stat().st_mtime
            source_mtime = nc_file.stat().st_mtime
            
            return texture_mtime > source_mtime
            
        except Exception as e:
            self.logger.warning(f"Error checking existing texture for {nc_file}: {e}")
            return False
            
    def process_dataset(self, dataset: str, files: List[Path], force_regenerate: bool = False) -> Dict[str, Any]:
        """
        Process all files for a specific dataset.
        
        Args:
            dataset: Dataset name
            files: List of NetCDF files to process
            force_regenerate: Force regeneration even if texture exists
            
        Returns:
            Processing results summary
        """
        self.logger.info(f"Processing {len(files)} files for dataset: {dataset}")
        
        generator = self.generators[dataset]
        results = {
            'dataset': dataset,
            'total_files': len(files),
            'processed': 0,
            'skipped': 0,
            'failed': 0,
            'files_processed': [],
            'files_failed': []
        }
        
        for nc_file in files:
            try:
                # Check if texture already exists
                if not force_regenerate and self.check_existing_texture(dataset, nc_file):
                    self.logger.info(f"Texture already exists for {nc_file.name}, skipping")
                    results['skipped'] += 1
                    continue
                    
                # Process file
                self.logger.info(f"Processing {nc_file}")
                success = generator.process_netcdf_to_texture(nc_file)
                
                if success:
                    results['processed'] += 1
                    results['files_processed'].append(str(nc_file))
                    self.logger.info(f"Successfully processed {nc_file.name}")
                else:
                    results['failed'] += 1
                    results['files_failed'].append(str(nc_file))
                    self.logger.error(f"Failed to process {nc_file.name}")
                    
            except Exception as e:
                results['failed'] += 1
                results['files_failed'].append(str(nc_file))
                self.logger.error(f"Exception processing {nc_file}: {e}")
                
        self.logger.info(f"Dataset {dataset} complete: {results['processed']} processed, "
                        f"{results['skipped']} skipped, {results['failed']} failed")
        
        return results
        
    def generate_summary_report(self, all_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate summary report of texture generation.
        
        Args:
            all_results: List of results from each dataset
            
        Returns:
            Summary report
        """
        summary = {
            'generation_time': datetime.now().isoformat(),
            'total_datasets': len(all_results),
            'overall_stats': {
                'total_files': 0,
                'processed': 0,
                'skipped': 0,
                'failed': 0
            },
            'dataset_results': all_results
        }
        
        for result in all_results:
            summary['overall_stats']['total_files'] += result['total_files']
            summary['overall_stats']['processed'] += result['processed']
            summary['overall_stats']['skipped'] += result['skipped']
            summary['overall_stats']['failed'] += result['failed']
            
        return summary
        
    def run(self, dataset: str = None, force_regenerate: bool = False) -> Dict[str, Any]:
        """
        Run batch texture generation.
        
        Args:
            dataset: Specific dataset to process (optional)
            force_regenerate: Force regeneration even if texture exists
            
        Returns:
            Processing summary
        """
        self.logger.info("Starting batch texture generation")
        self.logger.info(f"Source directory: {self.unified_coords_path}")
        self.logger.info(f"Output directory: {self.textures_output_path}")
        
        # Find all NetCDF files
        files_by_dataset = self.find_netcdf_files(dataset)
        
        if not any(files_by_dataset.values()):
            self.logger.warning("No valid NetCDF files found to process")
            return {'error': 'No files found'}
            
        # Process each dataset
        all_results = []
        for dataset_name, files in files_by_dataset.items():
            if files:  # Only process datasets with files
                results = self.process_dataset(dataset_name, files, force_regenerate)
                all_results.append(results)
                
        # Generate summary report
        summary = self.generate_summary_report(all_results)
        
        # Save summary report
        report_path = self.textures_output_path / "generation_summary.json"
        try:
            with open(report_path, 'w') as f:
                json.dump(summary, f, indent=2)
            self.logger.info(f"Summary report saved: {report_path}")
        except Exception as e:
            self.logger.error(f"Failed to save summary report: {e}")
            
        self.logger.info("Batch texture generation complete")
        return summary

def main():
    """Main entry point for texture generation script."""
    parser = argparse.ArgumentParser(description="Generate ultra-high resolution textures from ocean data")
    parser.add_argument('--dataset', '-d', type=str, 
                       choices=['sst', 'acidity', 'currents', 'microplastics'],
                       help='Process specific dataset only')
    parser.add_argument('--force', '-f', action='store_true',
                       help='Force regeneration even if texture exists')
    parser.add_argument('--unified-coords-path', type=str,
                       help='Path to unified_coords directory')
    parser.add_argument('--output-path', type=str,
                       help='Path to textures output directory')
    parser.add_argument('--quality', '-q', type=str, 
                       choices=['standard', 'ultra'], default='ultra',
                       help='Texture quality level (default: ultra for maximum detail)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging for debugging')
    
    args = parser.parse_args()
    
    # Set up enhanced logging if verbose mode
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
        print("Verbose logging enabled - detailed processing information will be shown")
    
    # Initialize processor
    processor = TextureBatchProcessor(
        unified_coords_path=args.unified_coords_path,
        textures_output_path=args.output_path
    )
    
    # Display configuration info
    print(f"Texture Generation Configuration:")
    print(f"  Quality Level: {args.quality} ({'Ultra-high resolution (2041×4320)' if args.quality == 'ultra' else 'Standard resolution'})")
    print(f"  Force Regeneration: {args.force}")
    print(f"  Dataset Filter: {args.dataset or 'All datasets'}")
    print(f"  Enhanced Features: Cubic interpolation, coordinate validation, hybrid acidity support")
    print()
    
    # Run processing
    try:
        summary = processor.run(
            dataset=args.dataset,
            force_regenerate=args.force
        )
        
        # Print summary
        if 'error' not in summary:
            stats = summary['overall_stats']
            print(f"\nTexture Generation Summary:")
            print(f"Total files processed: {stats['total_files']}")
            print(f"Successfully generated: {stats['processed']}")
            print(f"Skipped (already exist): {stats['skipped']}")
            print(f"Failed: {stats['failed']}")
            
            if stats['failed'] > 0:
                print(f"\nFailed files:")
                for result in summary['dataset_results']:
                    for failed_file in result['files_failed']:
                        print(f"  {failed_file}")
        else:
            print(f"Error: {summary['error']}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nTexture generation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error during texture generation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()