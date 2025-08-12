#!/usr/bin/env python3
"""
Texture Service Module

Provides texture management and serving functionality for ocean data visualization.
Serves texture files from the ocean-data/textures directory via API endpoints.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from fastapi import HTTPException
from fastapi.responses import FileResponse
import logging

logger = logging.getLogger(__name__)

class TextureService:
    """Service for managing and serving ocean data textures."""
    
    def __init__(self, texture_base_path: str = "../ocean-data/textures"):
        """Initialize texture service with base path to textures directory."""
        self.texture_base_path = Path(texture_base_path)
        self.supported_categories = ["sst"]
        self.supported_resolutions = ["preview", "low", "medium", "high", "ultra"]
        
        # Verify texture directory exists
        if not self.texture_base_path.exists():
            logger.error(f"Texture directory not found: {self.texture_base_path}")
            raise ValueError(f"Texture directory not found: {self.texture_base_path}")
    
    def get_available_textures(self) -> Dict[str, Dict[str, List[str]]]:
        """
        Get all available textures organized by category and date.
        
        Returns:
            Dict with structure: {category: {date: [resolutions]}}
        """
        available = {}
        
        for category in self.supported_categories:
            category_path = self.texture_base_path / category
            available[category] = {}
            
            if category_path.exists():
                # Scan for texture files
                for texture_file in category_path.rglob("*.png"):
                    # Extract date and resolution from filename
                    # Expected formats: 
                    # - Legacy: {category}_texture_YYYYMMDD_{resolution}.png
                    # - New ERDDAP: SST_YYYYMMDD.png
                    filename = texture_file.stem
                    parts = filename.split('_')
                    
                    # Handle new ERDDAP format (SST_YYYYMMDD)
                    if category == "sst" and len(parts) == 2 and parts[0].upper() == "SST":
                        try:
                            date_str = parts[1]  # YYYYMMDD
                            if len(date_str) == 8:
                                formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                                
                                if formatted_date not in available[category]:
                                    available[category][formatted_date] = []
                                
                                # ERDDAP textures are ultra-high resolution
                                if "ultra" not in available[category][formatted_date]:
                                    available[category][formatted_date].append("ultra")
                        except (IndexError, ValueError) as e:
                            logger.warning(f"Could not parse ERDDAP texture filename: {filename} - {e}")
                    
                    # Handle legacy format
                    elif len(parts) >= 4:
                        try:
                            # Extract date (YYYYMMDD format)
                            date_str = parts[2]  # Should be YYYYMMDD
                            resolution = parts[3] if len(parts) > 3 else "medium"
                            
                            # Convert YYYYMMDD to YYYY-MM-DD for consistency
                            if len(date_str) == 8:
                                formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                                
                                if formatted_date not in available[category]:
                                    available[category][formatted_date] = []
                                
                                if resolution not in available[category][formatted_date]:
                                    available[category][formatted_date].append(resolution)
                        except (IndexError, ValueError) as e:
                            logger.warning(f"Could not parse texture filename: {filename} - {e}")
        
        return available
    
    def find_best_texture(self, category: str, date: Optional[str] = None, resolution: str = "medium") -> Optional[Path]:
        """
        Find the best available texture for given parameters with intelligent fallback.
        
        Args:
            category: Data category (sst, acidity, currents, waves)
            date: Preferred date in YYYY-MM-DD format
            resolution: Preferred resolution (preview, low, medium, high)
            
        Returns:
            Path to best available texture file or None if not found
        """
        if category not in self.supported_categories:
            logger.warning(f"Unsupported category: {category}")
            return None
        
        category_path = self.texture_base_path / category
        if not category_path.exists():
            logger.warning(f"Category directory not found: {category_path}")
            return None
        
        # Get all available textures for this category
        available = self.get_available_textures().get(category, {})
        
        if not available:
            logger.warning(f"No textures available for category: {category}")
            return None
        
        # Strategy 1: Exact match (preferred date and resolution)
        if date and date in available:
            date_str = date.replace('-', '')  # Convert to YYYYMMDD
            year = date[:4]
            
            # Special handling for SST ERDDAP textures (ultra resolution)
            if category == "sst" and "ultra" in available[date]:
                # Try ERDDAP format with year subdirectory
                texture_file = category_path / year / f"SST_{date_str}.png"
                if texture_file.exists():
                    logger.info(f"Found ERDDAP SST texture with year dir: {texture_file}")
                    return texture_file
                    
                # Try ERDDAP format without year subdirectory
                texture_file = category_path / f"SST_{date_str}.png"
                if texture_file.exists():
                    logger.info(f"Found ERDDAP SST texture without year dir: {texture_file}")
                    return texture_file
            
            # Standard format handling
            if resolution in available[date]:
                # Try with year subdirectory first
                texture_file = category_path / year / f"{category}_texture_{date_str}_{resolution}.png"
                if texture_file.exists():
                    logger.info(f"Found exact match with year dir: {texture_file}")
                    return texture_file
                    
                # Try without year subdirectory
                texture_file = category_path / f"{category}_texture_{date_str}_{resolution}.png"
                if texture_file.exists():
                    logger.info(f"Found exact match without year dir: {texture_file}")
                    return texture_file
        
        # Strategy 2: Same date, different resolution
        if date and date in available:
            date_str = date.replace('-', '')  # Convert to YYYYMMDD
            year = date[:4]
            
            # Check for ultra resolution (ERDDAP SST) first
            if "ultra" in available[date] and category == "sst":
                # Try ERDDAP format
                texture_file = category_path / year / f"SST_{date_str}.png"
                if texture_file.exists():
                    logger.info(f"Found ERDDAP SST texture (ultra resolution) with year dir: {texture_file}")
                    return texture_file
                    
                texture_file = category_path / f"SST_{date_str}.png"
                if texture_file.exists():
                    logger.info(f"Found ERDDAP SST texture (ultra resolution) without year dir: {texture_file}")
                    return texture_file
            
            # Check standard resolutions
            for alt_resolution in self.supported_resolutions:
                if alt_resolution in available[date]:
                    # Try with year subdirectory
                    texture_file = category_path / year / f"{category}_texture_{date_str}_{alt_resolution}.png"
                    if texture_file.exists():
                        logger.info(f"Found same date, different resolution with year dir: {texture_file}")
                        return texture_file
                        
                    # Try without year subdirectory
                    texture_file = category_path / f"{category}_texture_{date_str}_{alt_resolution}.png"
                    if texture_file.exists():
                        logger.info(f"Found same date, different resolution without year dir: {texture_file}")
                        return texture_file
        
        # Strategy 3: Different date, same/similar resolution
        for alt_date in sorted(available.keys(), reverse=True):  # Most recent first
            date_str = alt_date.replace('-', '')  # Convert to YYYYMMDD
            year = alt_date[:4]
            
            # For SST, prefer ultra resolution (ERDDAP) over requested resolution
            if category == "sst" and "ultra" in available[alt_date]:
                texture_file = category_path / year / f"SST_{date_str}.png"
                if texture_file.exists():
                    logger.info(f"Found ERDDAP SST texture for different date with year dir: {texture_file}")
                    return texture_file
                    
                texture_file = category_path / f"SST_{date_str}.png"
                if texture_file.exists():
                    logger.info(f"Found ERDDAP SST texture for different date without year dir: {texture_file}")
                    return texture_file
            
            # Check requested resolution
            if resolution in available[alt_date]:
                # Try with year subdirectory
                texture_file = category_path / year / f"{category}_texture_{date_str}_{resolution}.png"
                if texture_file.exists():
                    logger.info(f"Found different date, same resolution with year dir: {texture_file}")
                    return texture_file
                    
                # Try without year subdirectory
                texture_file = category_path / f"{category}_texture_{date_str}_{resolution}.png"
                if texture_file.exists():
                    logger.info(f"Found different date, same resolution without year dir: {texture_file}")
                    return texture_file
        
        # Strategy 4: Any available texture for this category
        for alt_date in sorted(available.keys(), reverse=True):  # Most recent first
            for alt_resolution in available[alt_date]:
                date_str = alt_date.replace('-', '')  # Convert to YYYYMMDD
                year = alt_date[:4]
                
                # Handle ERDDAP SST format
                if category == "sst" and alt_resolution == "ultra":
                    texture_file = category_path / year / f"SST_{date_str}.png"
                    if texture_file.exists():
                        logger.info(f"Found fallback ERDDAP SST texture with year dir: {texture_file}")
                        return texture_file
                        
                    texture_file = category_path / f"SST_{date_str}.png"
                    if texture_file.exists():
                        logger.info(f"Found fallback ERDDAP SST texture without year dir: {texture_file}")
                        return texture_file
                else:
                    # Try standard format with year subdirectory
                    texture_file = category_path / year / f"{category}_texture_{date_str}_{alt_resolution}.png"
                    if texture_file.exists():
                        logger.info(f"Found fallback texture with year dir: {texture_file}")
                        return texture_file
                        
                    # Try without year subdirectory
                    texture_file = category_path / f"{category}_texture_{date_str}_{alt_resolution}.png"
                    if texture_file.exists():
                        logger.info(f"Found fallback texture without year dir: {texture_file}")
                        return texture_file
        
        logger.warning(f"No texture found for category: {category}")
        return None
    
    def get_texture_metadata(self, texture_path: Path) -> Dict[str, str]:
        """
        Extract metadata from texture file path.
        
        Args:
            texture_path: Path to texture file
            
        Returns:
            Dictionary with texture metadata
        """
        filename = texture_path.stem
        parts = filename.split('_')
        
        # Handle ERDDAP SST format (SST_YYYYMMDD)
        if len(parts) == 2 and parts[0].upper() == "SST":
            date_str = parts[1]  # YYYYMMDD
            
            # Convert YYYYMMDD to YYYY-MM-DD
            if len(date_str) == 8:
                formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            else:
                formatted_date = date_str
            
            return {
                "category": "sst",
                "date": formatted_date,
                "resolution": "ultra",  # ERDDAP textures are ultra-high resolution
                "filename": texture_path.name,
                "size": texture_path.stat().st_size if texture_path.exists() else 0
            }
        
        # Handle standard format ({category}_texture_YYYYMMDD_{resolution})
        elif len(parts) >= 4:
            category = parts[0]
            date_str = parts[2]  # YYYYMMDD
            resolution = parts[3]
            
            # Convert YYYYMMDD to YYYY-MM-DD
            if len(date_str) == 8:
                formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            else:
                formatted_date = date_str
            
            return {
                "category": category,
                "date": formatted_date,
                "resolution": resolution,
                "filename": texture_path.name,
                "size": texture_path.stat().st_size if texture_path.exists() else 0
            }
        
        return {
            "category": "unknown",
            "date": "unknown",
            "resolution": "unknown",
            "filename": texture_path.name,
            "size": texture_path.stat().st_size if texture_path.exists() else 0
        }
    
    def serve_texture(self, category: str, date: Optional[str] = None, resolution: str = "medium") -> FileResponse:
        """
        Serve texture file with proper headers and caching.
        
        Args:
            category: Data category
            date: Optional date in YYYY-MM-DD format
            resolution: Texture resolution
            
        Returns:
            FileResponse with texture image
            
        Raises:
            HTTPException: If texture not found
        """
        texture_path = self.find_best_texture(category, date, resolution)
        
        if not texture_path or not texture_path.exists():
            raise HTTPException(
                status_code=404, 
                detail=f"Texture not found for category: {category}, date: {date}, resolution: {resolution}"
            )
        
        # Get metadata for response headers
        metadata = self.get_texture_metadata(texture_path)
        
        # Prepare response headers - DISABLE CACHING for development
        headers = {
            "Cache-Control": "no-cache, no-store, must-revalidate",  # Disable caching
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Texture-Category": metadata["category"],
            "X-Texture-Date": metadata["date"],
            "X-Texture-Resolution": metadata["resolution"]
        }
        
        logger.info(f"Serving texture: {texture_path}")
        
        return FileResponse(
            path=str(texture_path),
            media_type="image/png",
            headers=headers
        )
    
    def get_texture_summary(self) -> Dict[str, any]:
        """
        Get summary of all available textures.
        
        Returns:
            Summary dictionary with counts and availability
        """
        available = self.get_available_textures()
        
        summary = {
            "total_categories": len([cat for cat in available.keys() if available[cat]]),
            "categories": {},
            "total_textures": 0
        }
        
        for category, dates in available.items():
            if dates:  # Only include categories with textures
                texture_count = sum(len(resolutions) for resolutions in dates.values())
                summary["categories"][category] = {
                    "dates_available": len(dates),
                    "texture_count": texture_count,
                    "latest_date": max(dates.keys()) if dates else None,
                    "available_resolutions": list(set(
                        res for resolutions in dates.values() for res in resolutions
                    ))
                }
                summary["total_textures"] += texture_count
        
        return summary


# Global texture service instance
texture_service = TextureService()