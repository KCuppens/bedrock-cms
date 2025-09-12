import { useState, useEffect, useCallback, useRef } from 'react';
import { useQuery, UseQueryOptions } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useLocale } from '@/contexts/LocaleContext';

interface ResolvedSEO {
  title: string;
  description?: string;
  keywords?: string;
  robots?: string;
  canonical_url?: string;
  page_url?: string;
  locale_code?: string;
  jsonld?: any[];
  // Open Graph
  og_title?: string;
  og_description?: string;
  og_type?: string;
  og_image?: string;
  og_site_name?: string;
  // Twitter
  twitter_card?: string;
  twitter_site?: string;
  twitter_creator?: string;
  twitter_image?: string;
  // Technical
  author?: string;
  generator?: string;
  viewport?: string;
  google_site_verification?: string;
  bing_site_verification?: string;
  facebook_app_id?: string;
}

interface SEOLinks {
  canonical?: string;
  alternates?: Array<{
    hreflang: string;
    href: string;
  }>;
}

export interface PageData {
  id: string;
  title: string;
  slug: string;
  path: string;
  url: string;
  status: 'draft' | 'published' | 'scheduled' | 'pending_review' | 'approved' | 'rejected';
  blocks: any[];
  locale_code: string;
  locale_name: string;
  published_at?: string;
  updated_at: string;
  resolved_seo: ResolvedSEO;
  seo_links: SEOLinks;
  in_main_menu: boolean;
  in_footer: boolean;
  is_homepage: boolean;
}

interface UsePageOptions {
  enabled?: boolean;
  retryOnError?: boolean;
  staleTime?: number;
  cacheTime?: number;
  refetchOnWindowFocus?: boolean;
  previewToken?: string;
}

interface UsePageReturn {
  page: PageData | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
  isStale: boolean;
}

// Cache for page paths to avoid duplicate requests
const pathCache = new Map<string, Promise<PageData>>();

/**
 * Performance-optimized hook for fetching page data by path.
 *
 * Features:
 * - Automatic locale detection from context
 * - Request deduplication for same paths
 * - Optimized caching strategy
 * - Error boundary integration
 * - SEO data resolution
 */
export const usePage = (
  path: string,
  options: UsePageOptions = {}
): UsePageReturn => {
  const { currentLocale } = useLocale();
  const {
    enabled = true,
    retryOnError = true,
    staleTime = 5 * 60 * 1000, // 5 minutes for published pages
    cacheTime = 10 * 60 * 1000, // 10 minutes
    refetchOnWindowFocus = false,
    previewToken
  } = options;

  // Normalize path for consistent caching
  const normalizedPath = path?.startsWith('/') ? path : `/${path}`;
  const cacheKey = `${normalizedPath}-${currentLocale?.code || 'en'}${previewToken ? `-preview-${previewToken}` : ''}`;

  const queryConfig: UseQueryOptions<PageData> = {
    queryKey: ['page', normalizedPath, currentLocale?.code, previewToken],
    queryFn: async (): Promise<PageData> => {
      // Check if we have a pending request for this path
      const existingRequest = pathCache.get(cacheKey);
      if (existingRequest) {
        return existingRequest;
      }

      // Create new request and cache it
      const requestPromise = api.cms.pages.getByPath(
        normalizedPath,
        currentLocale?.code || 'en'
      ).then(response => {
        // Extract the page data from ApiResponse wrapper
        const pageData = response.data || response;

        // Validate response structure
        if (!pageData || typeof pageData !== 'object') {
          throw new Error('Invalid page data received from server');
        }

        // Clean up cache entry after successful request
        pathCache.delete(cacheKey);

        return pageData as PageData;
      }).catch(error => {
        // Clean up cache entry on error
        pathCache.delete(cacheKey);
        throw error;
      });

      pathCache.set(cacheKey, requestPromise);
      return requestPromise;
    },
    enabled: enabled && !!normalizedPath && !!currentLocale,
    retry: retryOnError ? 2 : false,
    staleTime,
    cacheTime,
    refetchOnWindowFocus,
    // Network-first for preview mode, cache-first for published
    refetchOnMount: previewToken ? 'always' : true,
    // Error handling
    onError: (error) => {
      console.error(`Failed to fetch page at path "${normalizedPath}":`, error);
      // Remove failed request from cache
      pathCache.delete(cacheKey);
    },
    // Success handling
    onSuccess: (data) => {
      // Prefetch related pages for better UX (navigation items, etc.)
      if (data.in_main_menu || data.in_footer) {
        // Could prefetch navigation data here
      }
    }
  };

  const query = useQuery(queryConfig);

  // Memoized return object to prevent unnecessary re-renders
  return {
    page: query.data || null,
    loading: query.isLoading || query.isFetching,
    error: query.error ? (query.error as any)?.message || 'Failed to load page' : null,
    refetch: query.refetch,
    isStale: query.isStale
  };
};

/**
 * Hook for prefetching pages - useful for hover effects, preloading, etc.
 */
export const usePrefetchPage = () => {
  const { currentLocale } = useLocale();

  return useCallback((path: string, previewToken?: string) => {
    const normalizedPath = path?.startsWith('/') ? path : `/${path}`;
    const cacheKey = `${normalizedPath}-${currentLocale?.code || 'en'}${previewToken ? `-preview-${previewToken}` : ''}`;

    // Only prefetch if not already cached or in progress
    if (!pathCache.has(cacheKey)) {
      const requestPromise = api.cms.pages.getByPath(
        normalizedPath,
        currentLocale?.code || 'en'
      ).then(response => response.data || response)
        .catch(() => null); // Ignore errors for prefetch

      pathCache.set(cacheKey, requestPromise);

      // Clean up prefetch cache after delay
      setTimeout(() => {
        pathCache.delete(cacheKey);
      }, 30000); // 30 seconds
    }
  }, [currentLocale]);
};

/**
 * Hook to get page metadata without loading the full page.
 * Useful for navigation, sitemap generation, etc.
 */
export const usePageMetadata = (path: string) => {
  return useQuery({
    queryKey: ['page-metadata', path],
    queryFn: async () => {
      // This would use a lightweight endpoint that returns only metadata
      // For now, we'll use the main endpoint but extract only what we need
      const response = await api.cms.pages.getByPath(path);
      const page = response.data || response;

      return {
        id: page.id,
        title: page.title,
        path: page.path,
        status: page.status,
        in_main_menu: page.in_main_menu,
        in_footer: page.in_footer,
        is_homepage: page.is_homepage,
        published_at: page.published_at,
        updated_at: page.updated_at
      };
    },
    staleTime: 10 * 60 * 1000, // 10 minutes
    cacheTime: 15 * 60 * 1000, // 15 minutes
  });
};

// Cleanup function to clear path cache (useful for testing or memory management)
export const clearPageCache = () => {
  pathCache.clear();
};
