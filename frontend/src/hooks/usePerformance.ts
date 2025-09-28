import { useEffect, useRef, useCallback, useState } from 'react';
import {
  performanceMark,
  performanceMeasure,
  monitorLongTasks,
  monitorLayoutShifts
} from '@/utils/webVitals';

/**
 * Hook to measure component render performance
 */
export const useRenderPerformance = (componentName: string) => {
  const renderCount = useRef(0);
  const mountTime = useRef<number>(0);

  useEffect(() => {
    const startMark = `${componentName}-mount-start`;
    const endMark = `${componentName}-mount-end`;

    // Mark component mount start
    performanceMark(startMark);

    // Mark component mount end after paint
    requestAnimationFrame(() => {
      performanceMark(endMark);
      const duration = performanceMeasure(`${componentName}-mount`, startMark, endMark);

      if (duration) {
        mountTime.current = duration;

        if (import.meta.env.DEV && duration > 100) {
          console.warn(`⚠️ Slow component mount [${componentName}]: ${Math.round(duration)}ms`);
        }
      }
    });

    return () => {
      if (import.meta.env.DEV) {
        console.log(`📊 Component [${componentName}] rendered ${renderCount.current} times`);
      }
    };
  }, [componentName]);

  // Track render count
  useEffect(() => {
    renderCount.current++;
  });

  return {
    renderCount: renderCount.current,
    mountTime: mountTime.current,
  };
};

/**
 * Hook to monitor long tasks
 */
export const useLongTaskMonitor = (threshold = 50) => {
  const [longTasks, setLongTasks] = useState<number[]>([]);

  useEffect(() => {
    const cleanup = monitorLongTasks((duration) => {
      if (duration > threshold) {
        setLongTasks(prev => [...prev, duration].slice(-10)); // Keep last 10
      }
    });

    return cleanup;
  }, [threshold]);

  return {
    longTasks,
    hasLongTasks: longTasks.length > 0,
    averageDuration: longTasks.length > 0
      ? longTasks.reduce((a, b) => a + b, 0) / longTasks.length
      : 0,
  };
};

/**
 * Hook to monitor layout shifts
 */
export const useLayoutShiftMonitor = () => {
  const [layoutShifts, setLayoutShifts] = useState<number[]>([]);
  const [cumulativeShift, setCumulativeShift] = useState(0);

  useEffect(() => {
    const cleanup = monitorLayoutShifts((value) => {
      setLayoutShifts(prev => [...prev, value].slice(-20)); // Keep last 20
      setCumulativeShift(prev => prev + value);
    });

    return cleanup;
  }, []);

  return {
    layoutShifts,
    cumulativeShift,
    shiftCount: layoutShifts.length,
  };
};

/**
 * Hook to lazy load components when idle
 */
export const useIdleCallback = (callback: () => void, options?: IdleRequestOptions) => {
  const callbackRef = useRef(callback);
  const handleRef = useRef<number>();

  useEffect(() => {
    callbackRef.current = callback;
  });

  const schedule = useCallback(() => {
    if ('requestIdleCallback' in window) {
      handleRef.current = window.requestIdleCallback(
        () => callbackRef.current(),
        options
      );
    } else {
      // Fallback for unsupported browsers
      handleRef.current = window.setTimeout(() => callbackRef.current(), 1);
    }
  }, [options]);

  const cancel = useCallback(() => {
    if (handleRef.current) {
      if ('cancelIdleCallback' in window) {
        window.cancelIdleCallback(handleRef.current);
      } else {
        clearTimeout(handleRef.current);
      }
    }
  }, []);

  useEffect(() => {
    return cancel;
  }, [cancel]);

  return { schedule, cancel };
};

/**
 * Hook for intersection observer (lazy loading)
 */
export const useIntersectionObserver = (
  options: IntersectionObserverInit = {}
) => {
  const [entry, setEntry] = useState<IntersectionObserverEntry | null>(null);
  const [isIntersecting, setIsIntersecting] = useState(false);
  const observerRef = useRef<IntersectionObserver | null>(null);
  const elementRef = useRef<Element | null>(null);

  const observe = useCallback((element: Element | null) => {
    if (observerRef.current) {
      observerRef.current.disconnect();
    }

    if (!element) {
      setEntry(null);
      setIsIntersecting(false);
      return;
    }

    observerRef.current = new IntersectionObserver(
      ([entry]) => {
        setEntry(entry);
        setIsIntersecting(entry.isIntersecting);
      },
      {
        threshold: 0,
        rootMargin: '50px',
        ...options,
      }
    );

    observerRef.current.observe(element);
    elementRef.current = element;
  }, [options]);

  useEffect(() => {
    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
    };
  }, []);

  return {
    observe,
    entry,
    isIntersecting,
  };
};

/**
 * Hook to prefetch links on hover
 */
export const useLinkPrefetch = () => {
  const prefetchedUrls = useRef(new Set<string>());

  const prefetch = useCallback((url: string) => {
    if (prefetchedUrls.current.has(url)) return;

    const link = document.createElement('link');
    link.rel = 'prefetch';
    link.href = url;
    document.head.appendChild(link);
    prefetchedUrls.current.add(url);

    if (import.meta.env.DEV) {
      console.log(`🔗 Prefetched: ${url}`);
    }
  }, []);

  const prefetchOnHover = useCallback((element: HTMLElement | null) => {
    if (!element) return;

    const handleMouseEnter = (e: MouseEvent) => {
      const link = (e.currentTarget as HTMLAnchorElement).href;
      if (link && !link.includes('#')) {
        // Use requestIdleCallback for prefetching
        if ('requestIdleCallback' in window) {
          requestIdleCallback(() => prefetch(link));
        } else {
          setTimeout(() => prefetch(link), 100);
        }
      }
    };

    element.addEventListener('mouseenter', handleMouseEnter);

    return () => {
      element.removeEventListener('mouseenter', handleMouseEnter);
    };
  }, [prefetch]);

  return { prefetch, prefetchOnHover };
};

/**
 * Hook to optimize animations based on user preference
 */
export const useReducedMotion = () => {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(
    () => window.matchMedia('(prefers-reduced-motion: reduce)').matches
  );

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');

    const handleChange = (e: MediaQueryListEvent) => {
      setPrefersReducedMotion(e.matches);
    };

    // Modern browsers
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    }

    // Legacy browsers
    mediaQuery.addListener(handleChange);
    return () => mediaQuery.removeListener(handleChange);
  }, []);

  return prefersReducedMotion;
};

/**
 * Hook to detect network connection quality
 */
export const useNetworkQuality = () => {
  const [connectionQuality, setConnectionQuality] = useState<{
    effectiveType?: string;
    downlink?: number;
    rtt?: number;
    saveData?: boolean;
  }>({});

  useEffect(() => {
    const connection = (navigator as any).connection ||
                      (navigator as any).mozConnection ||
                      (navigator as any).webkitConnection;

    if (!connection) return;

    const updateConnectionQuality = () => {
      setConnectionQuality({
        effectiveType: connection.effectiveType,
        downlink: connection.downlink,
        rtt: connection.rtt,
        saveData: connection.saveData,
      });
    };

    updateConnectionQuality();

    connection.addEventListener('change', updateConnectionQuality);
    return () => connection.removeEventListener('change', updateConnectionQuality);
  }, []);

  const isSlowConnection = connectionQuality.effectiveType === '2g' ||
                          connectionQuality.effectiveType === 'slow-2g';

  const shouldReduceData = connectionQuality.saveData || isSlowConnection;

  return {
    ...connectionQuality,
    isSlowConnection,
    shouldReduceData,
  };
};

/**
 * Hook for memory monitoring
 */
export const useMemoryMonitor = () => {
  const [memory, setMemory] = useState<{
    used: number;
    total: number;
    limit: number;
    percentage: number;
  } | null>(null);

  useEffect(() => {
    if (!(performance as any).memory) return;

    const updateMemory = () => {
      const perfMemory = (performance as any).memory;
      const used = perfMemory.usedJSHeapSize;
      const total = perfMemory.totalJSHeapSize;
      const limit = perfMemory.jsHeapSizeLimit;

      setMemory({
        used: Math.round(used / 1048576), // Convert to MB
        total: Math.round(total / 1048576),
        limit: Math.round(limit / 1048576),
        percentage: Math.round((used / limit) * 100),
      });
    };

    updateMemory();
    const interval = setInterval(updateMemory, 5000); // Update every 5 seconds

    return () => clearInterval(interval);
  }, []);

  const isHighMemoryUsage = memory ? memory.percentage > 80 : false;

  return {
    memory,
    isHighMemoryUsage,
  };
};

/**
 * Hook to debounce values for better performance
 */
export const useDebounce = <T>(value: T, delay: number): T => {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
};

/**
 * Hook to throttle function calls for better performance
 */
export const useThrottle = <T extends (...args: any[]) => void>(
  fn: T,
  limit: number
): T => {
  const inThrottle = useRef(false);

  return useCallback(
    ((...args: Parameters<T>) => {
      if (!inThrottle.current) {
        fn(...args);
        inThrottle.current = true;
        setTimeout(() => {
          inThrottle.current = false;
        }, limit);
      }
    }) as T,
    [fn, limit]
  );
};

/**
 * Hook to defer rendering until next tick for better performance
 */
export const useDeferredValue = <T>(value: T): T => {
  const [deferredValue, setDeferredValue] = useState(value);

  useEffect(() => {
    const handle = setTimeout(() => {
      setDeferredValue(value);
    }, 0);

    return () => clearTimeout(handle);
  }, [value]);

  return deferredValue;
};

/**
 * Hook for memoized calculations with dependency tracking
 */
export const useMemoizedValue = <T>(
  factory: () => T,
  deps: React.DependencyList
): T => {
  const memoRef = useRef<{ value: T; deps: React.DependencyList }>();

  if (
    !memoRef.current ||
    deps.some((dep, i) => dep !== memoRef.current!.deps[i])
  ) {
    memoRef.current = {
      value: factory(),
      deps,
    };
  }

  return memoRef.current.value;
};

/**
 * Hook for component visibility tracking
 */
export const useVisibility = () => {
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    const handleVisibilityChange = () => {
      setIsVisible(!document.hidden);
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, []);

  return isVisible;
};

/**
 * Hook for focus management and performance
 */
export const useFocusWithin = () => {
  const [isFocused, setIsFocused] = useState(false);
  const ref = useRef<HTMLElement>(null);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    const handleFocusIn = () => setIsFocused(true);
    const handleFocusOut = (e: FocusEvent) => {
      if (!element.contains(e.relatedTarget as Node)) {
        setIsFocused(false);
      }
    };

    element.addEventListener('focusin', handleFocusIn);
    element.addEventListener('focusout', handleFocusOut);

    return () => {
      element.removeEventListener('focusin', handleFocusIn);
      element.removeEventListener('focusout', handleFocusOut);
    };
  }, []);

  return { ref, isFocused };
};

/**
 * Hook for lazy loading images with placeholder support
 */
export const useLazyImage = (src: string, placeholder?: string) => {
  const [imageSrc, setImageSrc] = useState(placeholder || '');
  const [isLoaded, setIsLoaded] = useState(false);
  const [isError, setIsError] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);

  const { observe } = useIntersectionObserver({
    threshold: 0.1,
    rootMargin: '50px',
  });

  useEffect(() => {
    if (imgRef.current) {
      observe(imgRef.current);
    }
  }, [observe]);

  const { isIntersecting } = useIntersectionObserver();

  useEffect(() => {
    if (isIntersecting && src && !isLoaded && !isError) {
      const img = new Image();

      img.onload = () => {
        setImageSrc(src);
        setIsLoaded(true);
      };

      img.onerror = () => {
        setIsError(true);
      };

      img.src = src;
    }
  }, [isIntersecting, src, isLoaded, isError]);

  return {
    imgRef,
    src: imageSrc,
    isLoaded,
    isError,
  };
};

/**
 * Hook for tracking scroll performance
 */
export const useScrollPerformance = () => {
  const [scrollMetrics, setScrollMetrics] = useState({
    scrollY: 0,
    scrollDirection: 'up' as 'up' | 'down',
    scrollSpeed: 0,
    isScrolling: false,
  });

  const lastScrollY = useRef(0);
  const scrollTimeout = useRef<NodeJS.Timeout>();

  const handleScroll = useThrottle(() => {
    const currentScrollY = window.scrollY;
    const direction = currentScrollY > lastScrollY.current ? 'down' : 'up';
    const speed = Math.abs(currentScrollY - lastScrollY.current);

    setScrollMetrics({
      scrollY: currentScrollY,
      scrollDirection: direction,
      scrollSpeed: speed,
      isScrolling: true,
    });

    lastScrollY.current = currentScrollY;

    // Clear existing timeout
    if (scrollTimeout.current) {
      clearTimeout(scrollTimeout.current);
    }

    // Set scrolling to false after scroll ends
    scrollTimeout.current = setTimeout(() => {
      setScrollMetrics(prev => ({ ...prev, isScrolling: false }));
    }, 150);
  }, 16); // ~60fps

  useEffect(() => {
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, [handleScroll]);

  return scrollMetrics;
};
