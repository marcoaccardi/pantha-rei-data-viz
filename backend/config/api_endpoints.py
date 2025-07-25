#!/usr/bin/env python3
"""
API endpoints and configuration for ocean climate data sources.
Priority APIs based on comprehensive climate analysis requirements.
"""

from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class APIEndpoint:
    """Configuration for an API endpoint."""
    name: str
    base_url: str
    api_type: str  # 'rest', 'opendap', 'wms', 'wfs'
    authentication_required: bool
    rate_limit: str
    description: str
    documentation_url: str

# Priority API endpoints based on climate analysis requirements
API_ENDPOINTS = {
    # #1 RECOMMENDED: Copernicus Marine Service
    'copernicus': APIEndpoint(
        name="Copernicus Marine Service",
        base_url="https://data.marine.copernicus.eu",
        api_type="rest",
        authentication_required=True,
        rate_limit="No quotas on volume or bandwidth",
        description="Direct API access with subset queries, no downloads required. Comprehensive ocean climate data.",
        documentation_url="https://help.marine.copernicus.eu/"
    ),
    
    # #2 NOAA CO-OPS API
    'noaa_cops': APIEndpoint(
        name="NOAA CO-OPS API",
        base_url="https://api.tidesandcurrents.noaa.gov/api/prod/datagetter",
        api_type="rest",
        authentication_required=False,
        rate_limit="Reasonable rate limits, generous for typical use",
        description="Real-time coastal data, sea level trends, water temperature, extreme statistics.",
        documentation_url="https://api.tidesandcurrents.noaa.gov/api/prod/"
    ),
    
    # #3 EMODnet Physics
    'emodnet': APIEndpoint(
        name="EMODnet Physics",
        base_url="https://geoservice.maris.nl",
        api_type="wms",
        authentication_required=False,
        rate_limit="Standard web service limits",
        description="European ocean data federation, WMS/WFS services, temperature/salinity climatologies.",
        documentation_url="https://cdi-open.seadatanet.org/api"
    ),
    
    # #4 PANGAEA API
    'pangaea': APIEndpoint(
        name="PANGAEA API",
        base_url="https://pangaea.de",
        api_type="rest",
        authentication_required=False,
        rate_limit="Academic use encouraged, reasonable limits",
        description="Research-quality datasets, microplastics data, paleoclimate records.",
        documentation_url="https://pangaea.de/submit/documentation/api"
    ),
    
    # #5 NASA Ocean Data
    'nasa_ocean': APIEndpoint(
        name="NASA Ocean Data",
        base_url="https://oceandata.sci.gsfc.nasa.gov",
        api_type="opendap",
        authentication_required=False,
        rate_limit="Standard NASA Earthdata limits",
        description="Satellite climate records, long-term global observations via OPeNDAP.",
        documentation_url="https://oceancolor.gsfc.nasa.gov/data/overview/"
    )
}

# Climate data type categories
CLIMATE_DATA_TYPES = {
    'temperature_heat': {
        'name': 'Temperature & Heat',
        'parameters': [
            'sea_surface_temperature',
            'sst_anomalies', 
            'ocean_heat_content',
            'subsurface_temperature',
            'marine_heatwave_indicators',
            'temperature_stratification',
            'mixed_layer_depth'
        ],
        'description': 'Sea surface temperature anomalies, ocean heat content, marine heatwaves'
    },
    
    'sea_level_dynamics': {
        'name': 'Sea Level & Ocean Dynamics', 
        'parameters': [
            'sea_level_rise_rates',
            'sea_level_anomalies',
            'steric_sea_level',
            'ocean_circulation_changes',
            'gulf_stream_indices',
            'amoc_indicators'
        ],
        'description': 'Sea level rise rates, ocean circulation changes, AMOC indicators'
    },
    
    'salinity_water_cycle': {
        'name': 'Salinity & Water Cycle',
        'parameters': [
            'sea_surface_salinity',
            'salinity_stratification', 
            'evaporation_precipitation_balance',
            'river_discharge_impacts',
            'haline_circulation_changes'
        ],
        'description': 'Sea surface salinity trends, water cycle indicators, circulation changes'
    },
    
    'ocean_chemistry': {
        'name': 'Ocean Chemistry & Acidification',
        'parameters': [
            'ph_levels',
            'dissolved_co2',
            'carbonate_saturation',
            'total_alkalinity',
            'dissolved_oxygen',
            'nutrient_distribution'
        ],
        'description': 'Ocean acidification, carbon cycle indicators, biogeochemical cycles'
    },
    
    'cryosphere_ice': {
        'name': 'Cryosphere & Ice',
        'parameters': [
            'sea_ice_extent',
            'sea_ice_thickness',
            'ice_age_distribution',
            'ice_free_season_length',
            'glacier_discharge',
            'ice_shelf_stability'
        ],
        'description': 'Sea ice extent/thickness, ice age distribution, ice sheet contributions'
    },
    
    'biological_ecosystem': {
        'name': 'Biological & Ecosystem Indicators',
        'parameters': [
            'chlorophyll_a',
            'phytoplankton_community',
            'fish_distribution_migrations',
            'coral_bleaching_frequency',
            'species_range_boundaries',
            'biodiversity_indices'
        ],
        'description': 'Primary productivity, species shifts, ecosystem health metrics'
    },
    
    'pollution_human_impacts': {
        'name': 'Pollution & Human Impacts',
        'parameters': [
            'microplastics_concentration',
            'microplastics_size_distribution',
            'microplastics_transport_pathways',
            'marine_debris_accumulation',
            'chemical_pollutants',
            'ocean_noise_levels',
            'coastal_development_impacts'
        ],
        'description': 'Microplastics pollution, chemical contaminants, anthropogenic impacts'
    },
    
    'extreme_events': {
        'name': 'Extreme Events & Variability',
        'parameters': [
            'hurricane_typhoon_intensity',
            'storm_surge_frequency',
            'coastal_flooding_occurrences',
            'drought_impacts',
            'el_nino_la_nina_indices',
            'north_atlantic_oscillation'
        ],  
        'description': 'Storm intensification, extreme sea levels, climate oscillations'
    }
}

# API to data type mapping - which APIs provide which data types
API_DATA_MAPPING = {
    'copernicus': [
        'temperature_heat', 'sea_level_dynamics', 'salinity_water_cycle', 
        'ocean_chemistry', 'cryosphere_ice', 'biological_ecosystem'
    ],
    'noaa_cops': [
        'temperature_heat', 'sea_level_dynamics', 'extreme_events'
    ],
    'emodnet': [
        'temperature_heat', 'salinity_water_cycle', 'ocean_chemistry'
    ],
    'pangaea': [
        'pollution_human_impacts', 'biological_ecosystem', 'ocean_chemistry'
    ],
    'nasa_ocean': [
        'temperature_heat', 'biological_ecosystem', 'cryosphere_ice'
    ]
}

# Common request parameters
DEFAULT_PARAMS = {
    'spatial_resolution': '0.25_degree',
    'temporal_resolution': 'daily', 
    'output_format': 'json',
    'coordinate_system': 'WGS84',
    'depth_levels': 'surface'  # Most APIs focus on surface data
}

def get_api_config(api_name: str) -> APIEndpoint:
    """Get configuration for a specific API."""
    if api_name not in API_ENDPOINTS:
        raise ValueError(f"Unknown API: {api_name}. Available: {list(API_ENDPOINTS.keys())}")
    return API_ENDPOINTS[api_name]

def get_apis_for_data_type(data_type: str) -> list:
    """Get list of APIs that provide a specific data type."""
    apis = []
    for api_name, data_types in API_DATA_MAPPING.items():
        if data_type in data_types:
            apis.append(api_name)
    return apis

def get_data_types_for_api(api_name: str) -> list:
    """Get list of data types available from a specific API."""
    return API_DATA_MAPPING.get(api_name, [])