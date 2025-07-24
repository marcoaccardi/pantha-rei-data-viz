#!/usr/bin/env python3
"""
WGS84 Coordinate System Validation and Utilities
Implements reliable coordinate system retrieval following ERDDAP standards.

This module provides comprehensive coordinate validation, transformation, and
standardization for oceanographic data retrieval systems.
"""

import math
from typing import Dict, Tuple, Optional, List, Any
from dataclasses import dataclass
from enum import Enum
import json

class CoordinateReferenceSystem(Enum):
    """Supported coordinate reference systems."""
    WGS84 = "EPSG:4326"
    WEB_MERCATOR = "EPSG:3857"

@dataclass
class CoordinateValidationResult:
    """Result of coordinate validation with detailed information."""
    is_valid: bool
    longitude: float
    latitude: float
    crs: str
    normalized_longitude: float  # Always -180 to 180
    normalized_latitude: float   # Always -90 to 90
    is_over_ocean: bool
    ocean_confidence: float
    validation_errors: List[str]
    validation_warnings: List[str]
    metadata: Dict[str, Any]

    def add_error(self, message: str):
        """Add validation error."""
        self.validation_errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str):
        """Add validation warning."""
        self.validation_warnings.append(message)

class WGS84CoordinateValidator:
    """
    WGS84 (EPSG:4326) coordinate validation and standardization.
    Follows NOAA ERDDAP coordinate conventions and oceanographic standards.
    """

    # WGS84 coordinate bounds
    WGS84_LAT_MIN = -90.0
    WGS84_LAT_MAX = 90.0
    WGS84_LON_MIN = -180.0
    WGS84_LON_MAX = 180.0

    # ERDDAP standard units and conventions
    ERDDAP_LONGITUDE_UNITS = "degrees_east"
    ERDDAP_LATITUDE_UNITS = "degrees_north"
    ERDDAP_CRS = "EPSG:4326"

    def __init__(self):
        """Initialize coordinate validator with oceanographic boundaries."""
        # Import ocean validation from existing module
        from .ocean_validation import OceanValidator
        self.ocean_validator = OceanValidator()

    def validate_coordinates(self, latitude: float, longitude: float, 
                           strict_ocean_check: bool = False) -> CoordinateValidationResult:
        """
        Comprehensive coordinate validation following WGS84 and ERDDAP standards.

        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees  
            strict_ocean_check: If True, reject coordinates not over deep ocean

        Returns:
            CoordinateValidationResult with validation details
        """
        result = CoordinateValidationResult(
            is_valid=True,
            longitude=longitude,
            latitude=latitude,
            crs=self.ERDDAP_CRS,
            normalized_longitude=longitude,
            normalized_latitude=latitude,
            is_over_ocean=False,
            ocean_confidence=0.0,
            validation_errors=[],
            validation_warnings=[],
            metadata={}
        )

        # 1. Basic coordinate bounds validation
        self._validate_coordinate_bounds(result)

        # 2. Normalize coordinates to standard WGS84 ranges
        self._normalize_coordinates(result)

        # 3. Ocean/land validation
        self._validate_ocean_location(result, strict_ocean_check)

        # 4. Add ERDDAP-compliant metadata
        self._add_erddap_metadata(result)

        # 5. Precision validation for coordinate quality
        self._validate_coordinate_precision(result)

        return result

    def _validate_coordinate_bounds(self, result: CoordinateValidationResult):
        """Validate coordinates are within WGS84 bounds."""
        
        # Check latitude bounds
        if not (self.WGS84_LAT_MIN <= result.latitude <= self.WGS84_LAT_MAX):
            result.add_error(
                f"Latitude {result.latitude} outside WGS84 bounds "
                f"({self.WGS84_LAT_MIN} to {self.WGS84_LAT_MAX})"
            )

        # Check longitude bounds (allow 0-360 range for conversion)
        if not (self.WGS84_LON_MIN <= result.longitude <= self.WGS84_LON_MAX) and \
           not (0.0 <= result.longitude <= 360.0):
            result.add_error(
                f"Longitude {result.longitude} outside valid bounds "
                f"({self.WGS84_LON_MIN} to {self.WGS84_LON_MAX} or 0 to 360)"
            )

    def _normalize_coordinates(self, result: CoordinateValidationResult):
        """Normalize coordinates to standard WGS84 ranges."""
        
        # Normalize latitude (clamp to valid range)
        result.normalized_latitude = max(self.WGS84_LAT_MIN, 
                                       min(self.WGS84_LAT_MAX, result.latitude))

        # Normalize longitude (convert 0-360 to -180-180 if needed)
        if result.longitude > 180.0:
            result.normalized_longitude = result.longitude - 360.0
            result.add_warning(
                f"Longitude converted from 0-360 range: {result.longitude} → {result.normalized_longitude}"
            )
        else:
            result.normalized_longitude = result.longitude

        # Ensure longitude is within bounds after normalization
        result.normalized_longitude = max(self.WGS84_LON_MIN, 
                                        min(self.WGS84_LON_MAX, result.normalized_longitude))

    def _validate_ocean_location(self, result: CoordinateValidationResult, strict: bool):
        """Validate coordinates are over ocean using existing ocean validator."""
        
        try:
            ocean_result = self.ocean_validator.is_over_ocean(
                result.normalized_latitude, 
                result.normalized_longitude, 
                strict=strict
            )
            
            result.is_over_ocean = ocean_result["is_ocean"]
            result.ocean_confidence = ocean_result["confidence"]
            
            # Add ocean metadata
            result.metadata.update({
                "ocean_zone": ocean_result.get("ocean_zone"),
                "depth_estimate": ocean_result.get("depth_estimate"),
                "distance_to_land_km": ocean_result.get("distance_to_land_km"),
                "nearest_land": ocean_result.get("nearest_land")
            })

            # Add validation messages based on ocean status
            if not result.is_over_ocean:
                if strict:
                    result.add_error(f"Not over ocean: {ocean_result['reason']}")
                else:
                    result.add_warning(f"May not be over ocean: {ocean_result['reason']}")
            elif result.ocean_confidence < 0.6:
                result.add_warning(f"Low ocean confidence: {result.ocean_confidence:.1%}")

        except Exception as e:
            result.add_warning(f"Ocean validation failed: {str(e)}")
            result.ocean_confidence = 0.5  # Default moderate confidence

    def _add_erddap_metadata(self, result: CoordinateValidationResult):
        """Add ERDDAP-compliant coordinate metadata."""
        
        result.metadata.update({
            "longitude_units": self.ERDDAP_LONGITUDE_UNITS,
            "latitude_units": self.ERDDAP_LATITUDE_UNITS,
            "coordinate_reference_system": self.ERDDAP_CRS,
            "longitude_axis": "X",
            "latitude_axis": "Y",
            "longitude_coordinate_type": "Lon",
            "latitude_coordinate_type": "Lat",
            "geospatial_bounds_crs": self.ERDDAP_CRS,
            "longitude_standard_name": "longitude",
            "latitude_standard_name": "latitude"
        })

    def _validate_coordinate_precision(self, result: CoordinateValidationResult):
        """Validate coordinate precision for oceanographic data quality."""
        
        # Check for reasonable precision (not too many decimal places)
        lat_decimals = len(str(result.latitude).split('.')[-1]) if '.' in str(result.latitude) else 0
        lon_decimals = len(str(result.longitude).split('.')[-1]) if '.' in str(result.longitude) else 0

        if lat_decimals > 6 or lon_decimals > 6:
            result.add_warning(
                f"Very high precision coordinates ({lat_decimals}, {lon_decimals} decimals) "
                "may indicate over-specification"
            )

        # Check for suspiciously round numbers
        if result.latitude == int(result.latitude) and result.longitude == int(result.longitude):
            result.add_warning("Integer coordinates may indicate low precision data")

    def convert_coordinates(self, latitude: float, longitude: float, 
                          source_crs: str = "EPSG:4326", 
                          target_crs: str = "EPSG:4326") -> Tuple[float, float]:
        """
        Convert coordinates between different coordinate reference systems.
        
        Args:
            latitude: Source latitude
            longitude: Source longitude  
            source_crs: Source CRS (currently only EPSG:4326 supported)
            target_crs: Target CRS (currently only EPSG:4326 supported)
            
        Returns:
            Tuple of (target_latitude, target_longitude)
        """
        if source_crs != "EPSG:4326" or target_crs != "EPSG:4326":
            raise NotImplementedError("Only EPSG:4326 (WGS84) conversions supported currently")
        
        # Validate and normalize the coordinates
        result = self.validate_coordinates(latitude, longitude)
        if not result.is_valid:
            raise ValueError(f"Invalid coordinates: {result.validation_errors}")
        
        return result.normalized_latitude, result.normalized_longitude

    def format_for_erddap_query(self, latitude: float, longitude: float) -> Dict[str, str]:
        """
        Format coordinates for ERDDAP query strings.
        
        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees
            
        Returns:
            Dictionary with formatted coordinate strings for ERDDAP queries
        """
        # Validate coordinates first
        result = self.validate_coordinates(latitude, longitude)
        if not result.is_valid:
            raise ValueError(f"Invalid coordinates for ERDDAP query: {result.validation_errors}")

        lat = result.normalized_latitude
        lon = result.normalized_longitude

        return {
            "latitude": f"{lat:.6f}",
            "longitude": f"{lon:.6f}",
            "lat_constraint": f"[({lat:.6f}):1:({lat:.6f})]",
            "lon_constraint": f"[({lon:.6f}):1:({lon:.6f})]",
            "lat_units": self.ERDDAP_LATITUDE_UNITS,
            "lon_units": self.ERDDAP_LONGITUDE_UNITS
        }

    def get_coordinate_bounds(self, center_lat: float, center_lon: float, 
                            radius_km: float) -> Dict[str, float]:
        """
        Calculate coordinate bounds for a circular area around a center point.
        
        Args:
            center_lat: Center latitude
            center_lon: Center longitude
            radius_km: Radius in kilometers
            
        Returns:
            Dictionary with min/max latitude and longitude bounds
        """
        # Earth's radius in kilometers
        R = 6371.0
        
        # Convert radius to degrees (approximate)
        lat_delta = radius_km / (R * math.pi / 180)
        lon_delta = radius_km / (R * math.cos(math.radians(center_lat)) * math.pi / 180)
        
        bounds = {
            "lat_min": max(self.WGS84_LAT_MIN, center_lat - lat_delta),
            "lat_max": min(self.WGS84_LAT_MAX, center_lat + lat_delta),
            "lon_min": max(self.WGS84_LON_MIN, center_lon - lon_delta),
            "lon_max": min(self.WGS84_LON_MAX, center_lon + lon_delta)
        }
        
        return bounds

    def is_coordinate_in_bounds(self, latitude: float, longitude: float, 
                              bounds: Dict[str, float]) -> bool:
        """Check if coordinate is within specified bounds."""
        return (bounds["lat_min"] <= latitude <= bounds["lat_max"] and
                bounds["lon_min"] <= longitude <= bounds["lon_max"])

def validate_wgs84_coordinates(latitude: float, longitude: float, 
                             strict_ocean: bool = False) -> CoordinateValidationResult:
    """
    Convenience function for WGS84 coordinate validation.
    
    Args:
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees
        strict_ocean: If True, require coordinates to be over deep ocean
        
    Returns:
        CoordinateValidationResult with validation details
    """
    validator = WGS84CoordinateValidator()
    return validator.validate_coordinates(latitude, longitude, strict_ocean)

def normalize_longitude(longitude: float) -> float:
    """
    Normalize longitude to -180 to 180 range.
    
    Args:
        longitude: Longitude in any valid range
        
    Returns:
        Normalized longitude in -180 to 180 range
    """
    if longitude > 180:
        return longitude - 360
    elif longitude < -180:
        return longitude + 360
    return longitude

def format_coordinate_for_display(latitude: float, longitude: float, 
                                precision: int = 4) -> str:
    """
    Format coordinates for human-readable display.
    
    Args:
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees
        precision: Number of decimal places
        
    Returns:
        Formatted coordinate string
    """
    lat_dir = "N" if latitude >= 0 else "S"
    lon_dir = "E" if longitude >= 0 else "W"
    
    return f"{abs(latitude):.{precision}f}°{lat_dir}, {abs(longitude):.{precision}f}°{lon_dir}"

if __name__ == "__main__":
    # Test the coordinate validation system
    validator = WGS84CoordinateValidator()
    
    test_coordinates = [
        (25.7617, -80.1918),    # Miami (coastal)
        (35.0, -150.0),         # North Pacific (deep ocean)
        (40.7128, -74.0060),    # New York (land)
        (0.0, 0.0),             # Equator/Prime Meridian intersection
        (45.0, -30.0),          # North Atlantic (deep ocean)
        (91.0, 200.0),          # Invalid coordinates
    ]
    
    print("🌍 WGS84 Coordinate Validation Test")
    print("=" * 60)
    
    for lat, lon in test_coordinates:
        result = validator.validate_coordinates(lat, lon)
        status = "✅ VALID" if result.is_valid else "❌ INVALID"
        ocean_status = "🌊 OCEAN" if result.is_over_ocean else "🏞️ LAND"
        
        print(f"\n{status} | {lat:8.4f}, {lon:9.4f}")
        print(f"   Normalized: {result.normalized_latitude:7.4f}, {result.normalized_longitude:8.4f}")
        print(f"   {ocean_status} (confidence: {result.ocean_confidence:.1%})")
        
        if result.validation_errors:
            for error in result.validation_errors:
                print(f"   ❌ {error}")
        
        if result.validation_warnings:
            for warning in result.validation_warnings:
                print(f"   ⚠️  {warning}")
        
        # Test ERDDAP formatting
        if result.is_valid:
            try:
                erddap_format = validator.format_for_erddap_query(lat, lon)
                print(f"   📡 ERDDAP: lat={erddap_format['latitude']}, lon={erddap_format['longitude']}")
            except ValueError as e:
                print(f"   📡 ERDDAP: {e}")