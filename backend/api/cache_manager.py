"""
High-Performance Cache Manager for Ocean Data API

Implements multi-layered caching to dramatically speed up data access:
1. Memory cache for frequently accessed points
2. Pre-loaded coordinate grids for spatial indexing
3. Smart file handle management
"""

import asyncio
import time
import json
import hashlib
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass, asdict
from pathlib import Path
import logging
import xarray as xr
import numpy as np
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

@dataclass
class CacheKey:
    """Cache key for point data requests."""
    dataset: str
    lat: float
    lon: float
    date: str
    
    def __hash__(self):
        # Round coordinates to reduce cache misses for nearby points
        lat_rounded = round(self.lat, 2)  # ~1km precision
        lon_rounded = round(self.lon, 2)
        return hash((self.dataset, lat_rounded, lon_rounded, self.date))

@dataclass 
class CachedPoint:
    """Cached point data with metadata."""
    data: Dict[str, Any]
    timestamp: float
    extraction_time_ms: float
    actual_location: Tuple[float, float]

class CoordinateGrid:
    """Pre-loaded coordinate grid for fast spatial lookups."""
    
    def __init__(self, dataset: str, file_path: Path):
        self.dataset = dataset
        self.file_path = file_path
        self.lats = None
        self.lons = None
        self.lat_indices = None
        self.lon_indices = None
        self.loaded = False
        
    async def load(self):
        """Load coordinate arrays for fast spatial indexing."""
        if self.loaded:
            return
            
        try:
            logger.info(f"📍 Loading coordinate grid for {self.dataset}")
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
                await loop.run_in_executor(executor, self._load_coordinates)
            self.loaded = True
            logger.info(f"✅ Coordinate grid loaded for {self.dataset}: {len(self.lats)} lat x {len(self.lons)} lon")
        except Exception as e:
            logger.error(f"❌ Failed to load coordinate grid for {self.dataset}: {e}")
            
    def _load_coordinates(self):
        """Synchronously load coordinate arrays."""
        with xr.open_dataset(self.file_path) as ds:
            # Determine coordinate names
            lat_coord = 'latitude' if 'latitude' in ds.coords else 'lat'
            lon_coord = 'longitude' if 'longitude' in ds.coords else 'lon'
            
            # Load coordinate arrays
            self.lats = ds[lat_coord].values
            self.lons = ds[lon_coord].values
            
            # Pre-calculate indices for common coordinate ranges
            # Create lookup tables for faster nearest neighbor search
            self.lat_indices = np.arange(len(self.lats))
            self.lon_indices = np.arange(len(self.lons))
    
    def find_nearest_indices(self, lat: float, lon: float) -> Tuple[int, int, float, float]:
        """Find nearest grid indices quickly using pre-loaded arrays."""
        if not self.loaded:
            raise RuntimeError(f"Coordinate grid not loaded for {self.dataset}")
        
        # Use numpy's optimized argmin for fast lookup
        lat_idx = np.argmin(np.abs(self.lats - lat))
        lon_idx = np.argmin(np.abs(self.lons - lon))
        
        actual_lat = float(self.lats[lat_idx])
        actual_lon = float(self.lons[lon_idx])
        
        return lat_idx, lon_idx, actual_lat, actual_lon

class SmartFileManager:
    """Manages NetCDF file handles with intelligent caching."""
    
    def __init__(self, max_open_files: int = 5):
        self.max_open_files = max_open_files
        self.open_files: Dict[str, xr.Dataset] = {}
        self.file_access_times: Dict[str, float] = {}
        self.coordinate_grids: Dict[str, CoordinateGrid] = {}
        
    async def get_dataset(self, file_path: Path, dataset_name: str) -> xr.Dataset:
        """Get dataset with intelligent caching and LRU eviction."""
        file_key = str(file_path)
        current_time = time.time()
        
        # Check if file is already open
        if file_key in self.open_files:
            self.file_access_times[file_key] = current_time
            return self.open_files[file_key]
        
        # Need to open new file - check if we need to close old ones
        if len(self.open_files) >= self.max_open_files:
            await self._evict_oldest_file()
        
        # Open new file
        logger.info(f"📂 Opening NetCDF file: {file_path.name}")
        try:
            ds = xr.open_dataset(file_path)
            self.open_files[file_key] = ds
            self.file_access_times[file_key] = current_time
            
            # Pre-load coordinate grid for spatial indexing
            if file_key not in self.coordinate_grids:
                grid = CoordinateGrid(dataset_name, file_path)
                await grid.load()
                self.coordinate_grids[file_key] = grid
            
            return ds
        except Exception as e:
            logger.error(f"❌ Failed to open {file_path}: {e}")
            raise
    
    async def _evict_oldest_file(self):
        """Remove least recently used file from cache."""
        if not self.open_files:
            return
            
        # Find oldest file
        oldest_key = min(self.file_access_times.keys(), 
                        key=lambda k: self.file_access_times[k])
        
        # Close and remove
        try:
            self.open_files[oldest_key].close()
            logger.info(f"🗑️ Closed old NetCDF file: {Path(oldest_key).name}")
        except Exception as e:
            logger.warning(f"Error closing file {oldest_key}: {e}")
        
        del self.open_files[oldest_key]
        del self.file_access_times[oldest_key]
    
    def get_coordinate_grid(self, file_path: Path) -> Optional[CoordinateGrid]:
        """Get pre-loaded coordinate grid for fast spatial lookups."""
        file_key = str(file_path)
        return self.coordinate_grids.get(file_key)
    
    async def cleanup(self):
        """Close all open files."""
        for ds in self.open_files.values():
            try:
                ds.close()
            except Exception:
                pass
        self.open_files.clear()
        self.file_access_times.clear()
        self.coordinate_grids.clear()

class HighPerformanceCacheManager:
    """Ultra-fast cache manager with multiple optimization layers."""
    
    def __init__(self, cache_size: int = 10000, cache_ttl_seconds: int = 3600):
        self.cache_size = cache_size
        self.cache_ttl = cache_ttl_seconds
        self.point_cache: Dict[CacheKey, CachedPoint] = {}
        self.cache_hits = 0
        self.cache_misses = 0
        self.file_manager = SmartFileManager()
        
        # Performance monitoring
        self.total_requests = 0
        self.total_cache_time = 0
        self.total_extraction_time = 0
        
    async def get_cached_point(self, dataset: str, lat: float, lon: float, date: str) -> Optional[CachedPoint]:
        """Get point data from cache if available and not expired."""
        cache_key = CacheKey(dataset, lat, lon, date)
        current_time = time.time()
        
        if cache_key in self.point_cache:
            cached_point = self.point_cache[cache_key]
            
            # Check if cache entry is still valid
            if current_time - cached_point.timestamp < self.cache_ttl:
                self.cache_hits += 1
                logger.debug(f"🎯 Cache HIT for {dataset} at ({lat}, {lon})")
                return cached_point
            else:
                # Expired - remove from cache
                del self.point_cache[cache_key]
        
        self.cache_misses += 1
        logger.debug(f"💨 Cache MISS for {dataset} at ({lat}, {lon})")
        return None
    
    async def cache_point(self, dataset: str, lat: float, lon: float, date: str, 
                         data: Dict[str, Any], extraction_time_ms: float, 
                         actual_location: Tuple[float, float]):
        """Cache point data with LRU eviction."""
        cache_key = CacheKey(dataset, lat, lon, date)
        current_time = time.time()
        
        # Check cache size limit
        if len(self.point_cache) >= self.cache_size:
            await self._evict_oldest_cache_entry()
        
        # Store in cache
        cached_point = CachedPoint(
            data=data,
            timestamp=current_time,
            extraction_time_ms=extraction_time_ms,
            actual_location=actual_location
        )
        
        self.point_cache[cache_key] = cached_point
        logger.debug(f"💾 Cached point for {dataset} at ({lat}, {lon})")
    
    async def _evict_oldest_cache_entry(self):
        """Remove oldest cache entry."""
        if not self.point_cache:
            return
            
        # Find oldest entry
        oldest_key = min(self.point_cache.keys(), 
                        key=lambda k: self.point_cache[k].timestamp)
        
        del self.point_cache[oldest_key]
        logger.debug(f"🗑️ Evicted old cache entry: {oldest_key.dataset}")
    
    async def get_dataset_with_grid(self, file_path: Path, dataset_name: str) -> Tuple[xr.Dataset, CoordinateGrid]:
        """Get dataset and coordinate grid for ultra-fast spatial lookups."""
        ds = await self.file_manager.get_dataset(file_path, dataset_name)
        grid = self.file_manager.get_coordinate_grid(file_path)
        
        if not grid or not grid.loaded:
            raise RuntimeError(f"Coordinate grid not available for {dataset_name}")
        
        return ds, grid
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate_percent": round(hit_rate, 2),
            "cached_points": len(self.point_cache),
            "open_files": len(self.file_manager.open_files),
            "coordinate_grids": len(self.file_manager.coordinate_grids)
        }
    
    async def cleanup(self):
        """Clean up resources."""
        await self.file_manager.cleanup()
        self.point_cache.clear()

# Global cache manager instance
cache_manager = HighPerformanceCacheManager()