import { onCLS, onFCP, onLCP, onTTFB, onINP, Metric } from 'web-vitals';

interface PerformanceData {
  metric: string;
  value: number;
  rating: 'good' | 'needs-improvement' | 'poor';
  delta?: number;
  id: string;
  navigationType: string;
  url: string;
  timestamp: number;
  userAgent: string;
  connection?: {
    effectiveType?: string;
    downlink?: number;
    rtt?: number;
  };
  memory?: {
    used?: number;
    total?: number;
    limit?: number;
  };
}

/**
 * Send performance metrics to analytics endpoint
 */
const sendToAnalytics = async (metric: Metric) => {
  // Get additional context
  const navigatorConnection = (navigator as any).connection;
  const navigatorMemory = (performance as any).memory;

  const data: PerformanceData = {
    metric: metric.name,
    value: Math.round(metric.value),
    rating: metric.rating,
    delta: metric.delta ? Math.round(metric.delta) : undefined,
    id: metric.id,
    navigationType: metric.navigationType || 'unknown',
    url: window.location.href,
    timestamp: Date.now(),
    userAgent: navigator.userAgent,
    connection: navigatorConnection ? {
      effectiveType: navigatorConnection.effectiveType,
      downlink: navigatorConnection.downlink,
      rtt: navigatorConnection.rtt,
    } : undefined,
    memory: navigatorMemory ? {
      used: Math.round(navigatorMemory.usedJSHeapSize / 1048576), // MB
      total: Math.round(navigatorMemory.totalJSHeapSize / 1048576), // MB
      limit: Math.round(navigatorMemory.jsHeapSizeLimit / 1048576), // MB
    } : undefined,
  };

  // Log in development
  if (import.meta.env.DEV) {
    console.log(`📊 Web Vital [${metric.name}]:`, {
      value: `${Math.round(metric.value)}${getMetricUnit(metric.name)}`,
      rating: metric.rating,
      ...(metric.delta && { delta: `${Math.round(metric.delta)}${getMetricUnit(metric.name)}` }),
    });
  }

  // Send to analytics endpoint using sendBeacon for reliability
  if (navigator.sendBeacon && import.meta.env.VITE_ANALYTICS_ENDPOINT) {
    const blob = new Blob([JSON.stringify(data)], { type: 'application/json' });
    navigator.sendBeacon(import.meta.env.VITE_ANALYTICS_ENDPOINT, blob);
  }

  // Also store in localStorage for offline analysis
  storeMetricLocally(data);
};

/**
 * Get the unit for a metric
 */
const getMetricUnit = (metricName: string): string => {
  switch (metricName) {
    case 'CLS':
      return '';
    case 'FCP':
    case 'LCP':
    case 'TTFB':
    case 'INP':
      return 'ms';
    default:
      return '';
  }
};

/**
 * Store metrics locally for offline analysis
 */
const storeMetricLocally = (data: PerformanceData) => {
  try {
    const key = 'web-vitals-data';
    const existing = localStorage.getItem(key);
    const metrics = existing ? JSON.parse(existing) : [];

    // Keep only last 100 metrics
    metrics.push(data);
    if (metrics.length > 100) {
      metrics.shift();
    }

    localStorage.setItem(key, JSON.stringify(metrics));
  } catch (e) {
    // Ignore errors (quota exceeded, etc.)
  }
};

/**
 * Initialize Web Vitals monitoring
 */
export const initWebVitals = () => {
  // Core Web Vitals
  onCLS(sendToAnalytics);  // Cumulative Layout Shift
  onFCP(sendToAnalytics);  // First Contentful Paint
  onLCP(sendToAnalytics);  // Largest Contentful Paint
  onTTFB(sendToAnalytics); // Time to First Byte
  onINP(sendToAnalytics);  // Interaction to Next Paint (replaces FID)
};

/**
 * Get stored Web Vitals data for debugging
 */
export const getStoredMetrics = (): PerformanceData[] => {
  try {
    const data = localStorage.getItem('web-vitals-data');
    return data ? JSON.parse(data) : [];
  } catch {
    return [];
  }
};

/**
 * Clear stored metrics
 */
export const clearStoredMetrics = () => {
  localStorage.removeItem('web-vitals-data');
};

/**
 * Get performance summary
 */
export const getPerformanceSummary = () => {
  const metrics = getStoredMetrics();

  if (metrics.length === 0) {
    return null;
  }

  const summary: Record<string, { avg: number; min: number; max: number; count: number }> = {};

  metrics.forEach(m => {
    if (!summary[m.metric]) {
      summary[m.metric] = { avg: 0, min: Infinity, max: -Infinity, count: 0 };
    }

    const s = summary[m.metric];
    s.count++;
    s.avg = (s.avg * (s.count - 1) + m.value) / s.count;
    s.min = Math.min(s.min, m.value);
    s.max = Math.max(s.max, m.value);
  });

  return summary;
};

/**
 * Custom performance marks
 */
export const performanceMark = (name: string) => {
  if (performance.mark) {
    performance.mark(name);
  }
};

/**
 * Custom performance measures
 */
export const performanceMeasure = (
  name: string,
  startMark: string,
  endMark?: string
) => {
  if (performance.measure) {
    try {
      performance.measure(name, startMark, endMark);

      // Get the measure and log it
      const measures = performance.getEntriesByName(name, 'measure');
      const lastMeasure = measures[measures.length - 1];

      if (lastMeasure && import.meta.env.DEV) {
        console.log(`⏱️ Performance [${name}]: ${Math.round(lastMeasure.duration)}ms`);
      }

      return lastMeasure?.duration;
    } catch (e) {
      // Ignore errors if marks don't exist
    }
  }
  return null;
};

/**
 * Monitor long tasks
 */
export const monitorLongTasks = (callback?: (duration: number) => void) => {
  if ('PerformanceObserver' in window) {
    try {
      const observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          // Long task is > 50ms
          if (entry.duration > 50) {
            if (import.meta.env.DEV) {
              console.warn(`⚠️ Long task detected: ${Math.round(entry.duration)}ms`);
            }
            callback?.(entry.duration);
          }
        }
      });

      observer.observe({ entryTypes: ['longtask'] });

      return () => observer.disconnect();
    } catch (e) {
      // Browser doesn't support longtask entries
    }
  }

  return () => {};
};

/**
 * Monitor layout shifts
 */
export const monitorLayoutShifts = (callback?: (value: number) => void) => {
  if ('PerformanceObserver' in window) {
    try {
      const observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          const layoutShiftEntry = entry as any;

          // Only report shifts without recent input (not user-triggered)
          if (!layoutShiftEntry.hadRecentInput && layoutShiftEntry.value > 0) {
            if (import.meta.env.DEV) {
              console.warn(`📐 Layout shift detected: ${layoutShiftEntry.value.toFixed(4)}`);
            }
            callback?.(layoutShiftEntry.value);
          }
        }
      });

      observer.observe({ entryTypes: ['layout-shift'] });

      return () => observer.disconnect();
    } catch (e) {
      // Browser doesn't support layout-shift entries
    }
  }

  return () => {};
};
