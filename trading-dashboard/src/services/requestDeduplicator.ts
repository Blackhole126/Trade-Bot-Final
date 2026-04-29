/**
 * REQUEST DEDUPLICATION SERVICE
 * Prevents duplicate API calls for the same symbol while request is in flight
 */

interface PendingRequest {
  promise: Promise<any>;
  timestamp: number;
}

class RequestDeduplicator {
  private pendingRequests = new Map<string, PendingRequest>();
  private cache = new Map<string, { data: any; timestamp: number }>();
  private readonly CACHE_TTL = 30000; // 30 seconds

  async deduplicate<T>(
    key: string,
    requestFn: () => Promise<T>,
    options: { cacheTTL?: number; forceRefresh?: boolean } = {}
  ): Promise<T> {
    const { cacheTTL = this.CACHE_TTL, forceRefresh = false } = options;
    
    // FORCE REFRESH: Bypass all caching and deduplication
    if (forceRefresh) {
      console.log(`[REFRESH] Forcing fresh request for ${key}, bypassing dedup`);
      const uniqueKey = `${key}_refresh_${Date.now()}`;
      
      const promise = requestFn().finally(() => {
        this.pendingRequests.delete(uniqueKey);
      });
      
      this.pendingRequests.set(uniqueKey, {
        promise,
        timestamp: Date.now()
      });
      
      try {
        const result = await promise;
        // Update cache with fresh data
        this.cache.set(key, {
          data: result,
          timestamp: Date.now()
        });
        return result;
      } catch (error) {
        throw error;
      }
    }
    
    // Normal flow: Check cache first
    const cached = this.cache.get(key);
    if (cached && Date.now() - cached.timestamp < cacheTTL) {
      console.log(`[DEDUP] Cache hit for ${key}`);
      return cached.data;
    }

    // Check if request is already in flight
    const pending = this.pendingRequests.get(key);
    if (pending) {
      console.log(`[DEDUP] Request in flight for ${key}, waiting...`);
      return pending.promise;
    }

    // Execute new request
    console.log(`[DEDUP] New request for ${key}`);
    const promise = requestFn().finally(() => {
      this.pendingRequests.delete(key);
    });

    this.pendingRequests.set(key, {
      promise,
      timestamp: Date.now()
    });

    try {
      const result = await promise;
      // Cache successful results
      this.cache.set(key, {
        data: result,
        timestamp: Date.now()
      });
      return result;
    } catch (error) {
      // Don't cache errors
      throw error;
    }
  }

  clearCache() {
    this.cache.clear();
    console.log('[DEDUP] Cache cleared');
  }

  getStats() {
    return {
      pendingRequests: this.pendingRequests.size,
      cachedItems: this.cache.size
    };
  }
}

export const requestDeduplicator = new RequestDeduplicator();