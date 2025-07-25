#!/usr/bin/env python3
"""
Fallback cache manager for API responses without SQLite dependency.
Uses JSON files for caching when SQLite is not available.
"""

import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import os

class FallbackAPIResponseCache:
    """Fallback cache manager using JSON files instead of SQLite."""
    
    def __init__(self, cache_dir: Path):
        """
        Initialize fallback cache manager.
        
        Args:
            cache_dir: Directory to store cache files
        """
        self.logger = logging.getLogger(__name__)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache metadata file
        self.metadata_file = self.cache_dir / 'cache_metadata.json'
        self.metadata = self._load_metadata()
        
        self.logger.info(f"Fallback cache manager initialized at: {self.cache_dir}")
        
        # Run cleanup
        self._cleanup_expired_entries()
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load cache metadata from file."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load cache metadata: {e}")
        return {}
    
    def _save_metadata(self):
        """Save cache metadata to file."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2, default=str)
        except Exception as e:
            self.logger.warning(f"Failed to save cache metadata: {e}")
    
    def _generate_cache_key(self, api_name: str, key: str) -> str:
        """Generate cache key hash."""
        combined = f"{api_name}_{key}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def _cleanup_expired_entries(self):
        """Remove expired cache entries."""
        current_time = datetime.now()
        expired_keys = []
        
        for cache_key, entry in self.metadata.items():
            try:
                expires_at = datetime.fromisoformat(entry.get('expires_at', ''))
                if current_time > expires_at:
                    expired_keys.append(cache_key)
            except Exception:
                expired_keys.append(cache_key)  # Remove invalid entries
        
        for key in expired_keys:
            self._remove_cache_entry(key)
        
        if expired_keys:
            self.logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def _remove_cache_entry(self, cache_key: str):
        """Remove a single cache entry."""
        # Remove from metadata
        if cache_key in self.metadata:
            del self.metadata[cache_key]
        
        # Remove cache file
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                cache_file.unlink()
            except Exception as e:
                self.logger.warning(f"Failed to remove cache file {cache_file}: {e}")
    
    def cache_response(self, api_name: str, key: str, data: Any, ttl_hours: int = 24):
        """
        Cache API response data.
        
        Args:
            api_name: Name of the API
            key: Cache key
            data: Response data to cache
            ttl_hours: Time to live in hours
        """
        try:
            cache_key = self._generate_cache_key(api_name, key)
            cache_file = self.cache_dir / f"{cache_key}.json"
            
            # Save data to file
            cache_entry = {
                'api_name': api_name,
                'key': key,
                'data': data,
                'cached_at': datetime.now().isoformat(),
                'ttl_hours': ttl_hours
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cache_entry, f, indent=2, default=str)
            
            # Update metadata
            expires_at = datetime.now() + timedelta(hours=ttl_hours)
            self.metadata[cache_key] = {
                'api_name': api_name,
                'key': key,
                'cached_at': datetime.now().isoformat(),
                'expires_at': expires_at.isoformat(),
                'file_path': str(cache_file)
            }
            
            self._save_metadata()
            self.logger.debug(f"Cached response for {api_name}:{key}")
            
        except Exception as e:
            self.logger.error(f"Failed to cache response: {e}")
    
    def get_cached_response(self, api_name: str, key: str) -> Optional[Any]:
        """
        Retrieve cached response data.
        
        Args:
            api_name: Name of the API
            key: Cache key
            
        Returns:
            Cached data or None if not found/expired
        """
        try:
            cache_key = self._generate_cache_key(api_name, key)
            
            # Check metadata first
            if cache_key not in self.metadata:
                return None
            
            # Check if expired
            entry = self.metadata[cache_key]
            expires_at = datetime.fromisoformat(entry.get('expires_at', ''))
            if datetime.now() > expires_at:
                self._remove_cache_entry(cache_key)
                return None
            
            # Load from file
            cache_file = self.cache_dir / f"{cache_key}.json"
            if not cache_file.exists():
                self._remove_cache_entry(cache_key)
                return None
            
            with open(cache_file, 'r') as f:
                cache_entry = json.load(f)
            
            self.logger.debug(f"Retrieved cached response for {api_name}:{key}")
            return cache_entry.get('data')
            
        except Exception as e:
            self.logger.warning(f"Failed to retrieve cached response: {e}")
            return None
    
    def clear_cache(self, api_name: str = None):
        """
        Clear cache entries.
        
        Args:
            api_name: If specified, only clear entries for this API
        """
        keys_to_remove = []
        
        for cache_key, entry in self.metadata.items():
            if api_name is None or entry.get('api_name') == api_name:
                keys_to_remove.append(cache_key)
        
        for key in keys_to_remove:
            self._remove_cache_entry(key)
        
        self._save_metadata()
        self.logger.info(f"Cleared {len(keys_to_remove)} cache entries" + 
                        (f" for {api_name}" if api_name else ""))
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_entries = len(self.metadata)
        api_counts = {}
        
        for entry in self.metadata.values():
            api_name = entry.get('api_name', 'unknown')
            api_counts[api_name] = api_counts.get(api_name, 0) + 1
        
        return {
            'total_entries': total_entries,
            'entries_by_api': api_counts,
            'cache_directory': str(self.cache_dir),
            'metadata_file': str(self.metadata_file)
        }

# Alias for compatibility
APIResponseCache = FallbackAPIResponseCache