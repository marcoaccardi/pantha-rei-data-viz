#!/usr/bin/env python3
"""
Dynamic Global Coordinate System
Replaces static 216-station lookup with dynamic global ocean data retrieval.

This module provides dynamic coordinate-based ocean data access without
relying on predefined station locations, enabling global coverage.
"""

import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import logging

from .coordinate_system import WGS84CoordinateValidator, validate_wgs84_coordinates
from ..processors.ocean_currents_processor import OceanCurrentsProcessor
from ..processors.marine_bio_processor import MarineBiogeochemistryProcessor
from ..processors.wave_data_processor import WaveDataProcessor
from ..processors.coral_bleaching_processor import CoralBleachingProcessor
from ..processors.erddap_sst_processor import ERDDAPSSTProcessor

logger = logging.getLogger(__name__)

class DynamicOceanDataSystem:
    """
    Dynamic ocean data retrieval system supporting arbitrary global coordinates.
    Replaces static station-based lookups with real-time ERDDAP API integration.
    """

    def __init__(self):
        """Initialize dynamic coordinate system with real data processors."""
        self.coordinate_validator = WGS84CoordinateValidator()
        
        # Initialize real data processors (no synthetic fallbacks)
        self.processors = {
            'ocean_currents': OceanCurrentsProcessor(),
            'marine_bio': MarineBiogeochemistryProcessor(),
            'wave_data': WaveDataProcessor(),
            'coral_bleaching': CoralBleachingProcessor(),
            'sst': ERDDAPSSTProcessor()
        }
        
        # Processor mapping for different data types
        self.data_type_mapping = {
            'sea_surface_temperature': 'sst',
            'ocean_currents': 'ocean_currents',
            'wave_height': 'wave_data',
            'wave_data': 'wave_data',
            'chlorophyll': 'marine_bio',
            'marine_biology': 'marine_bio',
            'coral_bleaching': 'coral_bleaching',
            'ocean_chemistry': 'marine_bio',
            'biogeochemistry': 'marine_bio'
        }

        logger.info("🌍 Dynamic Ocean Data System initialized")
        logger.info("📡 Real ERDDAP data sources: Ocean Currents, Marine Bio, Waves, SST, Coral Bleaching")
        logger.info("❌ No synthetic data generation - Real data only")

    async def get_ocean_data_for_coordinates(self, latitude: float, longitude: float, 
                                           date: Optional[str] = None,
                                           data_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get comprehensive ocean data for any global coordinates.
        
        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees
            date: Date string (YYYY-MM-DD), defaults to today
            data_types: List of specific data types to retrieve, or None for all
            
        Returns:
            Dictionary with ocean data from real sources and coordinate metadata
        """
        # Validate coordinates first
        coord_result = self.coordinate_validator.validate_coordinates(latitude, longitude)
        
        if not coord_result.is_valid:
            raise ValueError(f"Invalid coordinates: {'; '.join(coord_result.validation_errors)}")
        
        # Use normalized coordinates for all data retrieval
        normalized_lat = coord_result.normalized_latitude
        normalized_lon = coord_result.normalized_longitude
        
        # Validate date
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        # Determine which data types to retrieve
        if data_types is None:
            data_types = list(self.data_type_mapping.keys())
        
        logger.info(f"🌊 Retrieving ocean data for {normalized_lat:.6f}, {normalized_lon:.6f} on {date}")
        logger.info(f"📊 Data types: {', '.join(data_types)}")
        
        # Retrieve data from real sources concurrently
        data_results = {}
        failed_sources = []
        
        # Process each data type
        for data_type in data_types:
            if data_type in self.data_type_mapping:
                processor_key = self.data_type_mapping[data_type]
                processor = self.processors[processor_key]
                
                try:
                    logger.debug(f"📡 Querying {processor_key} for {data_type}")
                    result = processor.get_processor_data(normalized_lat, normalized_lon, date)
                    
                    if result and result.get('data'):
                        data_results[data_type] = result
                        logger.info(f"✅ {data_type}: {result['metadata']['data_source']}")
                    else:
                        failed_sources.append(data_type)
                        logger.warning(f"⚠️ {data_type}: No data returned")
                        
                except Exception as e:
                    failed_sources.append(data_type)
                    logger.error(f"❌ {data_type} failed: {str(e)}")
            else:
                logger.warning(f"⚠️ Unknown data type: {data_type}")
        
        # Create comprehensive response
        response = {
            "coordinate_info": {
                "request_coordinates": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "validated_coordinates": {
                    "latitude": normalized_lat,
                    "longitude": normalized_lon,
                    "coordinate_reference_system": coord_result.crs
                },
                "ocean_validation": {
                    "is_over_ocean": coord_result.is_over_ocean,
                    "confidence": coord_result.ocean_confidence,
                    "ocean_zone": coord_result.metadata.get("ocean_zone"),
                    "depth_estimate": coord_result.metadata.get("depth_estimate")
                }
            },
            "data_summary": {
                "successful_retrievals": len(data_results),
                "failed_retrievals": len(failed_sources),
                "success_rate": len(data_results) / len(data_types) if data_types else 0,
                "failed_sources": failed_sources
            },
            "ocean_data": data_results,
            "metadata": {
                "retrieval_timestamp": datetime.utcnow().isoformat() + "Z",
                "date_requested": date,
                "system": "DynamicOceanDataSystem",
                "data_policy": "Real data only - No synthetic generation"
            }
        }
        
        # Log summary
        success_count = len(data_results)
        total_count = len(data_types)
        logger.info(f"📊 Data retrieval complete: {success_count}/{total_count} successful")
        
        if failed_sources:
            logger.warning(f"⚠️ Failed sources: {', '.join(failed_sources)}")
        
        return response

    async def get_single_parameter(self, latitude: float, longitude: float, 
                                 parameter: str, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get a single oceanographic parameter for coordinates.
        
        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees
            parameter: Parameter name (e.g., 'sea_surface_temperature', 'ocean_currents')
            date: Date string (YYYY-MM-DD), defaults to today
            
        Returns:
            Dictionary with single parameter data
        """
        result = await self.get_ocean_data_for_coordinates(
            latitude, longitude, date, [parameter]
        )
        
        if parameter in result["ocean_data"]:
            return result["ocean_data"][parameter]
        else:
            raise ValueError(f"Parameter '{parameter}' could not be retrieved for coordinates ({latitude}, {longitude})")

    def get_supported_parameters(self) -> List[str]:
        """Get list of supported oceanographic parameters."""
        return list(self.data_type_mapping.keys())

    def get_supported_processors(self) -> List[str]:
        """Get list of available data processors."""
        return list(self.processors.keys())

    async def validate_global_coverage(self, test_coordinates: List[Tuple[float, float]]) -> Dict[str, Any]:
        """
        Test global coverage by attempting data retrieval at multiple points.
        
        Args:
            test_coordinates: List of (latitude, longitude) tuples to test
            
        Returns:
            Coverage validation report
        """
        logger.info(f"🌍 Testing global coverage at {len(test_coordinates)} locations")
        
        results = []
        successful_locations = 0
        
        for lat, lon in test_coordinates:
            try:
                coord_result = self.coordinate_validator.validate_coordinates(lat, lon)
                
                location_result = {
                    "coordinates": (lat, lon),
                    "normalized_coordinates": (coord_result.normalized_latitude, coord_result.normalized_longitude),
                    "is_valid": coord_result.is_valid,
                    "is_over_ocean": coord_result.is_over_ocean,
                    "ocean_confidence": coord_result.ocean_confidence,
                    "validation_errors": coord_result.validation_errors,
                    "data_availability": {}
                }
                
                if coord_result.is_valid and coord_result.is_over_ocean:
                    # Test a subset of parameters for each location
                    test_params = ['sea_surface_temperature', 'ocean_currents']
                    
                    for param in test_params:
                        try:
                            data = await self.get_single_parameter(lat, lon, param)
                            location_result["data_availability"][param] = True
                        except:
                            location_result["data_availability"][param] = False
                    
                    if any(location_result["data_availability"].values()):
                        successful_locations += 1
                
                results.append(location_result)
                
            except Exception as e:
                results.append({
                    "coordinates": (lat, lon),
                    "error": str(e)
                })
        
        coverage_report = {
            "test_summary": {
                "total_locations": len(test_coordinates),
                "successful_locations": successful_locations,
                "coverage_percentage": (successful_locations / len(test_coordinates)) * 100
            },
            "location_results": results,
            "system_info": {
                "system": "DynamicOceanDataSystem",
                "processors": list(self.processors.keys()),
                "coordinate_validation": "WGS84/EPSG:4326"
            }
        }
        
        logger.info(f"🌍 Coverage test complete: {successful_locations}/{len(test_coordinates)} locations successful ({coverage_report['test_summary']['coverage_percentage']:.1f}%)")
        
        return coverage_report

    async def close(self):
        """Clean up resources."""
        for processor in self.processors.values():
            if hasattr(processor, 'close'):
                processor.close()
        logger.info("🔄 Dynamic Ocean Data System closed")

# Global instance for use across the application
dynamic_ocean_system = DynamicOceanDataSystem()

async def get_ocean_data_dynamic(latitude: float, longitude: float, 
                               date: Optional[str] = None,
                               data_types: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Convenience function for dynamic ocean data retrieval.
    
    Args:
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees
        date: Date string (YYYY-MM-DD), defaults to today
        data_types: List of specific data types to retrieve, or None for all
        
    Returns:
        Dictionary with ocean data from real sources
    """
    return await dynamic_ocean_system.get_ocean_data_for_coordinates(
        latitude, longitude, date, data_types
    )

if __name__ == "__main__":
    # Test the dynamic coordinate system
    import asyncio
    
    async def test_dynamic_system():
        system = DynamicOceanDataSystem()
        
        # Test coordinates (avoiding the original 216 static stations)
        test_coords = [
            (25.0, -80.0),    # Miami area ocean
            (35.0, -150.0),   # North Pacific 
            (45.0, -30.0),    # North Atlantic
            (-20.0, 50.0),    # Indian Ocean
        ]
        
        print("🧪 Testing Dynamic Ocean Data System")
        print("=" * 60)
        
        for lat, lon in test_coords:
            try:
                print(f"\n📍 Testing: {lat}°N, {lon}°E")
                result = await system.get_ocean_data_for_coordinates(lat, lon)
                
                print(f"   Ocean: {result['coordinate_info']['ocean_validation']['is_over_ocean']}")
                print(f"   Success: {result['data_summary']['successful_retrievals']}/{len(system.get_supported_parameters())} parameters")
                print(f"   Sources: {list(result['ocean_data'].keys())}")
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        # Test global coverage
        print(f"\n🌍 Testing Global Coverage")
        coverage = await system.validate_global_coverage(test_coords)
        print(f"   Coverage: {coverage['test_summary']['coverage_percentage']:.1f}%")
        
        await system.close()
    
    asyncio.run(test_dynamic_system())