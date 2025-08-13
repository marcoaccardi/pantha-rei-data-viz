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
            if hasattr(self, 'lat_size') and hasattr(self, 'lon_size'):
                logger.info(f"✅ Coordinate grid loaded for {self.dataset}: {self.lat_size} lat x {self.lon_size} lon (optimized)")
            elif self.lats is not None and self.lons is not None:
                logger.info(f"✅ Coordinate grid loaded for {self.dataset}: {len(self.lats)} lat x {len(self.lons)} lon")
            else:
                logger.info(f"✅ Coordinate grid loaded for {self.dataset} (bounds-only mode)")
        except Exception as e:
            logger.error(f"❌ Failed to load coordinate grid for {self.dataset}: {e}")
            # Set loaded to False so we don't try to use broken grid
            self.loaded = False
            
    def _load_coordinates(self):
        """Synchronously load coordinate arrays with optimization for large datasets."""
        # Check file size for optimization strategy
        file_size_mb = self.file_path.stat().st_size / (1024 * 1024)
        
        if file_size_mb > 100:  # Large files need chunked loading
            with xr.open_dataset(self.file_path, chunks='auto', decode_cf=False, cache=True, lock=False) as ds:
                self._process_coordinate_data(ds)
        else:
            with xr.open_dataset(self.file_path, cache=True, lock=False) as ds:
                self._process_coordinate_data(ds)
                
    def _process_coordinate_data(self, ds):
        """Process coordinate data from the dataset."""
        # Determine coordinate names
        lat_coord = 'latitude' if 'latitude' in ds.coords else 'lat'
        lon_coord = 'longitude' if 'longitude' in ds.coords else 'lon'
        
        # Check dataset size for optimization strategy
        lat_size = ds[lat_coord].size
        lon_size = ds[lon_coord].size
        total_points = lat_size * lon_size
        
        # OPTIMIZATION: For large datasets (>500K points), use ultra-fast coordinate indexing
        if total_points > 500_000:
            logger.info(f"🚀 ULTRA-FAST OPTIMIZATION: {self.dataset} has {total_points:,} points, using minimal coordinate loading")
            # ULTRA-OPTIMIZATION: Load only coordinate bounds, not full arrays
            self.is_large_dataset = True
            
            # For very large files (like currents), use even faster approach - just use coordinate metadata
            if total_points > 5_000_000:  # > 5M points (like currents with 8M+ points)
                logger.info(f"🚀 ULTRA-LARGE FILE: {self.dataset} has {total_points:,} points, using metadata-only loading")
                # Use coordinate attributes if available, much faster than min/max computation
                if 'actual_range' in ds[lat_coord].attrs:
                    lat_min, lat_max = float(ds[lat_coord].attrs['actual_range'][0]), float(ds[lat_coord].attrs['actual_range'][1])
                else:
                    # Fallback to first/last values for regularly spaced coordinates
                    lat_vals = ds[lat_coord].values
                    lat_min, lat_max = float(lat_vals[0]), float(lat_vals[-1])
                
                if 'actual_range' in ds[lon_coord].attrs:
                    lon_min, lon_max = float(ds[lon_coord].attrs['actual_range'][0]), float(ds[lon_coord].attrs['actual_range'][1])
                else:
                    lon_vals = ds[lon_coord].values
                    lon_min, lon_max = float(lon_vals[0]), float(lon_vals[-1])
            else:
                # Get min/max without loading full arrays for moderately large files
                lat_min = float(ds[lat_coord].min().values)
                lat_max = float(ds[lat_coord].max().values)
                lon_min = float(ds[lon_coord].min().values)
                lon_max = float(ds[lon_coord].max().values)
            
            self.lat_min, self.lat_max = lat_min, lat_max
            self.lon_min, self.lon_max = lon_min, lon_max
            
            # Calculate step sizes from dataset attributes or first few values
            self.lat_step = (lat_max - lat_min) / (lat_size - 1) if lat_size > 1 else 1.0
            self.lon_step = (lon_max - lon_min) / (lon_size - 1) if lon_size > 1 else 1.0
            
            # Store only array shapes for index calculations  
            self.lat_size = lat_size
            self.lon_size = lon_size
            
            # Don't load full coordinate arrays for ultra-large datasets
            self.lats = None  # Will be computed on demand
            self.lons = None  # Will be computed on demand
            
            logger.info(f"⚡ ULTRA-FAST: Loaded only bounds for {self.dataset}: lat({lat_min:.2f} to {lat_max:.2f}) lon({lon_min:.2f} to {lon_max:.2f})")
        else:
            # Standard loading for smaller datasets
            self.lats = ds[lat_coord].values
            self.lons = ds[lon_coord].values
            self.is_large_dataset = False
        
        # Pre-calculate indices for common coordinate ranges
        if self.lats is not None and self.lons is not None:
            self.lat_indices = np.arange(len(self.lats))
            self.lon_indices = np.arange(len(self.lons))
        elif hasattr(self, 'lat_size') and hasattr(self, 'lon_size'):
            self.lat_indices = np.arange(self.lat_size)  
            self.lon_indices = np.arange(self.lon_size)
        else:
            self.lat_indices = None
            self.lon_indices = None
    
    def find_nearest_indices(self, lat: float, lon: float) -> Tuple[int, int, float, float]:
        """Find nearest grid indices quickly using optimized methods."""
        if not self.loaded:
            raise RuntimeError(f"Coordinate grid not loaded for {self.dataset}")
        
        # OPTIMIZATION: For large datasets, use mathematical calculation instead of array search
        if hasattr(self, 'is_large_dataset') and self.is_large_dataset:
            # Mathematical index calculation (much faster than array search)
            lat_idx = int(round((lat - self.lat_min) / self.lat_step)) if hasattr(self, 'lat_step') else 0
            lon_idx = int(round((lon - self.lon_min) / self.lon_step)) if hasattr(self, 'lon_step') else 0
            
            # Clamp to valid range using stored sizes
            if hasattr(self, 'lat_size'):
                lat_idx = max(0, min(lat_idx, self.lat_size - 1))
            elif self.lats is not None:
                lat_idx = max(0, min(lat_idx, len(self.lats) - 1))
                
            if hasattr(self, 'lon_size'):  
                lon_idx = max(0, min(lon_idx, self.lon_size - 1))
            elif self.lons is not None:
                lon_idx = max(0, min(lon_idx, len(self.lons) - 1))
            
            # Calculate actual coordinates mathematically (no array lookup needed!)
            actual_lat = float(self.lat_min + lat_idx * self.lat_step)
            actual_lon = float(self.lon_min + lon_idx * self.lon_step)
            
            return lat_idx, lon_idx, actual_lat, actual_lon
        else:
            # Standard numpy argmin for smaller datasets
            lat_idx = np.argmin(np.abs(self.lats - lat))
            lon_idx = np.argmin(np.abs(self.lons - lon))
            
            actual_lat = float(self.lats[lat_idx])
            actual_lon = float(self.lons[lon_idx])
            
            return lat_idx, lon_idx, actual_lat, actual_lon

class SmartFileManager:
    """Manages NetCDF file handles with intelligent caching."""
    
    def __init__(self, max_open_files: int = 5, max_coordinate_grids: int = 10):
        self.max_open_files = max_open_files
        self.max_coordinate_grids = max_coordinate_grids  # Limit coordinate grid cache
        self.open_files: Dict[str, xr.Dataset] = {}
        self.file_access_times: Dict[str, float] = {}
        self.coordinate_grids: Dict[str, CoordinateGrid] = {}
        self.grid_access_times: Dict[str, float] = {}  # Track grid access for LRU
        
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
        
        # Open new file with optimization
        logger.info(f"📂 Opening NetCDF file: {file_path.name}")
        try:
            # Check file size for optimization strategy
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            
            if file_size_mb > 100:  # Large files (>100MB) need chunking
                logger.info(f"🚀 Large file detected ({file_size_mb:.1f}MB), using chunked loading")
                ds = xr.open_dataset(
                    file_path, 
                    chunks='auto',      # Enable chunking for large files
                    decode_cf=False,    # Skip decoding for faster loading
                    cache=True,         # Enable caching
                    lock=False          # Disable locking for better performance
                )
            else:
                # Smaller files can be loaded normally but with optimizations
                ds = xr.open_dataset(
                    file_path,
                    cache=True,         # Enable caching
                    lock=False          # Disable locking for better performance
                )
                
            self.open_files[file_key] = ds
            self.file_access_times[file_key] = current_time
            
            # Pre-load coordinate grid for spatial indexing with memory limits
            if file_key not in self.coordinate_grids:
                # Check if we need to evict old coordinate grids
                if len(self.coordinate_grids) >= self.max_coordinate_grids:
                    await self._evict_oldest_grid()
                
                # Skip coordinate grid loading for very large files to prevent blocking
                if file_size_mb > 200:  # Skip grid loading for files > 200MB
                    logger.info(f"⚡ ULTRA-LARGE FILE: Skipping coordinate grid pre-loading for {file_path.name} ({file_size_mb:.1f}MB)")
                    # Create a minimal grid that will load on-demand
                    grid = CoordinateGrid(dataset_name, file_path)
                    grid.loaded = False  # Will load on first access
                    self.coordinate_grids[file_key] = grid
                    self.grid_access_times[file_key] = current_time
                else:
                    grid = CoordinateGrid(dataset_name, file_path)
                    await grid.load()
                    if grid.loaded:  # Only cache if loading succeeded
                        self.coordinate_grids[file_key] = grid
                        self.grid_access_times[file_key] = current_time
            
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
    
    async def _evict_oldest_grid(self):
        """Remove least recently used coordinate grid from cache."""
        if not self.coordinate_grids:
            return
            
        oldest_key = min(self.grid_access_times.keys(), key=lambda k: self.grid_access_times[k])
        logger.info(f"🗑️ Evicting old coordinate grid: {Path(oldest_key).name}")
        
        del self.coordinate_grids[oldest_key]
        del self.grid_access_times[oldest_key]
    
    def get_coordinate_grid(self, file_path: Path) -> Optional[CoordinateGrid]:
        """Get pre-loaded coordinate grid for fast spatial lookups."""
        file_key = str(file_path)
        grid = self.coordinate_grids.get(file_key)
        if grid and file_key in self.grid_access_times:
            # Update access time for LRU
            self.grid_access_times[file_key] = time.time()
        return grid
    
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
        
        # Dataset-specific cache TTL optimization
        self.dataset_cache_ttl = {
            'sst': 1800,  # 30 minutes for SST (changes frequently) 
            'acidity_current': 7200,  # 2 hours for current acidity (daily updates)
            'acidity_historical': 86400,  # 24 hours for historical acidity (static data)
            'acidity': 7200,  # 2 hours for generic acidity requests
            'currents': 1800,  # 30 minutes for currents (changes frequently)
            'microplastics': 86400  # 24 hours for microplastics (static data)
        }
        
    async def get_cached_point(self, dataset: str, lat: float, lon: float, date: str) -> Optional[CachedPoint]:
        """Get point data from cache if available and not expired (with dataset-specific TTL)."""
        cache_key = CacheKey(dataset, lat, lon, date)
        current_time = time.time()
        
        if cache_key in self.point_cache:
            cached_point = self.point_cache[cache_key]
            
            # Use dataset-specific TTL for more efficient caching
            dataset_ttl = self.dataset_cache_ttl.get(dataset, self.cache_ttl)
            
            # Check if cache entry is still valid
            if current_time - cached_point.timestamp < dataset_ttl:
                self.cache_hits += 1
                logger.debug(f"🎯 Cache HIT for {dataset} at ({lat}, {lon}) [TTL: {dataset_ttl}s]")
                return cached_point
            else:
                # Expired - remove from cache
                logger.debug(f"⏱️ Cache EXPIRED for {dataset} at ({lat}, {lon}) after {dataset_ttl}s")
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
        
        if not grid:
            raise RuntimeError(f"Coordinate grid not available for {dataset_name}")
        
        # For large files where grid loading was skipped, load on-demand
        if not grid.loaded:
            logger.info(f"⚡ Loading coordinate grid on-demand for {dataset_name}")
            await grid.load()
            if not grid.loaded:
                raise RuntimeError(f"Failed to load coordinate grid for {dataset_name}")
        
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