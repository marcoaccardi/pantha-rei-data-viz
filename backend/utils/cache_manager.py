#!/usr/bin/env python3
"""
Enhanced cache manager for API responses.
Uses SQLite for structured data and implements TTL-based caching.
"""

import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
import os

class APIResponseCache:
    """Enhanced cache manager for API responses with SQLite backend."""
    
    def __init__(self, cache_dir: Path):
        """
        Initialize cache manager.
        
        Args:
            cache_dir: Directory to store cache files
        """
        self.logger = logging.getLogger(__name__)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize SQLite database
        self.cache_db = self.cache_dir / 'api_response_cache.sqlite'
        self._init_database()
        
        # Cache configuration from environment
        self.max_cache_size_mb = int(os.getenv('CACHE_MAX_SIZE_MB', 1000))
        self.cleanup_interval_hours = int(os.getenv('CACHE_CLEANUP_INTERVAL_HOURS', 6))
        
        self.logger.info(f"Cache manager initialized with database: {self.cache_db}")
        
        # Run initial cleanup
        self._cleanup_expired_entries()
    
    def _init_database(self):
        """Initialize cache database tables."""
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        
        # Create main cache table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_name TEXT NOT NULL,
                query_hash TEXT NOT NULL,
                query_params TEXT NOT NULL,
                response_data TEXT NOT NULL,
                data_size_bytes INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                access_count INTEGER DEFAULT 0,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(api_name, query_hash)
            )
        ''')
        
        # Create indices for performance
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_api_hash 
            ON api_responses(api_name, query_hash)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_expires 
            ON api_responses(expires_at)
        ''')
        
        # Create cache statistics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_name TEXT NOT NULL,
                total_requests INTEGER DEFAULT 0,
                cache_hits INTEGER DEFAULT 0,
                cache_misses INTEGER DEFAULT 0,
                total_size_bytes INTEGER DEFAULT 0,
                last_cleanup TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _generate_query_hash(self, query_params: Dict[str, Any]) -> str:
        """Generate unique hash for query parameters."""
        # Sort parameters for consistent hashing
        sorted_params = json.dumps(query_params, sort_keys=True)
        return hashlib.md5(sorted_params.encode()).hexdigest()
    
    def get_cached_response(self, api_name: str, query_key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached API response if valid.
        
        Args:
            api_name: Name of the API
            query_key: Unique key for the query
            
        Returns:
            Cached response data or None if not found/expired
        """
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        
        try:
            # Get cached response if not expired
            cursor.execute('''
                SELECT response_data, id FROM api_responses 
                WHERE api_name = ? AND query_hash = ? AND expires_at > ?
            ''', (api_name, query_key, datetime.now()))
            
            result = cursor.fetchone()
            
            if result:
                response_data, cache_id = result
                
                # Update access statistics
                cursor.execute('''
                    UPDATE api_responses 
                    SET access_count = access_count + 1, 
                        last_accessed = ? 
                    WHERE id = ?
                ''', (datetime.now(), cache_id))
                
                # Update cache hit statistics
                self._update_stats(cursor, api_name, hit=True)
                
                conn.commit()
                
                self.logger.debug(f"Cache hit for {api_name}:{query_key}")
                return json.loads(response_data)
            else:
                # Update cache miss statistics
                self._update_stats(cursor, api_name, hit=False)
                conn.commit()
                
                self.logger.debug(f"Cache miss for {api_name}:{query_key}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error retrieving cached response: {e}")
            return None
        finally:
            conn.close()
    
    def cache_response(self, api_name: str, query_key: str, 
                      response_data: Any, ttl_hours: int = 24):
        """
        Cache API response with TTL.
        
        Args:
            api_name: Name of the API
            query_key: Unique key for the query
            response_data: Response data to cache
            ttl_hours: Time to live in hours
        """
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        
        try:
            expires_at = datetime.now() + timedelta(hours=ttl_hours)
            response_json = json.dumps(response_data, default=str)
            data_size = len(response_json.encode('utf-8'))
            
            # Extract query parameters if available
            query_params = {}
            if isinstance(response_data, dict):
                query_params = response_data.get('query_parameters', {})
            
            cursor.execute('''
                INSERT OR REPLACE INTO api_responses 
                (api_name, query_hash, query_params, response_data, 
                 data_size_bytes, expires_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (api_name, query_key, json.dumps(query_params), 
                  response_json, data_size, expires_at, datetime.now()))
            
            conn.commit()
            
            self.logger.debug(f"Cached response for {api_name}:{query_key}, expires: {expires_at}")
            
            # Check if cleanup is needed
            if self._should_cleanup():
                self._cleanup_expired_entries()
                
        except Exception as e:
            self.logger.error(f"Error caching response: {e}")
        finally:
            conn.close()
    
    def _update_stats(self, cursor, api_name: str, hit: bool):
        """Update cache statistics."""
        # Check if stats exist for this API
        cursor.execute('''
            SELECT id FROM cache_stats WHERE api_name = ?
        ''', (api_name,))
        
        if cursor.fetchone():
            # Update existing stats
            if hit:
                cursor.execute('''
                    UPDATE cache_stats 
                    SET total_requests = total_requests + 1,
                        cache_hits = cache_hits + 1
                    WHERE api_name = ?
                ''', (api_name,))
            else:
                cursor.execute('''
                    UPDATE cache_stats 
                    SET total_requests = total_requests + 1,
                        cache_misses = cache_misses + 1
                    WHERE api_name = ?
                ''', (api_name,))
        else:
            # Create new stats entry
            cursor.execute('''
                INSERT INTO cache_stats 
                (api_name, total_requests, cache_hits, cache_misses)
                VALUES (?, 1, ?, ?)
            ''', (api_name, 1 if hit else 0, 0 if hit else 1))
    
    def _should_cleanup(self) -> bool:
        """Check if cache cleanup is needed."""
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        
        try:
            # Check last cleanup time
            cursor.execute('''
                SELECT MAX(last_cleanup) FROM cache_stats
            ''')
            
            result = cursor.fetchone()
            if result and result[0]:
                last_cleanup = datetime.fromisoformat(result[0])
                hours_since_cleanup = (datetime.now() - last_cleanup).total_seconds() / 3600
                return hours_since_cleanup >= self.cleanup_interval_hours
            else:
                return True
                
        except Exception as e:
            self.logger.error(f"Error checking cleanup status: {e}")
            return False
        finally:
            conn.close()
    
    def _cleanup_expired_entries(self):
        """Remove expired cache entries and manage cache size."""
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        
        try:
            self.logger.info("Starting cache cleanup...")
            
            # Remove expired entries
            cursor.execute('''
                DELETE FROM api_responses WHERE expires_at < ?
            ''', (datetime.now(),))
            
            expired_count = cursor.rowcount
            
            # Check total cache size
            cursor.execute('''
                SELECT SUM(data_size_bytes) FROM api_responses
            ''')
            
            total_size = cursor.fetchone()[0] or 0
            max_size_bytes = self.max_cache_size_mb * 1024 * 1024
            
            # If cache is too large, remove least recently accessed entries
            if total_size > max_size_bytes:
                self.logger.info(f"Cache size ({total_size/1024/1024:.2f}MB) exceeds limit ({self.max_cache_size_mb}MB)")
                
                # Calculate how much to remove
                size_to_remove = total_size - (max_size_bytes * 0.8)  # Keep 80% of max
                
                # Remove least recently accessed entries
                cursor.execute('''
                    DELETE FROM api_responses 
                    WHERE id IN (
                        SELECT id FROM api_responses 
                        ORDER BY last_accessed ASC 
                        LIMIT (
                            SELECT COUNT(*) FROM api_responses 
                            WHERE data_size_bytes <= ?
                        )
                    )
                ''', (size_to_remove,))
                
                removed_count = cursor.rowcount
                self.logger.info(f"Removed {removed_count} entries to manage cache size")
            
            # Update cleanup timestamp
            cursor.execute('''
                UPDATE cache_stats SET last_cleanup = ?
            ''', (datetime.now(),))
            
            conn.commit()
            
            self.logger.info(f"Cache cleanup completed. Removed {expired_count} expired entries")
            
        except Exception as e:
            self.logger.error(f"Error during cache cleanup: {e}")
        finally:
            conn.close()
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        
        try:
            # Get overall statistics
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_entries,
                    SUM(data_size_bytes) as total_size,
                    AVG(access_count) as avg_access_count,
                    MAX(last_accessed) as most_recent_access
                FROM api_responses
            ''')
            
            overall = cursor.fetchone()
            
            # Get per-API statistics
            cursor.execute('''
                SELECT 
                    api_name,
                    total_requests,
                    cache_hits,
                    cache_misses,
                    ROUND(CAST(cache_hits AS FLOAT) / NULLIF(total_requests, 0) * 100, 2) as hit_rate
                FROM cache_stats
            ''')
            
            api_stats = []
            for row in cursor.fetchall():
                api_stats.append({
                    'api_name': row[0],
                    'total_requests': row[1],
                    'cache_hits': row[2],
                    'cache_misses': row[3],
                    'hit_rate': row[4] or 0
                })
            
            return {
                'total_entries': overall[0] or 0,
                'total_size_mb': (overall[1] or 0) / 1024 / 1024,
                'avg_access_count': overall[2] or 0,
                'most_recent_access': overall[3],
                'api_statistics': api_stats,
                'cache_db_path': str(self.cache_db),
                'max_size_mb': self.max_cache_size_mb
            }
            
        except Exception as e:
            self.logger.error(f"Error getting cache statistics: {e}")
            return {}
        finally:
            conn.close()
    
    def clear_cache(self, api_name: Optional[str] = None):
        """
        Clear cache entries.
        
        Args:
            api_name: If specified, only clear cache for this API
        """
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        
        try:
            if api_name:
                cursor.execute('''
                    DELETE FROM api_responses WHERE api_name = ?
                ''', (api_name,))
                self.logger.info(f"Cleared cache for API: {api_name}")
            else:
                cursor.execute('DELETE FROM api_responses')
                self.logger.info("Cleared all cache entries")
            
            conn.commit()
            
        except Exception as e:
            self.logger.error(f"Error clearing cache: {e}")
        finally:
            conn.close()


def main():
    """Test cache manager."""
    import tempfile
    
    # Create temporary cache directory
    with tempfile.TemporaryDirectory() as temp_dir:
        cache = APIResponseCache(Path(temp_dir))
        
        print("🗄️ CACHE MANAGER TEST")
        print("=" * 50)
        
        # Test caching
        test_data = {
            'status': 'success',
            'data': {'temperature': 22.5, 'salinity': 35.2},
            'query_parameters': {'lat': 40.0, 'lon': -70.0}
        }
        
        # Cache some data
        cache.cache_response('test_api', 'test_key_1', test_data, ttl_hours=1)
        print("✅ Cached test data")
        
        # Retrieve cached data
        cached = cache.get_cached_response('test_api', 'test_key_1')
        print(f"✅ Retrieved cached data: {cached is not None}")
        
        # Test cache miss
        missed = cache.get_cached_response('test_api', 'non_existent_key')
        print(f"✅ Cache miss test: {missed is None}")
        
        # Get statistics
        stats = cache.get_cache_statistics()
        print("\n📊 Cache Statistics:")
        print(f"  Total entries: {stats['total_entries']}")
        print(f"  Total size: {stats['total_size_mb']:.2f} MB")
        print(f"  API statistics: {stats['api_statistics']}")

if __name__ == "__main__":
    main()