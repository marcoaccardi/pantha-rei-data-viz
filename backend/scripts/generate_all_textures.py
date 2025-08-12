#!/usr/bin/env python3
"""
Batch texture generation script for all available ocean data.
Enhanced to use high-quality ERDDAP textures for SST and local processing for other datasets.
"""

import sys
import os
from pathlib import Path
import logging
import argparse
from typing import Dict, List, Any
import json
from datetime import datetime, date, timedelta

# Add backend to Python path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from processors.dataset_texture_generators import (
    MicroplasticsTextureGenerator
)

# Import new high-quality SST texture downloader
from downloaders.sst_erddap_texture_downloader import SSTERDDAPTextureDownloader

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
            self.unified_coords_path = Path("../ocean-data/processed/unified_coords")
        else:
            self.unified_coords_path = Path(unified_coords_path)
            
        if textures_output_path is None:
            self.textures_output_path = Path("../ocean-data/textures")
        else:
            self.textures_output_path = Path(textures_output_path)
            
        # Initialize generators (SST now uses ERDDAP downloader exclusively)
        # Note: Acidity and Currents texture generators removed due to low data quality
        self.generators = {
            'microplastics': MicroplasticsTextureGenerator(self.textures_output_path)
        }
        
        # Initialize high-quality ERDDAP SST texture downloader
        self.sst_erddap_downloader = SSTERDDAPTextureDownloader(
            Path("../ocean-data/textures/sst")
        )
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('../ocean-data/logs/texture_generation.log')
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
        Enhanced to use high-quality ERDDAP textures for SST.
        
        Args:
            dataset: Dataset name
            files: List of NetCDF files to process
            force_regenerate: Force regeneration even if texture exists
            
        Returns:
            Processing results summary
        """
        self.logger.info(f"Processing {len(files)} files for dataset: {dataset}")
        
        # Special handling for SST - use high-quality ERDDAP textures
        if dataset == 'sst':
            return self._process_sst_with_erddap(files, force_regenerate)
        
        # Standard processing for other datasets
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
        
    def _process_sst_with_erddap(self, files: List[Path], force_regenerate: bool = False) -> Dict[str, Any]:
        """
        Process SST dataset using high-quality ERDDAP textures.
        Extracts dates from NetCDF files and downloads corresponding ERDDAP textures.
        
        Args:
            files: List of SST NetCDF files
            force_regenerate: Force download even if texture exists
            
        Returns:
            Processing results summary
        """
        self.logger.info(f"Using high-quality ERDDAP textures for {len(files)} SST files")
        
        results = {
            'dataset': 'sst',
            'method': 'erddap_transparentpng',
            'total_files': len(files),
            'processed': 0,
            'skipped': 0,
            'failed': 0,
            'files_processed': [],
            'files_failed': []
        }
        
        # Extract dates from NetCDF filenames and download textures
        dates_to_download = set()
        
        for nc_file in files:
            try:
                # Extract date from filename (various formats)
                import re
                date_match = re.search(r'(\d{8})', nc_file.name)
                if date_match:
                    date_str = date_match.group(1)
                    target_date = datetime.strptime(date_str, '%Y%m%d').date()
                    dates_to_download.add(target_date)
                else:
                    self.logger.warning(f"Could not extract date from {nc_file.name}")
                    results['failed'] += 1
                    results['files_failed'].append(str(nc_file))
            except Exception as e:
                self.logger.error(f"Error processing filename {nc_file.name}: {e}")
                results['failed'] += 1
                results['files_failed'].append(str(nc_file))
        
        # Download high-quality textures for all extracted dates
        self.logger.info(f"Downloading ERDDAP textures for {len(dates_to_download)} unique dates")
        
        for target_date in sorted(dates_to_download):
            try:
                # Check if texture already exists
                texture_filename = f"SST_{target_date.strftime('%Y%m%d')}.png"
                year_dir = self.sst_erddap_downloader.output_base_path / str(target_date.year)
                texture_path = year_dir / texture_filename
                
                if texture_path.exists() and not force_regenerate:
                    self.logger.info(f"ERDDAP texture already exists for {target_date}, skipping")
                    results['skipped'] += 1
                    continue
                
                # Download high-quality texture
                success = self.sst_erddap_downloader.download_texture_for_date(target_date)
                
                if success:
                    results['processed'] += 1
                    results['files_processed'].append(f"ERDDAP_SST_{target_date}")
                    self.logger.info(f"Successfully downloaded ERDDAP texture for {target_date}")
                else:
                    results['failed'] += 1
                    results['files_failed'].append(f"ERDDAP_SST_{target_date}")
                    self.logger.error(f"Failed to download ERDDAP texture for {target_date}")
                    
            except Exception as e:
                results['failed'] += 1
                results['files_failed'].append(f"ERDDAP_SST_{target_date}")
                self.logger.error(f"Exception downloading ERDDAP texture for {target_date}: {e}")
        
        self.logger.info(f"SST ERDDAP processing complete: {results['processed']} downloaded, "
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
                       choices=['microplastics'],
                       help='Process specific dataset only (SST uses ERDDAP textures directly, acidity/currents removed due to low quality)')
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