#!/usr/bin/env python3
"""
Coordinate validation utilities for ocean data queries.
Ensures coordinates are valid ocean points and within API bounds.
"""

import json
from pathlib import Path
from typing import Tuple, Dict, Any, List, Optional
import logging

class CoordinateValidator:
    """Validator for ocean coordinates with web-globe compatibility."""
    
    def __init__(self, ocean_mask_file: Optional[Path] = None):
        """
        Initialize coordinate validator.
        
        Args:
            ocean_mask_file: Path to ocean mask data file (optional)
        """
        self.logger = logging.getLogger(__name__)
        self.ocean_mask_file = ocean_mask_file
        
        # Define coordinate precision for web-globe compatibility
        self.COORDINATE_PRECISION = 4  # decimal places
        
        # Global ocean bounds
        self.GLOBAL_BOUNDS = {
            'lat_min': -90.0,
            'lat_max': 90.0,
            'lon_min': -180.0,
            'lon_max': 180.0
        }
        
        # Known land coordinates (simplified for demonstration)
        # In production, this would load from a proper ocean mask file
        self.known_land_points = {
            (0.0, 0.0),  # Gulf of Guinea (actually ocean, but for demo)
        }
        
        # API-specific bounds
        self.api_bounds = {
            'copernicus': self.GLOBAL_BOUNDS,
            'noaa_cops': {
                'lat_min': 24.0,  # Florida Keys minimum
                'lat_max': 72.0,  # Alaska maximum
                'lon_min': -180.0,  # Aleutian Islands
                'lon_max': -65.0   # US East Coast
            },
            'pangaea': self.GLOBAL_BOUNDS  # Research data can be anywhere
        }
        
        self.logger.info("Coordinate validator initialized")
    
    def validate_coordinates(self, lat: float, lon: float) -> bool:
        """
        Validate if coordinates are within valid range.
        
        Args:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees
            
        Returns:
            True if coordinates are valid
        """
        try:
            # Check if coordinates are numbers
            lat = float(lat)
            lon = float(lon)
            
            # Check global bounds
            if not (self.GLOBAL_BOUNDS['lat_min'] <= lat <= self.GLOBAL_BOUNDS['lat_max']):
                self.logger.warning(f"Latitude {lat} out of bounds")
                return False
                
            if not (self.GLOBAL_BOUNDS['lon_min'] <= lon <= self.GLOBAL_BOUNDS['lon_max']):
                self.logger.warning(f"Longitude {lon} out of bounds")
                return False
                
            return True
            
        except (TypeError, ValueError):
            self.logger.error(f"Invalid coordinate types: lat={lat}, lon={lon}")
            return False
    
    def validate_ocean_point(self, lat: float, lon: float) -> bool:
        """
        Validate if coordinates represent an ocean point.
        
        Args:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees
            
        Returns:
            True if coordinates are in the ocean
        """
        # First validate basic coordinates
        if not self.validate_coordinates(lat, lon):
            return False
        
        # Round to precision
        lat_rounded = round(lat, self.COORDINATE_PRECISION)
        lon_rounded = round(lon, self.COORDINATE_PRECISION)
        
        # Check against known land points (simplified)
        if (lat_rounded, lon_rounded) in self.known_land_points:
            self.logger.info(f"Coordinates {lat}, {lon} identified as land")
            return False
        
        # In a real implementation, this would check against an ocean mask
        # For now, we'll use some basic heuristics
        
        # Exclude major land masses (very simplified)
        land_regions = [
            # Continental interiors
            {'lat_min': 35, 'lat_max': 50, 'lon_min': -100, 'lon_max': -90},  # Central USA
            {'lat_min': 45, 'lat_max': 60, 'lon_min': 20, 'lon_max': 40},     # Eastern Europe
            {'lat_min': -30, 'lat_max': -20, 'lon_min': 130, 'lon_max': 140}, # Central Australia
            {'lat_min': 20, 'lat_max': 30, 'lon_min': 0, 'lon_max': 10},      # Sahara
        ]
        
        for region in land_regions:
            if (region['lat_min'] <= lat <= region['lat_max'] and 
                region['lon_min'] <= lon <= region['lon_max']):
                self.logger.info(f"Coordinates {lat}, {lon} in known land region")
                return False
        
        # If we get here, assume it's ocean (in production, use proper ocean mask)
        return True
    
    def validate_for_api(self, lat: float, lon: float, api_name: str) -> bool:
        """
        Validate if coordinates are within bounds for specific API.
        
        Args:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees
            api_name: Name of the API to check bounds for
            
        Returns:
            True if coordinates are valid for the API
        """
        if api_name not in self.api_bounds:
            self.logger.warning(f"Unknown API: {api_name}")
            return False
        
        bounds = self.api_bounds[api_name]
        
        if not (bounds['lat_min'] <= lat <= bounds['lat_max']):
            self.logger.info(f"Latitude {lat} out of bounds for {api_name}")
            return False
            
        if not (bounds['lon_min'] <= lon <= bounds['lon_max']):
            self.logger.info(f"Longitude {lon} out of bounds for {api_name}")
            return False
            
        return True
    
    def normalize_coordinates(self, lat: float, lon: float) -> Tuple[float, float]:
        """
        Normalize coordinates to standard format with proper precision.
        
        Args:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees
            
        Returns:
            Tuple of (normalized_lat, normalized_lon)
        """
        # Ensure longitude is in -180 to 180 range
        while lon > 180:
            lon -= 360
        while lon < -180:
            lon += 360
        
        # Round to specified precision
        lat = round(lat, self.COORDINATE_PRECISION)
        lon = round(lon, self.COORDINATE_PRECISION)
        
        return lat, lon
    
    def get_region_name(self, lat: float, lon: float) -> str:
        """
        Get descriptive region name for coordinates.
        
        Args:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees
            
        Returns:
            Region name string
        """
        # Define major ocean regions
        if lat > 60:
            if lon > -180 and lon < -100:
                return "Arctic Ocean (Pacific)"
            elif lon > -100 and lon < 0:
                return "Arctic Ocean (Atlantic)"
            else:
                return "Arctic Ocean"
        elif lat < -60:
            return "Southern Ocean"
        elif -180 <= lon <= -100:
            if 0 <= lat <= 60:
                return "North Pacific Ocean"
            else:
                return "South Pacific Ocean"
        elif -100 <= lon <= -20:
            if 0 <= lat <= 60:
                return "North Atlantic Ocean"
            else:
                return "South Atlantic Ocean"
        elif -20 <= lon <= 120:
            if lat > 30:
                return "Mediterranean/European Waters"
            else:
                return "Indian Ocean"
        else:
            if lat > 0:
                return "Western Pacific Ocean"
            else:
                return "Indo-Pacific Region"
    
    def validate_coordinate_batch(self, coordinates: List[Dict[str, float]]) -> List[Dict[str, Any]]:
        """
        Validate a batch of coordinates.
        
        Args:
            coordinates: List of coordinate dictionaries with 'lat' and 'lon' keys
            
        Returns:
            List of validation results
        """
        results = []
        
        for coord in coordinates:
            lat = coord.get('lat')
            lon = coord.get('lon')
            
            if lat is None or lon is None:
                results.append({
                    'original': coord,
                    'valid': False,
                    'error': 'Missing lat or lon'
                })
                continue
            
            # Normalize coordinates
            lat_norm, lon_norm = self.normalize_coordinates(lat, lon)
            
            # Validate
            is_valid = self.validate_coordinates(lat_norm, lon_norm)
            is_ocean = self.validate_ocean_point(lat_norm, lon_norm) if is_valid else False
            
            results.append({
                'original': coord,
                'normalized': {'lat': lat_norm, 'lon': lon_norm},
                'valid': is_valid,
                'is_ocean': is_ocean,
                'region': self.get_region_name(lat_norm, lon_norm) if is_valid else None,
                'apis_available': [
                    api for api in self.api_bounds.keys()
                    if self.validate_for_api(lat_norm, lon_norm, api)
                ] if is_valid else []
            })
        
        return results
    
    def find_nearest_ocean_point(self, lat: float, lon: float, search_radius: float = 1.0) -> Optional[Tuple[float, float]]:
        """
        Find nearest ocean point to given coordinates.
        
        Args:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees
            search_radius: Search radius in degrees
            
        Returns:
            Tuple of (ocean_lat, ocean_lon) or None if not found
        """
        # This is a simplified implementation
        # In production, this would use proper ocean mask data
        
        # Try points in a grid around the coordinate
        step = 0.1
        for dlat in range(int(-search_radius/step), int(search_radius/step) + 1):
            for dlon in range(int(-search_radius/step), int(search_radius/step) + 1):
                test_lat = lat + dlat * step
                test_lon = lon + dlon * step
                
                if self.validate_ocean_point(test_lat, test_lon):
                    return self.normalize_coordinates(test_lat, test_lon)
        
        return None


def main():
    """Test coordinate validator."""
    validator = CoordinateValidator()
    
    # Test coordinates
    test_coords = [
        {'lat': 40.0, 'lon': -70.0, 'name': 'North Atlantic (Gulf Stream)'},
        {'lat': -16.3, 'lon': 145.8, 'name': 'Great Barrier Reef'},
        {'lat': 40.0, 'lon': -95.0, 'name': 'Central USA (Land)'},
        {'lat': 24.7, 'lon': -80.9, 'name': 'Florida Keys'},
        {'lat': 71.0, 'lon': -8.0, 'name': 'Norwegian Sea'},
    ]
    
    print("🌊 COORDINATE VALIDATOR TEST")
    print("=" * 50)
    
    for coord in test_coords:
        lat, lon = coord['lat'], coord['lon']
        print(f"\n📍 Testing: {coord['name']} ({lat}, {lon})")
        
        # Basic validation
        valid = validator.validate_coordinates(lat, lon)
        print(f"  Valid coordinates: {'✅' if valid else '❌'}")
        
        # Ocean validation
        is_ocean = validator.validate_ocean_point(lat, lon)
        print(f"  Ocean point: {'✅' if is_ocean else '❌'}")
        
        # Region
        region = validator.get_region_name(lat, lon)
        print(f"  Region: {region}")
        
        # API availability
        for api in ['copernicus', 'noaa_cops', 'pangaea']:
            api_valid = validator.validate_for_api(lat, lon, api)
            print(f"  {api}: {'✅ Available' if api_valid else '❌ Not available'}")

if __name__ == "__main__":
    main()