"""
Resilience middleware for handling connection issues and resource cleanup.

Provides:
- Automatic retry logic for failed operations
- Proper resource cleanup for NetCDF files
- Connection pool management
- Circuit breaker pattern for failing services
"""

import asyncio
import time
import logging
from typing import Callable, Any, Optional, Dict
from functools import wraps
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Circuit breaker to prevent cascading failures."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.is_open = False
        
    def record_success(self):
        """Record a successful operation."""
        self.failure_count = 0
        self.is_open = False
        
    def record_failure(self):
        """Record a failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.is_open = True
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
            
    def can_attempt(self) -> bool:
        """Check if we can attempt an operation."""
        if not self.is_open:
            return True
            
        # Check if recovery timeout has passed
        if time.time() - self.last_failure_time > self.recovery_timeout:
            logger.info("Circuit breaker attempting recovery")
            self.is_open = False
            self.failure_count = 0
            return True
            
        return False


class RetryPolicy:
    """Configurable retry policy with exponential backoff."""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 30.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number."""
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        return delay


def with_retry(retry_policy: Optional[RetryPolicy] = None, 
               circuit_breaker: Optional[CircuitBreaker] = None):
    """Decorator to add retry logic to async functions."""
    if retry_policy is None:
        retry_policy = RetryPolicy()
        
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(retry_policy.max_retries + 1):
                try:
                    # Check circuit breaker
                    if circuit_breaker and not circuit_breaker.can_attempt():
                        raise Exception("Circuit breaker is open")
                    
                    # Attempt the operation
                    result = await func(*args, **kwargs)
                    
                    # Record success
                    if circuit_breaker:
                        circuit_breaker.record_success()
                        
                    return result
                    
                except asyncio.CancelledError:
                    # Don't retry on cancellation
                    raise
                    
                except Exception as e:
                    last_exception = e
                    
                    # Record failure
                    if circuit_breaker:
                        circuit_breaker.record_failure()
                    
                    # Check if we should retry
                    if attempt < retry_policy.max_retries:
                        delay = retry_policy.get_delay(attempt)
                        logger.warning(
                            f"Operation {func.__name__} failed (attempt {attempt + 1}/{retry_policy.max_retries + 1}), "
                            f"retrying in {delay}s: {str(e)}"
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"Operation {func.__name__} failed after all retries: {str(e)}")
                        
            # All retries exhausted
            raise last_exception
            
        return wrapper
    return decorator


@asynccontextmanager
async def managed_resource(resource_factory: Callable, cleanup_func: Optional[Callable] = None):
    """Context manager for proper resource cleanup."""
    resource = None
    try:
        resource = await resource_factory()
        yield resource
    finally:
        if resource and cleanup_func:
            try:
                await cleanup_func(resource)
            except Exception as e:
                logger.error(f"Error during resource cleanup: {e}")


class ConnectionPool:
    """Simple connection pool for managing resources."""
    
    def __init__(self, factory: Callable, max_size: int = 10):
        self.factory = factory
        self.max_size = max_size
        self.pool: list = []
        self.in_use: Dict[Any, float] = {}
        self._lock = asyncio.Lock()
        
    async def acquire(self) -> Any:
        """Acquire a connection from the pool."""
        async with self._lock:
            # Try to get from pool
            while self.pool:
                conn = self.pool.pop()
                if await self._validate_connection(conn):
                    self.in_use[conn] = time.time()
                    return conn
                else:
                    await self._close_connection(conn)
                    
            # Create new connection if under limit
            if len(self.in_use) < self.max_size:
                conn = await self.factory()
                self.in_use[conn] = time.time()
                return conn
                
            # Wait for connection to be available
            raise Exception("Connection pool exhausted")
            
    async def release(self, conn: Any):
        """Release connection back to pool."""
        async with self._lock:
            if conn in self.in_use:
                del self.in_use[conn]
                if len(self.pool) < self.max_size:
                    self.pool.append(conn)
                else:
                    await self._close_connection(conn)
                    
    async def _validate_connection(self, conn: Any) -> bool:
        """Validate if connection is still usable."""
        # Override in subclass for specific validation
        return True
        
    async def _close_connection(self, conn: Any):
        """Close a connection."""
        # Override in subclass for specific cleanup
        try:
            if hasattr(conn, 'close'):
                await conn.close() if asyncio.iscoroutinefunction(conn.close) else conn.close()
        except Exception as e:
            logger.error(f"Error closing connection: {e}")
            
    async def cleanup(self):
        """Clean up all connections."""
        async with self._lock:
            # Close pooled connections
            for conn in self.pool:
                await self._close_connection(conn)
            self.pool.clear()
            
            # Close in-use connections
            for conn in list(self.in_use.keys()):
                await self._close_connection(conn)
            self.in_use.clear()


# Global instances for reuse
default_retry_policy = RetryPolicy(max_retries=3, base_delay=1.0, max_delay=10.0)
data_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30)