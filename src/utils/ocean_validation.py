#!/usr/bin/env python3
"""
Ocean Coordinate Validation Utilities
Validates coordinates to ensure they are over ocean rather than land.
"""

from typing import Tuple, Dict, Optional
import math

class OceanValidator:
    """Validates if coordinates are over ocean areas."""
    
    def __init__(self):
        """Initialize ocean validator with basic land/ocean boundaries."""
        # Major landmass boundaries (simplified)
        self.major_landmasses = [
            # North America
            {"name": "North America", "lat_range": (25, 70), "lon_range": (-165, -50)},
            # South America  
            {"name": "South America", "lat_range": (-55, 12), "lon_range": (-80, -35)},
            # Europe
            {"name": "Europe", "lat_range": (35, 70), "lon_range": (-10, 45)},
            # Africa
            {"name": "Africa", "lat_range": (-35, 37), "lon_range": (-20, 50)},
            # Asia
            {"name": "Asia", "lat_range": (5, 75), "lon_range": (25, 180)},
            # Australia
            {"name": "Australia", "lat_range": (-45, -10), "lon_range": (110, 155)},
            # Antarctica (main landmass)
            {"name": "Antarctica", "lat_range": (-90, -60), "lon_range": (-180, 180)},
        ]
        
        # Known deep ocean regions (safe zones)
        self.deep_ocean_zones = [
            {"name": "North Atlantic Deep", "lat_range": (30, 65), "lon_range": (-60, -10)},
            {"name": "South Atlantic Deep", "lat_range": (-50, -5), "lon_range": (-45, 15)},
            {"name": "North Pacific Deep", "lat_range": (15, 55), "lon_range": (-175, -120)},
            {"name": "South Pacific Deep", "lat_range": (-50, -10), "lon_range": (-160, -70)},
            {"name": "Indian Ocean Deep", "lat_range": (-45, 10), "lon_range": (50, 110)},
            {"name": "Southern Ocean", "lat_range": (-65, -45), "lon_range": (-180, 180)},
        ]
    
    def is_over_ocean(self, lat: float, lon: float, strict: bool = True) -> Dict[str, any]:
        """
        Check if coordinates are over ocean.
        
        Args:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees
            strict: If True, only accepts deep ocean areas
            
        Returns:
            Dictionary with validation results
        """
        result = {
            "is_ocean": True,
            "confidence": 0.5,
            "reason": "Unknown",
            "nearest_land": None,
            "ocean_zone": None,
            "depth_estimate": "Unknown"
        }
        
        # First check if coordinates are clearly over major landmasses
        for landmass in self.major_landmasses:
            lat_min, lat_max = landmass["lat_range"]
            lon_min, lon_max = landmass["lon_range"]
            
            if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
                result.update({
                    "is_ocean": False,
                    "confidence": 0.9,
                    "reason": f"Coordinates are over {landmass['name']}",
                    "nearest_land": landmass['name']
                })
                return result
        
        # Check if coordinates are in known deep ocean zones
        for ocean_zone in self.deep_ocean_zones:
            lat_min, lat_max = ocean_zone["lat_range"]
            lon_min, lon_max = ocean_zone["lon_range"]
            
            if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
                result.update({
                    "is_ocean": True,
                    "confidence": 0.95,
                    "reason": f"Coordinates are in {ocean_zone['name']}",
                    "ocean_zone": ocean_zone['name'],
                    "depth_estimate": "Deep (>1000m)"
                })
                return result
        
        # For coordinates not in known zones, use distance-based heuristics
        distance_to_land = self.estimate_distance_to_nearest_land(lat, lon)
        
        if distance_to_land > 500:  # > 500km from land
            result.update({
                "is_ocean": True,
                "confidence": 0.8,
                "reason": f"Far from land ({distance_to_land:.0f}km)",
                "depth_estimate": "Likely deep"
            })
        elif distance_to_land > 200:  # 200-500km from land
            result.update({
                "is_ocean": True,
                "confidence": 0.7,
                "reason": f"Moderate distance from land ({distance_to_land:.0f}km)",
                "depth_estimate": "Medium depth"
            })
        elif distance_to_land > 50:  # 50-200km from land
            result.update({
                "is_ocean": True,
                "confidence": 0.6,
                "reason": f"Near coastline ({distance_to_land:.0f}km)",
                "depth_estimate": "Shallow to medium"
            })
        else:  # < 50km from land
            if strict:
                result.update({
                    "is_ocean": False,
                    "confidence": 0.8,
                    "reason": f"Too close to coastline ({distance_to_land:.0f}km)",
                    "depth_estimate": "Very shallow/coastal"
                })
            else:
                result.update({
                    "is_ocean": True,
                    "confidence": 0.4,
                    "reason": f"Coastal waters ({distance_to_land:.0f}km from land)",
                    "depth_estimate": "Shallow"
                })
        
        return result
    
    def estimate_distance_to_nearest_land(self, lat: float, lon: float) -> float:
        """
        Estimate distance to nearest major landmass (simplified calculation).
        
        Args:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees
            
        Returns:
            Estimated distance to nearest land in kilometers
        """
        min_distance = float('inf')
        
        for landmass in self.major_landmasses:
            lat_min, lat_max = landmass["lat_range"]
            lon_min, lon_max = landmass["lon_range"]
            
            # Find closest point on landmass boundary
            closest_lat = max(lat_min, min(lat_max, lat))
            closest_lon = max(lon_min, min(lon_max, lon))
            
            # Calculate distance to closest point
            distance = self.haversine_distance(lat, lon, closest_lat, closest_lon)
            min_distance = min(min_distance, distance)
        
        return min_distance
    
    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the great circle distance between two points on Earth.
        
        Args:
            lat1, lon1: First point coordinates
            lat2, lon2: Second point coordinates
            
        Returns:
            Distance in kilometers
        """
        R = 6371  # Earth's radius in kilometers
        
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    def get_ocean_depth_estimate(self, lat: float, lon: float) -> str:
        """
        Estimate ocean depth category based on location.
        
        Args:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees
            
        Returns:
            Depth category string
        """
        ocean_info = self.is_over_ocean(lat, lon)
        
        if not ocean_info["is_ocean"]:
            return "Land/Coastal"
        
        # Simplified depth estimation based on distance from land and location
        distance_to_land = self.estimate_distance_to_nearest_land(lat, lon)
        
        if distance_to_land > 1000:
            return "Abyssal (>4000m)"
        elif distance_to_land > 500:
            return "Deep Ocean (2000-4000m)"
        elif distance_to_land > 200:
            return "Bathyal (200-2000m)"
        elif distance_to_land > 50:
            return "Continental Slope (50-200m)"
        else:
            return "Continental Shelf (<50m)"


def validate_ocean_coordinates(lat: float, lon: float, strict: bool = True) -> Dict[str, any]:
    """
    Convenience function to validate ocean coordinates.
    
    Args:
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees
        strict: If True, only accepts deep ocean areas
        
    Returns:
        Validation results dictionary
    """
    validator = OceanValidator()
    return validator.is_over_ocean(lat, lon, strict)


def generate_safe_ocean_coordinates() -> Tuple[float, float]:
    """
    Generate guaranteed safe ocean coordinates in deep water.
    
    Returns:
        Tuple of (latitude, longitude) in decimal degrees
    """
    import random
    
    validator = OceanValidator()
    
    # Use predefined safe deep ocean zones
    safe_zones = [
        {"center": (45, -30), "radius": 8},    # North Atlantic
        {"center": (-25, -15), "radius": 10},  # South Atlantic
        {"center": (35, -150), "radius": 12},  # North Pacific
        {"center": (-30, -120), "radius": 10}, # South Pacific
        {"center": (-15, 80), "radius": 8},    # Indian Ocean
    ]
    
    max_attempts = 10
    for attempt in range(max_attempts):
        # Select random safe zone
        zone = random.choice(safe_zones)
        center_lat, center_lon = zone["center"]
        radius = zone["radius"]
        
        # Generate coordinates within the zone
        lat = center_lat + (random.random() - 0.5) * radius
        lon = center_lon + (random.random() - 0.5) * radius
        
        # Validate the coordinates
        validation = validator.is_over_ocean(lat, lon, strict=True)
        
        if validation["is_ocean"] and validation["confidence"] > 0.7:
            return lat, lon
    
    # Fallback to guaranteed safe coordinates
    return 35.0, -150.0  # North Pacific deep ocean


if __name__ == "__main__":
    # Test the validation system
    validator = OceanValidator()
    
    test_coordinates = [
        (40.7128, -74.0060),   # New York (land)
        (25.7617, -80.1918),   # Miami (coastal)
        (35.0, -150.0),        # North Pacific (deep ocean)
        (-24.6781, 20.7202),   # South Africa (land)
        (45.0, -30.0),         # North Atlantic (deep ocean)
    ]
    
    print("🌊 Ocean Coordinate Validation Test")
    print("=" * 50)
    
    for lat, lon in test_coordinates:
        result = validator.is_over_ocean(lat, lon)
        status = "✅ OCEAN" if result["is_ocean"] else "❌ LAND"
        print(f"{status} | {lat:7.4f}, {lon:8.4f} | {result['reason']} | Confidence: {result['confidence']:.1%}")
    
    print("\n🎲 Generating safe ocean coordinates:")
    for i in range(3):
        lat, lon = generate_safe_ocean_coordinates()
        validation = validator.is_over_ocean(lat, lon)
        print(f"   {i+1}. {lat:.4f}, {lon:.4f} | {validation['ocean_zone']} | {validation['confidence']:.1%}")