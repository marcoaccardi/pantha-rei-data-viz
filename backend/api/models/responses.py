"""
Pydantic models for API responses.

Defines the structure of all API response objects to ensure consistent
data formatting and automatic API documentation generation.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

class Coordinates(BaseModel):
    """Geographic coordinates."""
    lat: float = Field(..., description="Latitude in degrees", ge=-90, le=90)
    lon: float = Field(..., description="Longitude in degrees", ge=-180, le=180)

class DataValue(BaseModel):
    """Individual data value with metadata."""
    value: Optional[Union[float, str]] = Field(None, description="Data value (numeric or categorical)")
    units: str = Field(..., description="Units of measurement")
    long_name: str = Field(..., description="Descriptive name of the variable")
    valid: bool = Field(..., description="Whether the value is valid (not NaN)")

class PointDataResponse(BaseModel):
    """Response for single point data extraction."""
    dataset: str = Field(..., description="Dataset name")
    location: Coordinates = Field(..., description="Requested coordinates")
    actual_location: Coordinates = Field(..., description="Actual grid coordinates used")
    date: str = Field(..., description="Date of the data (YYYY-MM-DD)")
    data: Dict[str, DataValue] = Field(..., description="Extracted data variables")
    extraction_time_ms: float = Field(..., description="Time taken for data extraction in milliseconds")
    file_source: str = Field(..., description="Source file path")

class MultiDatasetResponse(BaseModel):
    """Response for multi-dataset point extraction."""
    location: Coordinates = Field(..., description="Requested coordinates")
    date: str = Field(..., description="Date of the data (YYYY-MM-DD)")
    datasets: Dict[str, Union[PointDataResponse, Dict[str, Any]]] = Field(..., description="Data from each dataset")
    total_extraction_time_ms: float = Field(..., description="Total time for all extractions")

class DatasetInfo(BaseModel):
    """Information about an available dataset."""
    name: str = Field(..., description="Human-readable dataset name")
    description: str = Field(..., description="Dataset description")
    variables: List[str] = Field(..., description="Available variables")
    temporal_coverage: Dict[str, str] = Field(..., description="Date range coverage")
    spatial_resolution: str = Field(..., description="Spatial resolution description")
    file_count: int = Field(..., description="Number of available files")
    latest_date: Optional[str] = Field(None, description="Most recent date available")

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Health status: healthy/unhealthy")
    message: str = Field(..., description="Health status message")
    datasets_available: List[str] = Field(..., description="List of available datasets")
    total_files: int = Field(..., description="Total number of data files available")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Health check timestamp")

class ErrorResponse(BaseModel):
    """Error response."""
    error: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Error timestamp")