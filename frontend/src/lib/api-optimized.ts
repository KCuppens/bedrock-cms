import type { 
  ApiResponse, 
  PaginatedResponse, 
  Page,
  PageCreateRequest,
  PageUpdateRequest,
  PageFilters,
  MediaAsset,
  MediaUploadRequest,
  MediaFilters,
  TranslationUnit,
  TranslationUpdateRequest,
  TranslationFilters,
  User,
  Redirect,
  RedirectCreateRequest,
  AuditLogEntry,
  RequestConfig 
} from '@/types/api';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

// Cache configuration
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes
const CACHE_MAX_SIZE = 100; // Maximum cache entries

// Request queue for rate limiting
const REQUEST_QUEUE_DELAY = 100; // ms between requests
const MAX_RETRIES = 3;
const RETRY_DELAY = 1000; // ms

// Debounce helper
function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => Promise<ReturnType<T>> {
  let timeout: NodeJS.Timeout | null = null;
  let resolvePromise: ((value: ReturnType<T>) => void) | null = null;

  return (...args: Parameters<T>) => {
    return new Promise<ReturnType<T>>((resolve) => {
      if (timeout) clearTimeout(timeout);
      resolvePromise = resolve;
      
      timeout = setTimeout(async () => {
        const result = await func(...args);
        if (resolvePromise) resolvePromise(result);
      }, wait);
    });
  };
}

// LRU Cache implementation
class LRUCache<T> {
  private cache = new Map<string, { data: T; timestamp: number }>();
  private maxSize: number;
  private ttl: number;

  constructor(maxSize = CACHE_MAX_SIZE, ttl = CACHE_TTL) {
    this.maxSize = maxSize;
    this.ttl = ttl;
  }

  get(key: string): T | null {
    const entry = this.cache.get(key);
    if (!entry) return null;

    // Check if expired
    if (Date.now() - entry.timestamp > this.ttl) {
      this.cache.delete(key);
      return null;
    }

    // Move to end (most recently used)
    this.cache.delete(key);
    this.cache.set(key, entry);
    return entry.data;
  }

  set(key: string, data: T): void {
    // Remove oldest if at capacity
    if (this.cache.size >= this.maxSize && !this.cache.has(key)) {
      const firstKey = this.cache.keys().next().value;
      if (firstKey) this.cache.delete(firstKey);
    }

    this.cache.set(key, { data, timestamp: Date.now() });
  }

  invalidate(pattern?: string): void {
    if (!pattern) {
      this.cache.clear();
      return;
    }

    // Invalidate keys matching pattern
    for (const key of this.cache.keys()) {
      if (key.includes(pattern)) {
        this.cache.delete(key);
      }
    }
  }

  size(): number {
    return this.cache.size;
  }
}

// Request queue for rate limiting
class RequestQueue {
  private queue: Array<() => Promise<any>> = [];
  private processing = false;
  private delay: number;

  constructor(delay = REQUEST_QUEUE_DELAY) {
    this.delay = delay;
  }

  async add<T>(request: () => Promise<T>): Promise<T> {
    return new Promise((resolve, reject) => {
      this.queue.push(async () => {
        try {
          const result = await request();
          resolve(result);
        } catch (error) {
          reject(error);
        }
      });

      if (!this.processing) {
        this.process();
      }
    });
  }

  private async process(): Promise<void> {
    this.processing = true;

    while (this.queue.length > 0) {
      const request = this.queue.shift();
      if (request) {
        await request();
        await new Promise(resolve => setTimeout(resolve, this.delay));
      }
    }

    this.processing = false;
  }
}

// Optimized API Client
class OptimizedApiClient {
  private baseURL: string;
  private cache = new LRUCache();
  private requestQueue = new RequestQueue();
  private abortControllers = new Map<string, AbortController>();

  constructor(baseURL: string) {
    this.baseURL = baseURL;
  }

  // Cancel ongoing requests
  cancelRequest(key: string): void {
    const controller = this.abortControllers.get(key);
    if (controller) {
      controller.abort();
      this.abortControllers.delete(key);
    }
  }

  cancelAllRequests(): void {
    for (const controller of this.abortControllers.values()) {
      controller.abort();
    }
    this.abortControllers.clear();
  }

  // Retry logic with exponential backoff
  private async retryRequest<T>(
    fn: () => Promise<T>,
    retries = MAX_RETRIES,
    delay = RETRY_DELAY
  ): Promise<T> {
    try {
      return await fn();
    } catch (error: any) {
      if (retries === 0 || error.name === 'AbortError') {
        throw error;
      }

      // Don't retry on client errors (4xx)
      if (error.status && error.status >= 400 && error.status < 500) {
        throw error;
      }

      await new Promise(resolve => setTimeout(resolve, delay));
      return this.retryRequest(fn, retries - 1, delay * 2);
    }
  }

  private async request<T>({ 
    method, 
    url, 
    params, 
    data, 
    headers = {},
    useCache = true,
    cacheKey,
    signal,
    skipQueue = false
  }: RequestConfig & { 
    useCache?: boolean; 
    cacheKey?: string;
    signal?: AbortSignal;
    skipQueue?: boolean;
  }): Promise<T> {
    const fullUrl = new URL(url, this.baseURL);
    
    // Add query parameters
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          fullUrl.searchParams.set(key, String(value));
        }
      });
    }

    // Generate cache key
    const finalCacheKey = cacheKey || `${method}:${fullUrl.toString()}:${JSON.stringify(data || {})}`;

    // Check cache for GET requests
    if (method === 'GET' && useCache) {
      const cached = this.cache.get(finalCacheKey);
      if (cached) {
        return cached as T;
      }
    }

    // Create abort controller
    const abortController = new AbortController();
    const requestKey = `${method}:${url}`;
    
    // Cancel previous request to same endpoint
    this.cancelRequest(requestKey);
    this.abortControllers.set(requestKey, abortController);

    const makeRequest = async () => {
      const requestHeaders: HeadersInit = {
        'Content-Type': 'application/json',
        ...headers,
      };

      const config: RequestInit = {
        method,
        headers: requestHeaders,
        credentials: 'include',
        signal: signal || abortController.signal,
      };

      if (data && method !== 'GET') {
        if (data instanceof FormData) {
          delete requestHeaders['Content-Type'];
          config.body = data;
        } else {
          config.body = JSON.stringify(data);
        }
      }

      const response = await fetch(fullUrl.toString(), config);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ 
          error: 'Request failed',
          message: `HTTP ${response.status} ${response.statusText}`,
          status: response.status
        }));
        const error = new Error(errorData.message || errorData.error || 'Request failed');
        (error as any).status = response.status;
        throw error;
      }

      // Handle empty responses
      if (response.status === 204) {
        return {} as T;
      }

      const result = await response.json();

      // Cache successful GET requests
      if (method === 'GET' && useCache) {
        this.cache.set(finalCacheKey, result);
      }

      // Invalidate related cache on mutations
      if (method !== 'GET') {
        this.cache.invalidate(url.split('/')[1]); // Invalidate by resource type
      }

      return result;
    };

    // Use request queue for rate limiting (skip for urgent requests)
    if (skipQueue) {
      return this.retryRequest(makeRequest);
    } else {
      return this.requestQueue.add(() => this.retryRequest(makeRequest));
    }
  }

  // Optimistic update helper
  async optimisticUpdate<T>(
    key: string,
    optimisticData: T,
    updateFn: () => Promise<T>
  ): Promise<T> {
    // Set optimistic data in cache
    this.cache.set(key, optimisticData);

    try {
      const result = await updateFn();
      this.cache.set(key, result);
      return result;
    } catch (error) {
      // Revert on error
      this.cache.invalidate(key);
      throw error;
    }
  }

  // Batch requests helper
  async batchRequests<T>(
    requests: Array<() => Promise<T>>
  ): Promise<T[]> {
    return Promise.all(requests.map(req => this.requestQueue.add(req)));
  }

  // Pages API with optimizations
  pages = {
    list: (filters?: PageFilters): Promise<PaginatedResponse<Page>> =>
      this.request({ 
        method: 'GET', 
        url: '/pages', 
        params: filters,
        useCache: true 
      }),
    
    get: (id: number): Promise<ApiResponse<Page>> =>
      this.request({ 
        method: 'GET', 
        url: `/pages/${id}`,
        useCache: true,
        cacheKey: `page:${id}`
      }),
    
    create: (data: PageCreateRequest): Promise<ApiResponse<Page>> =>
      this.request({ 
        method: 'POST', 
        url: '/pages', 
        data,
        skipQueue: true // Priority for creates
      }),
    
    update: (id: number, data: PageUpdateRequest): Promise<ApiResponse<Page>> =>
      this.optimisticUpdate(
        `page:${id}`,
        { data: { ...data, id } as Page } as ApiResponse<Page>,
        () => this.request({ 
          method: 'PATCH', 
          url: `/pages/${id}`, 
          data,
          skipQueue: true
        })
      ),
    
    delete: (id: number): Promise<void> =>
      this.request({ 
        method: 'DELETE', 
        url: `/pages/${id}`,
        skipQueue: true
      }),
    
    publish: (id: number): Promise<ApiResponse<Page>> =>
      this.request({ 
        method: 'POST', 
        url: `/pages/${id}/publish`,
        skipQueue: true
      }),
    
    unpublish: (id: number): Promise<ApiResponse<Page>> =>
      this.request({ 
        method: 'POST', 
        url: `/pages/${id}/unpublish`,
        skipQueue: true
      }),
    
    // Debounced search
    search: debounce((query: string): Promise<PaginatedResponse<Page>> =>
      this.request({ 
        method: 'GET', 
        url: '/pages/search', 
        params: { q: query },
        useCache: true
      }), 300),
  };

  // Media API with upload progress
  media = {
    list: (filters?: MediaFilters): Promise<PaginatedResponse<MediaAsset>> =>
      this.request({ 
        method: 'GET', 
        url: '/media', 
        params: filters,
        useCache: true
      }),
    
    get: (id: number): Promise<ApiResponse<MediaAsset>> =>
      this.request({ 
        method: 'GET', 
        url: `/media/${id}`,
        useCache: true,
        cacheKey: `media:${id}`
      }),
    
    upload: async (
      data: MediaUploadRequest,
      onProgress?: (progress: number) => void
    ): Promise<ApiResponse<MediaAsset>> => {
      const formData = new FormData();
      formData.append('file', data.file);
      if (data.title) formData.append('title', data.title);
      if (data.description) formData.append('description', data.description);
      if (data.alt_texts) formData.append('alt_texts', JSON.stringify(data.alt_texts));
      if (data.tags) formData.append('tags', JSON.stringify(data.tags));
      
      // Use XMLHttpRequest for progress tracking
      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        
        xhr.upload.addEventListener('progress', (e) => {
          if (e.lengthComputable && onProgress) {
            const percentComplete = (e.loaded / e.total) * 100;
            onProgress(percentComplete);
          }
        });
        
        xhr.addEventListener('load', () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve(JSON.parse(xhr.responseText));
          } else {
            reject(new Error(`Upload failed: ${xhr.statusText}`));
          }
        });
        
        xhr.addEventListener('error', () => {
          reject(new Error('Upload failed'));
        });
        
        xhr.open('POST', `${this.baseURL}/media/upload`);
        xhr.withCredentials = true;
        xhr.send(formData);
      });
    },
    
    delete: (id: number): Promise<void> =>
      this.request({ 
        method: 'DELETE', 
        url: `/media/${id}`,
        skipQueue: true
      }),
    
    generateRenditions: (id: number): Promise<ApiResponse<MediaAsset>> =>
      this.request({ 
        method: 'POST', 
        url: `/media/${id}/renditions`
      }),
  };

  // Translations API
  translations = {
    list: (filters?: TranslationFilters): Promise<PaginatedResponse<TranslationUnit>> =>
      this.request({ 
        method: 'GET', 
        url: '/translations', 
        params: filters,
        useCache: true
      }),
    
    get: (id: string): Promise<ApiResponse<TranslationUnit>> =>
      this.request({ 
        method: 'GET', 
        url: `/translations/${id}`,
        useCache: true,
        cacheKey: `translation:${id}`
      }),
    
    update: (id: string, data: TranslationUpdateRequest): Promise<ApiResponse<TranslationUnit>> =>
      this.optimisticUpdate(
        `translation:${id}`,
        { data: { ...data, id } as TranslationUnit } as ApiResponse<TranslationUnit>,
        () => this.request({ 
          method: 'PATCH', 
          url: `/translations/${id}`, 
          data,
          skipQueue: true
        })
      ),
    
    bulkUpdate: (updates: Array<{ id: string; data: TranslationUpdateRequest }>): Promise<ApiResponse<TranslationUnit[]>> =>
      this.request({ 
        method: 'PATCH', 
        url: '/translations/bulk', 
        data: { updates },
        skipQueue: true
      }),
    
    suggest: (id: string): Promise<ApiResponse<{ suggestion: string }>> =>
      this.request({ 
        method: 'POST', 
        url: `/translations/${id}/suggest`,
        useCache: true,
        cacheKey: `translation-suggestion:${id}`
      }),
    
    approve: (id: string): Promise<ApiResponse<TranslationUnit>> =>
      this.request({ 
        method: 'POST', 
        url: `/translations/${id}/approve`,
        skipQueue: true
      }),
  };

  // Users API
  users = {
    list: (): Promise<PaginatedResponse<User>> =>
      this.request({ 
        method: 'GET', 
        url: '/users',
        useCache: true
      }),
    
    get: (id: number): Promise<ApiResponse<User>> =>
      this.request({ 
        method: 'GET', 
        url: `/users/${id}`,
        useCache: true,
        cacheKey: `user:${id}`
      }),
    
    me: (): Promise<ApiResponse<User>> =>
      this.request({ 
        method: 'GET', 
        url: '/users/me',
        useCache: true,
        cacheKey: 'user:me'
      }),
  };

  // SEO & Redirects API
  redirects = {
    list: (): Promise<PaginatedResponse<Redirect>> =>
      this.request({ 
        method: 'GET', 
        url: '/redirects',
        useCache: true
      }),
    
    create: (data: RedirectCreateRequest): Promise<ApiResponse<Redirect>> =>
      this.request({ 
        method: 'POST', 
        url: '/redirects', 
        data,
        skipQueue: true
      }),
    
    update: (id: number, data: Partial<RedirectCreateRequest>): Promise<ApiResponse<Redirect>> =>
      this.request({ 
        method: 'PATCH', 
        url: `/redirects/${id}`, 
        data,
        skipQueue: true
      }),
    
    delete: (id: number): Promise<void> =>
      this.request({ 
        method: 'DELETE', 
        url: `/redirects/${id}`,
        skipQueue: true
      }),
    
    test: (id: number): Promise<ApiResponse<{ status: number; location?: string }>> =>
      this.request({ 
        method: 'POST', 
        url: `/redirects/${id}/test`
      }),
  };

  // Audit Log API
  audit = {
    list: (filters?: { 
      actor?: string; 
      action?: string; 
      model?: string; 
      start_date?: string; 
      end_date?: string;
      page?: number;
      limit?: number; 
    }): Promise<PaginatedResponse<AuditLogEntry>> =>
      this.request({ 
        method: 'GET', 
        url: '/audit', 
        params: filters,
        useCache: true
      }),
    
    get: (id: number): Promise<ApiResponse<AuditLogEntry>> =>
      this.request({ 
        method: 'GET', 
        url: `/audit/${id}`,
        useCache: true,
        cacheKey: `audit:${id}`
      }),
  };

  // Schema & Documentation
  schema = {
    openapi: (): Promise<any> =>
      this.request({ 
        method: 'GET', 
        url: '/schema',
        useCache: true,
        cacheKey: 'schema:openapi'
      }),
    
    openApiYaml: async (): Promise<string> => {
      const cached = this.cache.get('schema:yaml');
      if (cached) return cached as string;
      
      const response = await fetch(`${this.baseURL}/schema.yaml`);
      const text = await response.text();
      this.cache.set('schema:yaml', text);
      return text;
    },
  };

  // Cache management
  clearCache(): void {
    this.cache.invalidate();
  }

  getCacheSize(): number {
    return this.cache.size();
  }

  invalidateCache(pattern: string): void {
    this.cache.invalidate(pattern);
  }
}

// Create and export optimized instance
export const api = new OptimizedApiClient(API_BASE_URL);

// Export types for convenience
export type * from '@/types/api';

// Utility functions
export const isApiError = (error: any): error is { message: string; status?: number } => {
  return error && typeof error.message === 'string';
};

export const handleApiError = (error: unknown): string => {
  if (isApiError(error)) {
    return error.message;
  }
  return 'An unexpected error occurred';
};

// Export utilities
export { debounce };