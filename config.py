#!/usr/bin/env python3
"""
Configuration settings for NOAA Climate Data System.
Centralized configuration management for all system components.
"""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
TEXTURES_DIR = BASE_DIR / "textures"
SRC_DIR = BASE_DIR / "src"

# Texture specifications
TEXTURE_SPECS = {
    'target_width': 7200,
    'target_height': 3600,
    'dpi': 300,
    'format': 'png',
    'aspect_ratio': 2.0,
    'min_width': 1024,
    'min_height': 512,
    'max_file_size_mb': 50
}

# Data source URLs
DATA_SOURCES = {
    'noaa_stations_api': 'https://api.tidesandcurrents.noaa.gov/api/prod/datagetter',
    'erddap_sst_base': 'https://pae-paha.pacioos.hawaii.edu/erddap/griddap',
    'nasa_earth_urls': {
        'world_topo_bathy': 'https://eoimages.gsfc.nasa.gov/images/imagerecords/73000/73909/world.topo.bathy.200412.3x5400x2700.jpg',
    }
}

# Directory paths
PATHS = {
    'base_dir': BASE_DIR,
    'data_dir': DATA_DIR,
    'cache_dir': DATA_DIR / "cache",
    'ocean_cache_dir': DATA_DIR / "ocean_cache",
    'coordinates_data_dir': DATA_DIR / "coordinates_data",
    'textures_dir': TEXTURES_DIR,
    'earth_textures_dir': TEXTURES_DIR / "earth",
    'sst_textures_dir': TEXTURES_DIR / "sst",
    'ocean_datasets_dir': DATA_DIR / "ocean_datasets",
    'biological_data_dir': DATA_DIR / "ocean_datasets" / "biological",
    'currents_data_dir': DATA_DIR / "ocean_datasets" / "currents",
    'web_globe_dir': BASE_DIR / "web-globe"
}

# API configuration
API_CONFIG = {
    'timeout': 120,
    'max_retries': 3,
    'cache_expire_hours': 24,
    'user_agent': 'NOAA-Climate-System/1.0 (Scientific Research)'
}

# Processing configuration
PROCESSING_CONFIG = {
    'temperature_range': (-2, 35),
    'land_color': [128, 128, 128, 255],  # Gray RGBA
    'progress_update_interval': 10
}

# Temperature color mapping (reference style)
TEMPERATURE_COLORS = {
    'very_cold': [173, 216, 230, 255],   # Light blue (polar/ice)
    'cold': [135, 206, 235, 255],        # Sky blue (very cold)
    'cool': [0, 255, 255, 255],          # Cyan (cold)
    'moderate_cool': [124, 252, 0, 255], # Lawn green (cool temperate)
    'moderate': [255, 255, 0, 255],      # Yellow (moderate)
    'warm': [255, 215, 0, 255],          # Gold (warm)
    'hot': [255, 165, 0, 255],           # Orange (hot tropical)
    'very_hot': [255, 69, 0, 255],       # Orange-red (very hot)
    'extreme': [255, 0, 0, 255],         # Red (extremely hot)
    'dangerous': [139, 0, 0, 255]        # Dark red (dangerous heat)
}

# Temperature thresholds for color mapping
TEMPERATURE_THRESHOLDS = [-1, 2, 8, 15, 18, 22, 25, 27, 29, 31]

# System configuration
SYSTEM_CONFIG = {
    'version': '1.0.0',
    'description': 'NOAA Climate Data Globe Texture System',
    'author': 'NOAA Climate Data System',
    'supported_formats': ['PNG', 'JPEG', 'JPG'],
    'react_three_fiber_ready': True,
    'scientific_accuracy': True
}

# Logging configuration
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'log_file': DATA_DIR / "cache" / "system.log"
}

# Create directories if they don't exist
def create_directories():
    """Create all required directories."""
    for path in PATHS.values():
        if isinstance(path, Path):
            path.mkdir(parents=True, exist_ok=True)

# Initialize directories on import
create_directories()