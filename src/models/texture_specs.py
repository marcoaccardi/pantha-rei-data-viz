#!/usr/bin/env python3
"""
Data models and specifications for texture processing.
"""

from dataclasses import dataclass
from typing import Tuple, Optional, Dict, Any
from pathlib import Path

@dataclass
class TextureSpecs:
    """Specifications for texture generation and validation."""
    
    width: int
    height: int
    aspect_ratio: float
    format: str
    file_size_mb: float
    has_transparency: bool
    suitable_for_globe: bool
    
    @property
    def dimensions(self) -> Tuple[int, int]:
        """Get texture dimensions as tuple."""
        return (self.width, self.height)
    
    @property
    def is_2_to_1_ratio(self) -> bool:
        """Check if texture has perfect 2:1 aspect ratio."""
        return abs(self.aspect_ratio - 2.0) < 0.05
    
    @property
    def meets_min_size(self) -> bool:
        """Check if texture meets minimum size requirements."""
        return self.width >= 1024 and self.height >= 512
    
    @property
    def is_web_optimized(self) -> bool:
        """Check if file size is web-optimized."""
        return self.file_size_mb < 50

@dataclass
class ValidationResult:
    """Result of texture validation."""
    
    file_exists: bool
    dimensions: Optional[Tuple[int, int]]
    aspect_ratio: float
    suitable_for_globe: bool
    file_size_mb: float
    format: Optional[str]
    has_transparency: bool
    validation_errors: list
    validation_warnings: list
    
    @property
    def is_valid(self) -> bool:
        """Check if validation passed without errors."""
        return len(self.validation_errors) == 0
    
    @property
    def has_warnings(self) -> bool:
        """Check if validation has warnings."""
        return len(self.validation_warnings) > 0
    
    def add_error(self, error: str):
        """Add validation error."""
        self.validation_errors.append(error)
    
    def add_warning(self, warning: str):
        """Add validation warning."""
        self.validation_warnings.append(warning)

@dataclass 
class ProcessingStatus:
    """Status tracking for processing operations."""
    
    stage: str
    progress: float
    current_file: Optional[str]
    files_processed: int
    total_files: int
    errors: list
    warnings: list
    
    @property
    def completion_percentage(self) -> float:
        """Get completion percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.files_processed / self.total_files) * 100
    
    @property
    def has_errors(self) -> bool:
        """Check if processing has errors."""
        return len(self.errors) > 0

@dataclass
class DataSource:
    """Configuration for data sources."""
    
    name: str
    url: str
    description: str
    format: str
    resolution: Optional[str]
    update_frequency: str
    requires_auth: bool = False
    
    @property
    def is_accessible(self) -> bool:
        """Check if data source is accessible."""
        # This would implement actual connectivity check
        return True

@dataclass
class StationData:
    """Station measurement data model."""
    
    station_id: str
    station_name: str
    latitude: float
    longitude: float
    measurements: Dict[str, Any]
    timestamp: str
    source: str
    
    @property
    def coordinates(self) -> Tuple[float, float]:
        """Get station coordinates."""
        return (self.latitude, self.longitude)
    
    @property
    def has_temperature_data(self) -> bool:
        """Check if station has temperature measurements."""
        return 'water_temperature' in self.measurements