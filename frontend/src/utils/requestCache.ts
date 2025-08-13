/**
 * High-Performance Request Cache and Deduplication System
 * 
 * Prevents duplicate API requests and caches responses for ultra-fast access.
 * Implements multiple optimization layers:
 * 1. Request deduplication (prevent duplicate in-flight requests)
 * 2. Response caching (cache successful responses)
 * 3. Browser storage persistence (survive page reloads)
 */

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  ttl: number;
}

interface PendingRequest<T> {
  promise: Promise<T>;
  timestamp: number;
}

interface RetryOptions {
  maxRetries?: number;
  initialDelay?: number;
  maxDelay?: number;
  backoffMultiplier?: number;
}

class HighPerformanceRequestCache {
  private memoryCache = new Map<string, CacheEntry<any>>();
  private pendingRequests = new Map<string, PendingRequest<any>>();
  private maxCacheSize = 1000;
  private defaultTTL = 5 * 60 * 1000; // 5 minutes
  private storagePrefix = 'ocean-data-cache-';
  
  // Performance counters
  private stats = {
    hits: 0,
    misses: 0,
    deduped: 0,
    requests: 0
  };

  /**
   * Get data with intelligent caching and deduplication
   */
  async get<T>(
    key: string, 
    fetcher: () => Promise<T>, 
    options: { ttl?: number; useStorage?: boolean; retry?: RetryOptions } = {}
  ): Promise<T> {
    const { ttl = this.defaultTTL, useStorage = true, retry = { maxRetries: 3 } } = options;
    this.stats.requests++;

    // Step 1: Check if request is already in flight
    const pendingRequest = this.pendingRequests.get(key);
    if (pendingRequest) {
      this.stats.deduped++;
      return pendingRequest.promise;
    }

    // Step 2: Check memory cache
    const memoryEntry = this.memoryCache.get(key);
    if (memoryEntry && this.isValid(memoryEntry)) {
      this.stats.hits++;
      return memoryEntry.data;
    }

    // Step 3: Check browser storage cache
    if (useStorage) {
      const storageData = this.getFromStorage<T>(key);
      if (storageData && this.isValid(storageData)) {
        this.stats.hits++;
        // Also store in memory for faster access
        this.memoryCache.set(key, storageData);
        this.enforceMemoryCacheSize();
        return storageData.data;
      }
    }

    // Step 4: Cache miss - make the request with deduplication
    this.stats.misses++;

    // Create and store pending request with retry logic
    const requestPromise = this.executeRequestWithRetry(key, fetcher, ttl, useStorage, retry);
    this.pendingRequests.set(key, {
      promise: requestPromise,
      timestamp: Date.now()
    });

    try {
      const result = await requestPromise;
      return result;
    } finally {
      // Clean up pending request
      this.pendingRequests.delete(key);
    }
  }

  private async executeRequestWithRetry<T>(
    key: string,
    fetcher: () => Promise<T>,
    ttl: number,
    useStorage: boolean,
    retryOptions: RetryOptions
  ): Promise<T> {
    const {
      maxRetries = 3,
      initialDelay = 1000,
      maxDelay = 30000,
      backoffMultiplier = 2
    } = retryOptions;

    let lastError: Error | null = null;
    let delay = initialDelay;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        return await this.executeRequest(key, fetcher, ttl, useStorage);
      } catch (error) {
        lastError = error as Error;
        
        // Don't retry on certain errors
        if (error instanceof Error) {
          const message = error.message.toLowerCase();
          if (message.includes('404') || message.includes('not found') || 
              message.includes('unauthorized') || message.includes('forbidden') ||
              message.includes('503') || message.includes('service unavailable')) {
            throw error;
          }
        }

        // If this is not the last attempt, wait before retrying
        if (attempt < maxRetries) {
          
          await new Promise(resolve => setTimeout(resolve, delay));
          
          // Exponential backoff
          delay = Math.min(delay * backoffMultiplier, maxDelay);
        }
      }
    }

    throw lastError || new Error('Request failed after all retries');
  }

  private async executeRequest<T>(
    key: string, 
    fetcher: () => Promise<T>, 
    ttl: number,
    useStorage: boolean
  ): Promise<T> {
    try {
      const startTime = Date.now();
      const data = await fetcher();
      const requestTime = Date.now() - startTime;


      // Cache the successful response
      const cacheEntry: CacheEntry<T> = {
        data,
        timestamp: Date.now(),
        ttl
      };

      // Store in memory cache
      this.memoryCache.set(key, cacheEntry);
      this.enforceMemoryCacheSize();

      // Store in browser storage if enabled
      if (useStorage) {
        this.saveToStorage(key, cacheEntry);
      }

      return data;
    } catch (error) {
      throw error;
    }
  }

  private isValid<T>(entry: CacheEntry<T>): boolean {
    return Date.now() - entry.timestamp < entry.ttl;
  }

  private enforceMemoryCacheSize(): void {
    if (this.memoryCache.size <= this.maxCacheSize) return;

    // Remove oldest entries
    const entries = Array.from(this.memoryCache.entries());
    entries.sort((a, b) => a[1].timestamp - b[1].timestamp);
    
    const toRemove = entries.slice(0, entries.length - this.maxCacheSize);
    toRemove.forEach(([key]) => this.memoryCache.delete(key));
  }

  private getFromStorage<T>(key: string): CacheEntry<T> | null {
    try {
      const stored = localStorage.getItem(this.storagePrefix + key);
      if (!stored) return null;
      
      return JSON.parse(stored) as CacheEntry<T>;
    } catch (error) {
      return null;
    }
  }

  private saveToStorage<T>(key: string, entry: CacheEntry<T>): void {
    try {
      localStorage.setItem(
        this.storagePrefix + key, 
        JSON.stringify(entry)
      );
    } catch (error) {
      // Storage might be full - try clearing old entries
      this.cleanupStorage();
    }
  }

  private cleanupStorage(): void {
    try {
      const keysToRemove: string[] = [];
      
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.startsWith(this.storagePrefix)) {
          try {
            const entry = JSON.parse(localStorage.getItem(key) || '{}');
            if (!this.isValid(entry)) {
              keysToRemove.push(key);
            }
          } catch {
            keysToRemove.push(key);
          }
        }
      }

      keysToRemove.forEach(key => localStorage.removeItem(key));
    } catch (error) {
    }
  }

  /**
   * Create cache key for ocean data requests
   */
  createOceanDataKey(lat: number, lon: number, date: string, datasets: string[]): string {
    // Round coordinates to reduce cache fragmentation
    const roundedLat = Math.round(lat * 100) / 100;
    const roundedLon = Math.round(lon * 100) / 100;
    // Include all datasets (currents performance issues have been resolved)
    const datasetsStr = datasets.sort().join(',');
    return `ocean-data:${roundedLat}:${roundedLon}:${date}:${datasetsStr}`;
  }

  /**
   * Create cache key for texture requests
   */
  createTextureKey(category: string, date?: string, resolution: string = 'medium'): string {
    return `texture:${category}:${date || 'latest'}:${resolution}`;
  }

  /**
   * Clear all caches
   */
  clearAll(): void {
    this.memoryCache.clear();
    this.pendingRequests.clear();
    
    // Clear storage cache
    const keysToRemove: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith(this.storagePrefix)) {
        keysToRemove.push(key);
      }
    }
    keysToRemove.forEach(key => localStorage.removeItem(key));
    
  }

  /**
   * Get cache statistics
   */
  getStats() {
    const totalRequests = this.stats.hits + this.stats.misses;
    const hitRate = totalRequests > 0 ? (this.stats.hits / totalRequests * 100) : 0;
    
    return {
      ...this.stats,
      hitRate: Math.round(hitRate * 100) / 100,
      memoryCacheSize: this.memoryCache.size,
      pendingRequests: this.pendingRequests.size
    };
  }

  /**
   * Clean up expired entries periodically
   */
  startCleanupInterval(intervalMs: number = 5 * 60 * 1000): void {
    setInterval(() => {
      // Clean memory cache
      const expiredKeys: string[] = [];
      this.memoryCache.forEach((entry, key) => {
        if (!this.isValid(entry)) {
          expiredKeys.push(key);
        }
      });
      expiredKeys.forEach(key => this.memoryCache.delete(key));

      // Clean storage cache
      this.cleanupStorage();

      if (expiredKeys.length > 0) {
      }
    }, intervalMs);
  }
}

// Global cache instance
export const requestCache = new HighPerformanceRequestCache();

// Start automatic cleanup
requestCache.startCleanupInterval();

// Development helper
if (typeof window !== 'undefined') {
  (window as any).oceanDataCache = {
    stats: () => requestCache.getStats(),
    clear: () => requestCache.clearAll()
  };
}