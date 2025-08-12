"""
Microplastics Texture Generator

This module creates visualization textures from microplastics data for globe rendering.
Integrates with the existing texture generation system.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as colors
from matplotlib.patches import Rectangle
from PIL import Image, ImageDraw, ImageFilter
import os
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# Import existing texture generator components
try:
    from .texture_generator import TextureGenerator
except ImportError:
    from texture_generator import TextureGenerator


class MicroplasticsTextureGenerator:
    """
    Generates texture maps from microplastics data for globe visualization
    """
    
    def __init__(self, 
                 data_path: str = None,
                 output_dir: str = None,
                 resolution: Tuple[int, int] = (2048, 1024)):
        """
        Initialize the microplastics texture generator
        
        Args:
            data_path: Path to unified microplastics CSV data
            output_dir: Output directory for textures
            resolution: Texture resolution (width, height)
        """
        self.data_path = data_path or "../ocean-data/processed/unified_coords/microplastics/unified/microplastics_complete_1993_2025.csv"
        self.output_dir = output_dir or "../ocean-data/textures/microplastics"
        self.resolution = resolution
        
        # Data storage
        self.data = None
        
        # Color mapping
        self.colormap = self._create_microplastics_colormap()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Create output directories
        self._setup_directories()
    
    def _setup_directories(self):
        """Create necessary output directories"""
        base_dirs = [self.output_dir]
        
        # Create year directories for organization
        for year in range(1993, 2026):
            base_dirs.append(os.path.join(self.output_dir, str(year)))
        
        for directory in base_dirs:
            Path(directory).mkdir(parents=True, exist_ok=True)
        
        self.logger.info("Created microplastics texture directory structure")
    
    def _create_microplastics_colormap(self):
        """Create custom colormap for microplastics visualization"""
        # Define colors for different concentration levels
        colors_list = [
            (0.0, 0.0, 0.3, 0.0),      # Very low: transparent blue
            (0.0, 0.3, 0.7, 0.3),      # Low: light blue
            (0.2, 0.6, 0.8, 0.5),      # Medium: cyan
            (0.8, 0.8, 0.2, 0.7),      # High: yellow
            (1.0, 0.4, 0.0, 0.9),      # Very high: orange-red
            (1.0, 0.0, 0.0, 1.0),      # Extreme: red
        ]
        
        # Create custom colormap
        n_colors = len(colors_list)
        colors_array = np.array(colors_list)
        
        # Create segmented colormap
        colormap = colors.LinearSegmentedColormap.from_list(
            'microplastics', colors_array, N=256
        )
        
        return colormap
    
    def load_data(self) -> pd.DataFrame:
        """
        Load unified microplastics data
        
        Returns:
            Loaded DataFrame
        """
        self.logger.info(f"Loading microplastics data from {self.data_path}")
        
        self.data = pd.read_csv(self.data_path)
        
        # Parse dates if needed
        if 'parsed_date' not in self.data.columns:
            self.data['parsed_date'] = pd.to_datetime(self.data['Date (MM-DD-YYYY)'], errors='coerce')
        
        # Ensure we have required columns
        required_columns = ['Latitude (degree)', 'Longitude(degree)', 'Microplastics measurement', 'year', 'month']
        missing_columns = [col for col in required_columns if col not in self.data.columns]
        
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        self.logger.info(f"Loaded {len(self.data)} microplastics records")
        
        return self.data
    
    def create_monthly_texture(self, year: int, month: int, resolution: str = 'medium') -> str:
        """
        Create texture for a specific month
        
        Args:
            year: Year to generate
            month: Month to generate (1-12)
            resolution: Texture resolution ('low', 'medium', 'high')
            
        Returns:
            Path to generated texture file
        """
        if self.data is None:
            self.load_data()
        
        self.logger.info(f"Generating microplastics texture for {year}-{month:02d}")
        
        # Filter data for the specific month
        month_data = self.data[
            (self.data['year'] == year) & 
            (self.data['month'] == month)
        ].copy()
        
        if len(month_data) == 0:
            self.logger.warning(f"No data available for {year}-{month:02d}, creating empty texture")
            return self._create_empty_texture(year, month, resolution)
        
        # Set resolution based on parameter
        res_map = {
            'low': (512, 256),
            'medium': (1024, 512), 
            'high': (2048, 1024)
        }
        width, height = res_map.get(resolution, (1024, 512))
        
        # Create concentration grid
        concentration_grid = self._create_concentration_grid(month_data, width, height)
        
        # Apply smoothing for better visualization
        concentration_grid = self._apply_smoothing(concentration_grid)
        
        # Create texture image
        texture_image = self._grid_to_image(concentration_grid, width, height)
        
        # Save texture
        filename = f"microplastics_texture_{year}{month:02d}_{resolution}.png"
        output_path = os.path.join(self.output_dir, str(year), filename)
        
        texture_image.save(output_path, 'PNG')
        
        self.logger.info(f"Saved texture: {output_path}")
        
        return output_path
    
    def _create_concentration_grid(self, data: pd.DataFrame, width: int, height: int) -> np.ndarray:
        """
        Create concentration grid from point data
        
        Args:
            data: DataFrame with microplastics data
            width: Grid width
            height: Grid height
            
        Returns:
            2D concentration grid
        """
        # Initialize grid
        grid = np.zeros((height, width))
        counts = np.zeros((height, width))
        
        # Convert coordinates to pixel indices
        lons = data['Longitude(degree)'].values
        lats = data['Latitude (degree)'].values
        concentrations = data['Microplastics measurement'].values
        
        # Normalize coordinates to grid indices
        lon_indices = ((lons + 180) / 360 * width).astype(int)
        lat_indices = ((90 - lats) / 180 * height).astype(int)
        
        # Clip to valid ranges
        lon_indices = np.clip(lon_indices, 0, width - 1)
        lat_indices = np.clip(lat_indices, 0, height - 1)
        
        # Accumulate concentrations
        for i in range(len(data)):
            lat_idx, lon_idx = lat_indices[i], lon_indices[i]
            concentration = concentrations[i]
            
            # Use log scale for better visualization
            log_concentration = np.log1p(max(0, concentration))
            
            grid[lat_idx, lon_idx] += log_concentration
            counts[lat_idx, lon_idx] += 1
        
        # Average concentrations where we have multiple points
        mask = counts > 0
        grid[mask] = grid[mask] / counts[mask]
        
        return grid
    
    def _apply_smoothing(self, grid: np.ndarray, sigma: float = 1.0) -> np.ndarray:
        """
        Apply Gaussian smoothing to concentration grid
        
        Args:
            grid: Input concentration grid
            sigma: Smoothing parameter
            
        Returns:
            Smoothed grid
        """
        from scipy import ndimage
        
        # Apply Gaussian filter
        smoothed = ndimage.gaussian_filter(grid, sigma=sigma)
        
        return smoothed
    
    def _grid_to_image(self, grid: np.ndarray, width: int, height: int) -> Image.Image:
        """
        Convert concentration grid to image
        
        Args:
            grid: Concentration grid
            width: Image width
            height: Image height
            
        Returns:
            PIL Image
        """
        # Normalize grid values
        if grid.max() > 0:
            normalized_grid = grid / grid.max()
        else:
            normalized_grid = grid
        
        # Apply colormap
        colored_grid = self.colormap(normalized_grid)
        
        # Convert to 8-bit RGBA
        rgba_grid = (colored_grid * 255).astype(np.uint8)
        
        # Create PIL image
        image = Image.fromarray(rgba_grid, 'RGBA')
        
        # Apply additional post-processing
        image = self._post_process_image(image)
        
        return image
    
    def _post_process_image(self, image: Image.Image) -> Image.Image:
        """
        Apply post-processing effects to texture
        
        Args:
            image: Input image
            
        Returns:
            Post-processed image
        """
        # Convert to RGBA if not already
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        # Apply slight blur for better blending
        image = image.filter(ImageFilter.GaussianBlur(radius=0.5))
        
        # Enhance contrast slightly
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.2)
        
        return image
    
    def _create_empty_texture(self, year: int, month: int, resolution: str) -> str:
        """
        Create empty/transparent texture for months with no data
        
        Args:
            year: Year
            month: Month
            resolution: Resolution level
            
        Returns:
            Path to created texture
        """
        res_map = {
            'low': (512, 256),
            'medium': (1024, 512), 
            'high': (2048, 1024)
        }
        width, height = res_map.get(resolution, (1024, 512))
        
        # Create transparent image
        image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        
        # Save
        filename = f"microplastics_texture_{year}{month:02d}_{resolution}.png"
        output_path = os.path.join(self.output_dir, str(year), filename)
        
        image.save(output_path, 'PNG')
        
        return output_path
    
    def generate_annual_textures(self, year: int, resolution: str = 'medium') -> List[str]:
        """
        Generate textures for all months of a year
        
        Args:
            year: Year to generate
            resolution: Texture resolution
            
        Returns:
            List of generated texture paths
        """
        self.logger.info(f"Generating annual textures for {year}")
        
        texture_paths = []
        
        for month in range(1, 13):
            try:
                texture_path = self.create_monthly_texture(year, month, resolution)
                texture_paths.append(texture_path)
            except Exception as e:
                self.logger.error(f"Error generating texture for {year}-{month:02d}: {e}")
                # Create empty texture as fallback
                texture_path = self._create_empty_texture(year, month, resolution)
                texture_paths.append(texture_path)
        
        self.logger.info(f"Generated {len(texture_paths)} textures for {year}")
        
        return texture_paths
    
    def generate_complete_texture_series(self, resolution: str = 'medium') -> Dict[int, List[str]]:
        """
        Generate complete texture series for all available years
        
        Args:
            resolution: Texture resolution
            
        Returns:
            Dictionary mapping years to texture paths
        """
        if self.data is None:
            self.load_data()
        
        self.logger.info("Generating complete microplastics texture series (1993-2025)")
        
        # Get available years
        available_years = sorted(self.data['year'].unique())
        
        all_textures = {}
        
        for year in range(1993, 2026):  # Generate for full range regardless of data availability
            year_textures = self.generate_annual_textures(year, resolution)
            all_textures[year] = year_textures
        
        # Generate metadata
        self._generate_texture_metadata(all_textures, resolution)
        
        self.logger.info(f"Generated complete texture series for {len(all_textures)} years")
        
        return all_textures
    
    def _generate_texture_metadata(self, texture_dict: Dict[int, List[str]], resolution: str):
        """
        Generate metadata file for texture series
        
        Args:
            texture_dict: Dictionary of year -> texture paths
            resolution: Resolution used
        """
        metadata = {
            'dataset': 'microplastics',
            'resolution': resolution,
            'temporal_coverage': '1993-2025',
            'total_textures': sum(len(paths) for paths in texture_dict.values()),
            'generation_date': datetime.now().isoformat(),
            'colormap': 'custom_microplastics',
            'data_source': 'unified_real_synthetic',
            'years': {}
        }
        
        for year, texture_paths in texture_dict.items():
            metadata['years'][str(year)] = {
                'texture_count': len(texture_paths),
                'textures': [os.path.basename(path) for path in texture_paths]
            }
        
        # Save metadata
        metadata_path = os.path.join(self.output_dir, f'microplastics_textures_metadata_{resolution}.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        self.logger.info(f"Generated texture metadata: {metadata_path}")
    
    def create_preview_montage(self, year: int, resolution: str = 'medium') -> str:
        """
        Create a montage preview of all months for a year
        
        Args:
            year: Year to create montage for
            resolution: Resolution to use
            
        Returns:
            Path to montage image
        """
        self.logger.info(f"Creating preview montage for {year}")
        
        # Load monthly textures
        monthly_images = []
        for month in range(1, 13):
            filename = f"microplastics_texture_{year}{month:02d}_{resolution}.png"
            texture_path = os.path.join(self.output_dir, str(year), filename)
            
            try:
                img = Image.open(texture_path)
                # Resize for montage
                img = img.resize((256, 128), Image.Resampling.LANCZOS)
                monthly_images.append(img)
            except FileNotFoundError:
                # Create placeholder
                img = Image.new('RGBA', (256, 128), (0, 0, 0, 0))
                monthly_images.append(img)
        
        # Create montage (4x3 grid)
        montage_width = 4 * 256
        montage_height = 3 * 128
        montage = Image.new('RGBA', (montage_width, montage_height), (0, 0, 0, 0))
        
        for i, img in enumerate(monthly_images):
            row = i // 4
            col = i % 4
            x = col * 256
            y = row * 128
            montage.paste(img, (x, y))
        
        # Add month labels
        draw = ImageDraw.Draw(montage)
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        for i, month_name in enumerate(months):
            row = i // 4
            col = i % 4
            x = col * 256 + 10
            y = row * 128 + 10
            draw.text((x, y), month_name, fill=(255, 255, 255, 255))
        
        # Save montage
        montage_path = os.path.join(self.output_dir, f'microplastics_montage_{year}_{resolution}.png')
        montage.save(montage_path, 'PNG')
        
        self.logger.info(f"Created montage: {montage_path}")
        
        return montage_path
    
    def create_concentration_legend(self) -> str:
        """
        Create a legend showing concentration levels and colors
        
        Returns:
            Path to legend image
        """
        self.logger.info("Creating concentration legend")
        
        # Create legend image
        legend_width, legend_height = 400, 200
        legend = Image.new('RGBA', (legend_width, legend_height), (255, 255, 255, 255))
        draw = ImageDraw.Draw(legend)
        
        # Define concentration levels
        levels = [
            (0, 'Very Low\n(0 pieces/m³)'),
            (0.0005, 'Low\n(0.0005 pieces/m³)'),
            (0.005, 'Medium\n(0.005 pieces/m³)'),
            (1.0, 'High\n(1 pieces/m³)'),
            (100.0, 'Very High\n(100+ pieces/m³)')
        ]
        
        # Draw color bar
        bar_width = 300
        bar_height = 30
        bar_x = 50
        bar_y = 50
        
        for i in range(bar_width):
            # Get color from colormap
            value = i / bar_width
            color = self.colormap(value)
            color_rgba = tuple(int(c * 255) for c in color)
            
            draw.line([(bar_x + i, bar_y), (bar_x + i, bar_y + bar_height)], fill=color_rgba)
        
        # Add labels
        draw.text((bar_x, bar_y - 20), 'Microplastics Concentration', fill=(0, 0, 0, 255))
        
        for i, (_, label) in enumerate(levels):
            x = bar_x + (i * bar_width // (len(levels) - 1))
            draw.text((x, bar_y + bar_height + 10), label, fill=(0, 0, 0, 255))
        
        # Save legend
        legend_path = os.path.join(self.output_dir, 'microplastics_concentration_legend.png')
        legend.save(legend_path, 'PNG')
        
        self.logger.info(f"Created legend: {legend_path}")
        
        return legend_path


def main():
    """
    Main function to generate microplastics textures
    """
    print("Microplastics Texture Generator")
    print("=" * 50)
    
    # Initialize generator
    generator = MicroplasticsTextureGenerator()
    
    try:
        # Load data
        print("\n[Phase 1] Loading Data")
        print("-" * 30)
        data = generator.load_data()
        print(f"Loaded {len(data):,} microplastics records")
        
        # Generate complete texture series
        print("\n[Phase 2] Generating Texture Series")
        print("-" * 30)
        all_textures = generator.generate_complete_texture_series(resolution='medium')
        
        total_textures = sum(len(paths) for paths in all_textures.values())
        print(f"Generated {total_textures:,} texture files")
        
        # Create preview montages for key years
        print("\n[Phase 3] Creating Preview Montages")
        print("-" * 30)
        preview_years = [1993, 2000, 2010, 2019, 2025]
        for year in preview_years:
            if year in all_textures:
                montage_path = generator.create_preview_montage(year)
                print(f"Created montage for {year}")
        
        # Create concentration legend
        print("\n[Phase 4] Creating Legend")
        print("-" * 30)
        legend_path = generator.create_concentration_legend()
        print(f"Created concentration legend")
        
        print(f"\n🎉 Texture Generation Complete!")
        print(f"📁 Output directory: {generator.output_dir}")
        print(f"🎨 Total textures: {total_textures:,}")
        print(f"📅 Years covered: 1993-2025 (33 years)")
        print(f"🗓️  Monthly resolution: 12 textures per year")
        
        return all_textures
        
    except Exception as e:
        print(f"❌ Error during texture generation: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()