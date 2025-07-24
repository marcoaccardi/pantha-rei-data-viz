#!/usr/bin/env python3
"""
Texture validation utilities for NOAA Climate Data System.
"""

import os
import numpy as np
from PIL import Image
from typing import Dict, Any, Optional
from pathlib import Path

from ..models.texture_specs import ValidationResult, TextureSpecs
import config

class TextureValidator:
    """Validate texture quality and React Three Fiber compatibility."""
    
    def __init__(self):
        """Initialize texture validator."""
        self.specs = config.TEXTURE_SPECS
    
    def validate_texture(self, file_path: str) -> ValidationResult:
        """
        Comprehensive texture validation.
        
        Args:
            file_path: Path to texture file
            
        Returns:
            ValidationResult with detailed validation information
        """
        result = ValidationResult(
            file_exists=False,
            dimensions=None,
            aspect_ratio=0.0,
            suitable_for_globe=False,
            file_size_mb=0.0,
            format=None,
            has_transparency=False,
            validation_errors=[],
            validation_warnings=[]
        )
        
        try:
            # Check file existence
            if not os.path.exists(file_path):
                result.add_error(f"File does not exist: {file_path}")
                return result
            
            result.file_exists = True
            result.file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            
            # Validate image
            with Image.open(file_path) as img:
                width, height = img.size
                result.dimensions = (width, height)
                result.aspect_ratio = width / height
                result.format = img.format
                result.has_transparency = img.mode in ('RGBA', 'LA')
                
                # Validate React Three Fiber requirements
                self._validate_globe_requirements(result)
                
                # Validate file size
                self._validate_file_size(result)
                
                # Validate content quality
                self._validate_content_quality(result, img)
                
        except Exception as e:
            result.add_error(f"Failed to validate texture: {str(e)}")
        
        return result
    
    def _validate_globe_requirements(self, result: ValidationResult):
        """Validate React Three Fiber globe requirements."""
        
        # Check aspect ratio
        if abs(result.aspect_ratio - 2.0) > 0.05:
            result.add_error(f"Invalid aspect ratio: {result.aspect_ratio:.3f} (required: 2:1)")
        
        # Check minimum size
        if result.dimensions:
            width, height = result.dimensions
            if width < self.specs['min_width'] or height < self.specs['min_height']:
                result.add_error(f"Size too small: {width}x{height} (min: {self.specs['min_width']}x{self.specs['min_height']})")
        
        # Check format compatibility
        if result.format not in config.SYSTEM_CONFIG['supported_formats']:
            result.add_error(f"Unsupported format: {result.format}")
        
        # Set globe suitability
        result.suitable_for_globe = len(result.validation_errors) == 0
    
    def _validate_file_size(self, result: ValidationResult):
        """Validate file size for web optimization."""
        
        max_size = self.specs['max_file_size_mb']
        if result.file_size_mb > max_size:
            result.add_warning(f"Large file size: {result.file_size_mb:.1f}MB (recommended: <{max_size}MB)")
        
        if result.file_size_mb < 0.1:
            result.add_warning("Very small file size may indicate low quality")
    
    def _validate_content_quality(self, result: ValidationResult, img: Image.Image):
        """Validate texture content quality."""
        
        try:
            img_array = np.array(img)
            
            if len(img_array.shape) >= 3:
                # Check for realistic color distribution
                self._check_color_distribution(result, img_array)
                
                # Check for proper land/ocean distribution
                self._check_land_ocean_ratio(result, img_array)
                
        except Exception as e:
            result.add_warning(f"Content analysis failed: {str(e)}")
    
    def _check_color_distribution(self, result: ValidationResult, img_array: np.ndarray):
        """Check for realistic color distribution."""
        
        # Calculate basic color statistics
        if len(img_array.shape) >= 3:
            blue_channel = img_array[:, :, 2]
            green_channel = img_array[:, :, 1]
            red_channel = img_array[:, :, 0]
            
            avg_blue = np.mean(blue_channel)
            avg_green = np.mean(green_channel)
            avg_red = np.mean(red_channel)
            
            # Check for Earth-like colors
            if avg_blue < 50:
                result.add_warning("Low blue content - may lack ocean areas")
            
            if avg_green < 30:
                result.add_warning("Low green content - may lack land vegetation")
    
    def _check_land_ocean_ratio(self, result: ValidationResult, img_array: np.ndarray):
        """Check for realistic land/ocean distribution."""
        
        if len(img_array.shape) >= 3:
            # Detect gray pixels (land areas)
            gray_mask = (
                (img_array[:,:,0] == 128) & 
                (img_array[:,:,1] == 128) & 
                (img_array[:,:,2] == 128)
            )
            
            total_pixels = img_array.shape[0] * img_array.shape[1]
            gray_pixels = np.sum(gray_mask)
            land_percentage = (gray_pixels / total_pixels) * 100
            
            # Earth is ~29% land, ~71% ocean
            if land_percentage < 10:
                result.add_warning(f"Very low land coverage: {land_percentage:.1f}%")
            elif land_percentage > 60:
                result.add_warning(f"Very high land coverage: {land_percentage:.1f}%")
    
    def validate_multiple_textures(self, file_paths: list) -> Dict[str, ValidationResult]:
        """Validate multiple texture files."""
        
        results = {}
        for file_path in file_paths:
            results[file_path] = self.validate_texture(file_path)
        
        return results
    
    def generate_validation_report(self, results: Dict[str, ValidationResult]) -> str:
        """Generate comprehensive validation report."""
        
        report = []
        report.append("🧪 TEXTURE VALIDATION REPORT")
        report.append("=" * 50)
        
        total_files = len(results)
        valid_files = sum(1 for r in results.values() if r.is_valid)
        globe_ready = sum(1 for r in results.values() if r.suitable_for_globe)
        
        report.append(f"📊 Summary:")
        report.append(f"   Total files: {total_files}")
        report.append(f"   Valid files: {valid_files}")
        report.append(f"   Globe ready: {globe_ready}")
        report.append(f"   Success rate: {(valid_files/total_files*100):.1f}%")
        
        report.append(f"\n📋 Detailed Results:")
        
        for file_path, result in results.items():
            filename = os.path.basename(file_path)
            status = "✅" if result.is_valid else "❌"
            globe_status = "🌐" if result.suitable_for_globe else "⚠️"
            
            report.append(f"\n{status} {filename}")
            
            if result.dimensions:
                width, height = result.dimensions
                report.append(f"   📐 {width}x{height} (ratio: {result.aspect_ratio:.3f})")
            
            report.append(f"   💾 {result.file_size_mb:.1f}MB")
            report.append(f"   {globe_status} Globe ready: {result.suitable_for_globe}")
            
            if result.validation_errors:
                report.append(f"   ❌ Errors:")
                for error in result.validation_errors:
                    report.append(f"      • {error}")
            
            if result.validation_warnings:
                report.append(f"   ⚠️ Warnings:")
                for warning in result.validation_warnings:
                    report.append(f"      • {warning}")
        
        return "\n".join(report)