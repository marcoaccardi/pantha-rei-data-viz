#!/usr/bin/env python3
"""
Base Processor with Standardized WGS84 Coordinate Handling
Provides common coordinate validation and standardization for all ocean data processors.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import logging

from ..utils.coordinate_system import (
    WGS84CoordinateValidator, 
    validate_wgs84_coordinates,
    CoordinateValidationResult
)

logger = logging.getLogger(__name__)

class CoordinateStandardizedProcessor(ABC):
    """
    Base class for ocean data processors with standardized WGS84 coordinate handling.
    
    All processors should inherit from this class to ensure consistent coordinate
    validation, normalization, and ERDDAP-compliant formatting.
    """

    def __init__(self):
        """Initialize coordinate validator."""
        self.coordinate_validator = WGS84CoordinateValidator()
        self.strict_ocean_validation = False  # Can be overridden by subclasses

    def validate_and_normalize_coordinates(self, latitude: float, longitude: float) -> CoordinateValidationResult:
        """
        Validate and normalize coordinates according to WGS84 standards.
        
        Args:
            latitude: Input latitude in decimal degrees
            longitude: Input longitude in decimal degrees
            
        Returns:
            CoordinateValidationResult with validated and normalized coordinates
            
        Raises:
            ValueError: If coordinates are invalid and cannot be processed
        """
        try:
            result = self.coordinate_validator.validate_coordinates(
                latitude, longitude, strict_ocean_check=self.strict_ocean_validation
            )
            
            # Log coordinate validation results
            if result.validation_warnings:
                for warning in result.validation_warnings:
                    logger.warning(f"Coordinate warning: {warning}")
            
            if not result.is_valid:
                error_msg = f"Invalid coordinates ({latitude}, {longitude}): {'; '.join(result.validation_errors)}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Log successful validation with details
            logger.debug(
                f"Coordinates validated: ({latitude}, {longitude}) → "
                f"({result.normalized_latitude:.6f}, {result.normalized_longitude:.6f}) "
                f"[Ocean: {result.is_over_ocean}, Confidence: {result.ocean_confidence:.1%}]"
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Coordinate validation failed for ({latitude}, {longitude}): {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def get_normalized_coordinates(self, latitude: float, longitude: float) -> Tuple[float, float]:
        """
        Get normalized WGS84 coordinates.
        
        Args:
            latitude: Input latitude in decimal degrees
            longitude: Input longitude in decimal degrees
            
        Returns:
            Tuple of (normalized_latitude, normalized_longitude)
        """
        result = self.validate_and_normalize_coordinates(latitude, longitude)
        return result.normalized_latitude, result.normalized_longitude

    def format_coordinates_for_erddap(self, latitude: float, longitude: float) -> Dict[str, str]:
        """
        Format coordinates for ERDDAP queries with validation.
        
        Args:
            latitude: Input latitude in decimal degrees
            longitude: Input longitude in decimal degrees
            
        Returns:
            Dictionary with ERDDAP-formatted coordinate strings
        """
        # Validate coordinates first
        result = self.validate_and_normalize_coordinates(latitude, longitude)
        
        # Use normalized coordinates for ERDDAP query
        return self.coordinate_validator.format_for_erddap_query(
            result.normalized_latitude, result.normalized_longitude
        )

    def validate_date_parameter(self, date: Optional[str] = None) -> str:
        """
        Validate and standardize date parameter.
        
        Args:
            date: Date string in YYYY-MM-DD format, or None for today
            
        Returns:
            Validated date string in YYYY-MM-DD format
        """
        if date is None:
            return datetime.now().strftime('%Y-%m-%d')
        
        try:
            # Validate date format
            datetime.strptime(date, '%Y-%m-%d')
            return date
        except ValueError:
            # Try to parse other common formats
            try:
                parsed_date = datetime.strptime(date, '%Y/%m/%d')
                return parsed_date.strftime('%Y-%m-%d')
            except ValueError:
                try:
                    parsed_date = datetime.strptime(date, '%m/%d/%Y')
                    return parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    error_msg = f"Invalid date format: {date}. Expected YYYY-MM-DD."
                    logger.error(error_msg)
                    raise ValueError(error_msg)

    def create_standardized_response(self, data: Dict[str, Any], 
                                   latitude: float, longitude: float, 
                                   date: str, source: str = "Unknown") -> Dict[str, Any]:
        """
        Create standardized response with coordinate metadata.
        
        Args:
            data: Processed data dictionary
            latitude: Original input latitude
            longitude: Original input longitude
            date: Date string
            source: Data source identifier
            
        Returns:
            Standardized response dictionary with metadata
        """
        # Get coordinate validation result for metadata
        coord_result = self.validate_and_normalize_coordinates(latitude, longitude)
        
        return {
            "data": data,
            "metadata": {
                "request_coordinates": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "coordinate_reference_system": "EPSG:4326"
                },
                "normalized_coordinates": {
                    "latitude": coord_result.normalized_latitude,
                    "longitude": coord_result.normalized_longitude,
                    "coordinate_reference_system": coord_result.crs
                },
                "ocean_validation": {
                    "is_over_ocean": coord_result.is_over_ocean,
                    "confidence": coord_result.ocean_confidence,
                    "ocean_zone": coord_result.metadata.get("ocean_zone"),
                    "depth_estimate": coord_result.metadata.get("depth_estimate")
                },
                "request_date": date,
                "data_source": source,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "coordinate_validation_warnings": coord_result.validation_warnings
            }            
        }

    def log_coordinate_request(self, latitude: float, longitude: float, 
                             date: str, processor_name: str):
        """
        Log coordinate-based data request with standardized format.
        
        Args:
            latitude: Request latitude
            longitude: Request longitude
            date: Request date
            processor_name: Name of the processor making the request
        """
        try:
            coord_result = self.validate_and_normalize_coordinates(latitude, longitude)
            ocean_status = "🌊 OCEAN" if coord_result.is_over_ocean else "🏞️ LAND"
            
            logger.info(
                f"{processor_name} request: {latitude:.4f}°N, {longitude:.4f}°E "
                f"({coord_result.normalized_latitude:.6f}, {coord_result.normalized_longitude:.6f}) "
                f"on {date} {ocean_status} [{coord_result.ocean_confidence:.1%}]"
            )
        except Exception as e:
            logger.warning(f"Could not log coordinate request: {e}")

    @abstractmethod
    def get_processor_data(self, lat: float, lon: float, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Abstract method that subclasses must implement for their specific data retrieval.
        
        This method should use the coordinate validation methods provided by the base class
        and return data in the standardized format.
        
        Args:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees
            date: Date string (YYYY-MM-DD), defaults to today
            
        Returns:
            Dictionary with processor-specific data and standardized metadata
        """
        pass

class OceanDataProcessor(CoordinateStandardizedProcessor):
    """
    Base class specifically for ocean data processors with strict ocean validation.
    """

    def __init__(self):
        """Initialize with strict ocean validation enabled."""
        super().__init__()
        self.strict_ocean_validation = True  # Require coordinates to be over ocean

class CoastalDataProcessor(CoordinateStandardizedProcessor):
    """
    Base class for coastal/marine data processors with lenient ocean validation.
    """

    def __init__(self):
        """Initialize with lenient validation for coastal areas."""
        super().__init__()
        self.strict_ocean_validation = False  # Allow coastal coordinates

def create_coordinate_validation_decorator(strict_ocean: bool = False):
    """
    Create a decorator for coordinate validation on processor methods.
    
    Args:
        strict_ocean: If True, require coordinates to be over deep ocean
        
    Returns:
        Decorator function
    """
    def decorator(func):
        def wrapper(self, lat: float, lon: float, *args, **kwargs):
            # Validate coordinates before calling the original method
            result = validate_wgs84_coordinates(lat, lon, strict_ocean=strict_ocean)
            
            if not result.is_valid:
                raise ValueError(f"Invalid coordinates: {'; '.join(result.validation_errors)}")
            
            # Call original method with normalized coordinates
            return func(self, result.normalized_latitude, result.normalized_longitude, *args, **kwargs)
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    
    return decorator

# Convenience decorators
validate_ocean_coordinates = create_coordinate_validation_decorator(strict_ocean=True)
validate_coordinates = create_coordinate_validation_decorator(strict_ocean=False)

if __name__ == "__main__":
    # Test the base processor coordinate handling
    
    class TestProcessor(CoordinateStandardizedProcessor):
        def get_processor_data(self, lat: float, lon: float, date: Optional[str] = None) -> Dict[str, Any]:
            # Validate coordinates
            normalized_lat, normalized_lon = self.get_normalized_coordinates(lat, lon)
            validated_date = self.validate_date_parameter(date)
            
            # Mock data
            test_data = {
                "temperature": 25.5,
                "salinity": 35.2
            }
            
            return self.create_standardized_response(
                test_data, lat, lon, validated_date, "TestProcessor"
            )
    
    # Test the processor
    processor = TestProcessor()
    
    test_cases = [
        (25.7617, -80.1918, "2024-01-15"),  # Miami
        (35.0, -150.0, None),               # North Pacific
        (45.0, 200.0, "2024-01-15"),        # Invalid longitude (should be converted)
    ]
    
    print("🧪 Testing Base Processor Coordinate Handling")
    print("=" * 60)
    
    for lat, lon, date in test_cases:
        try:
            result = processor.get_processor_data(lat, lon, date)
            print(f"\n✅ SUCCESS: {lat}, {lon} → {result['metadata']['normalized_coordinates']['latitude']:.6f}, {result['metadata']['normalized_coordinates']['longitude']:.6f}")
            print(f"   Ocean: {result['metadata']['ocean_validation']['is_over_ocean']} ({result['metadata']['ocean_validation']['confidence']:.1%})")
            if result['metadata']['coordinate_validation_warnings']:
                for warning in result['metadata']['coordinate_validation_warnings']:
                    print(f"   ⚠️ {warning}")
        except Exception as e:
            print(f"\n❌ ERROR: {lat}, {lon} - {e}")