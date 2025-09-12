import { lazy, ComponentType, LazyExoticComponent } from 'react';

// Cache for preloaded components
const preloadCache = new Map<string, Promise<any>>();

export interface PreloadableComponent<T extends ComponentType<any>> extends LazyExoticComponent<T> {
  preload: () => Promise<{ default: T }>;
}

/**
 * Enhanced lazy loading with preload capability
 *
 * @param importFunc Function that imports the component
 * @param chunkName Optional name for debugging
 * @returns Lazy component with preload method
 */
export function lazyWithPreload<T extends ComponentType<any>>(
  importFunc: () => Promise<{ default: T }>,
  chunkName?: string
): PreloadableComponent<T> {
  const cacheKey = chunkName || importFunc.toString();

  const preload = () => {
    if (!preloadCache.has(cacheKey)) {
      preloadCache.set(cacheKey, importFunc());
    }
    return preloadCache.get(cacheKey)!;
  };

  const LazyComponent = lazy(() => {
    // Use cached import if available
    if (preloadCache.has(cacheKey)) {
      return preloadCache.get(cacheKey)!;
    }

    // Otherwise import and cache
    const promise = importFunc();
    preloadCache.set(cacheKey, promise);
    return promise;
  }) as PreloadableComponent<T>;

  // Add preload method
  LazyComponent.preload = preload;

  return LazyComponent;
}

/**
 * Preload components based on route or user interaction
 *
 * @param components Array of preloadable components
 */
export function preloadComponents(components: PreloadableComponent<any>[]): void {
  components.forEach(component => {
    if (component.preload) {
      component.preload().catch(err => {
        console.error('Failed to preload component:', err);
      });
    }
  });
}

/**
 * Preload component on hover or focus
 *
 * @param component Component to preload
 * @returns Event handlers for preloading
 */
export function usePreloadOnInteraction<T extends ComponentType<any>>(
  component: PreloadableComponent<T>
) {
  const handleInteraction = () => {
    if (component.preload) {
      component.preload();
    }
  };

  return {
    onMouseEnter: handleInteraction,
    onFocus: handleInteraction,
    onTouchStart: handleInteraction,
  };
}

/**
 * Intersection Observer based preloading
 *
 * @param component Component to preload
 * @param rootMargin Margin for intersection observer
 */
export function preloadOnVisible<T extends ComponentType<any>>(
  component: PreloadableComponent<T>,
  rootMargin = '200px'
) {
  if (typeof window === 'undefined' || !('IntersectionObserver' in window)) {
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting && component.preload) {
          component.preload();
          observer.disconnect();
        }
      });
    },
    { rootMargin }
  );

  return observer;
}

/**
 * Preload components after main content is loaded
 *
 * @param components Components to preload
 * @param delay Delay in milliseconds
 */
export function preloadOnIdle(
  components: PreloadableComponent<any>[],
  delay = 2000
): void {
  if ('requestIdleCallback' in window) {
    requestIdleCallback(
      () => {
        preloadComponents(components);
      },
      { timeout: delay }
    );
  } else {
    // Fallback to setTimeout
    setTimeout(() => {
      preloadComponents(components);
    }, delay);
  }
}

/**
 * Network-aware preloading
 * Only preload on fast connections
 *
 * @param components Components to preload
 */
export function preloadOnFastConnection(
  components: PreloadableComponent<any>[]
): void {
  if ('connection' in navigator) {
    const connection = (navigator as any).connection;

    // Only preload on 4g or wifi
    if (connection.effectiveType === '4g' ||
        connection.type === 'wifi' ||
        !connection.saveData) {
      preloadComponents(components);
    }
  } else {
    // Can't detect, preload anyway
    preloadComponents(components);
  }
}