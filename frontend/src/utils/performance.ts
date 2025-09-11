import { onCLS, onFCP, onLCP, onTTFB, onINP, Metric } from 'web-vitals';

const vitalsUrl = 'https://vitals.vercel-analytics.com/v1/vitals';

function getConnectionSpeed() {
  const nav = navigator as any;
  const conn = nav.connection || nav.mozConnection || nav.webkitConnection;
  if (conn?.effectiveType) {
    return conn.effectiveType;
  }
  return 'unknown';
}

function sendToAnalytics(metric: Metric) {
  const body = {
    dsn: process.env.NODE_ENV === 'production' ? 'production' : 'development',
    id: metric.id,
    page: window.location.pathname,
    href: window.location.href,
    event_name: metric.name,
    value: metric.value.toString(),
    speed: getConnectionSpeed(),
  };

  // Log to console in development
  if (process.env.NODE_ENV === 'development') {
    console.log('[Web Vitals]', metric.name, metric.value, metric.rating);
  }

  // Send to analytics endpoint in production
  if (process.env.NODE_ENV === 'production' && window.location.hostname !== 'localhost') {
    const blob = new Blob([JSON.stringify(body)], { type: 'application/json' });
    if (navigator.sendBeacon) {
      navigator.sendBeacon(vitalsUrl, blob);
    } else {
      fetch(vitalsUrl, {
        body: JSON.stringify(body),
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        keepalive: true,
      });
    }
  }
}

export function reportWebVitals() {
  // Core Web Vitals
  onCLS(sendToAnalytics);  // Cumulative Layout Shift
  onFCP(sendToAnalytics);  // First Contentful Paint
  onLCP(sendToAnalytics);  // Largest Contentful Paint
  onTTFB(sendToAnalytics); // Time to First Byte
  onINP(sendToAnalytics);  // Interaction to Next Paint (replaces FID)
}

// Performance observer for custom metrics
export function measurePerformance(markName: string) {
  if (typeof window !== 'undefined' && window.performance && window.performance.mark) {
    window.performance.mark(markName);
  }
}

export function measurePerformanceEnd(markName: string, startMark: string) {
  if (typeof window !== 'undefined' && window.performance && window.performance.measure) {
    try {
      window.performance.measure(markName, startMark);
      const measure = window.performance.getEntriesByName(markName)[0];
      if (measure && process.env.NODE_ENV === 'development') {
        console.log(`[Performance] ${markName}: ${measure.duration.toFixed(2)}ms`);
      }
      return measure?.duration;
    } catch (e) {
      // Ignore errors from invalid marks
    }
  }
  return null;
}