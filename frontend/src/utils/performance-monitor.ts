import { onCLS, onFCP, onINP, onLCP, onTTFB, Metric } from 'web-vitals';

// Performance thresholds
const THRESHOLDS = {
  FCP: { good: 1800, poor: 3000 },
  LCP: { good: 2500, poor: 4000 },
  INP: { good: 200, poor: 500 }, // INP replaced FID
  CLS: { good: 0.1, poor: 0.25 },
  TTFB: { good: 800, poor: 1800 },
};

// Performance data collection
interface PerformanceData {
  metric: string;
  value: number;
  rating: 'good' | 'needs-improvement' | 'poor';
  timestamp: number;
  url: string;
  userAgent: string;
  connection?: string;
  memory?: number;
}

class PerformanceMonitor {
  private data: PerformanceData[] = [];
  private reportEndpoint: string | null = null;
  private debug = false;
  private sessionId: string;
  private observer: PerformanceObserver | null = null;

  constructor(config?: { 
    reportEndpoint?: string; 
    debug?: boolean;
  }) {
    this.reportEndpoint = config?.reportEndpoint || null;
    this.debug = config?.debug || false;
    this.sessionId = this.generateSessionId();
    
    // Initialize monitoring
    this.initWebVitals();
    this.initResourceTiming();
    this.initLongTasks();
    this.initMemoryMonitoring();
    this.initErrorTracking();
  }

  private generateSessionId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  // Initialize Web Vitals monitoring
  private initWebVitals(): void {
    // First Contentful Paint
    onFCP(this.handleMetric.bind(this));
    
    // Largest Contentful Paint
    onLCP(this.handleMetric.bind(this));
    
    // Interaction to Next Paint (replaced FID)
    onINP(this.handleMetric.bind(this));
    
    // Cumulative Layout Shift
    onCLS(this.handleMetric.bind(this));
    
    // Time to First Byte
    onTTFB(this.handleMetric.bind(this));
  }

  // Handle Web Vitals metrics
  private handleMetric(metric: Metric): void {
    const rating = this.getRating(metric.name, metric.value);
    
    const data: PerformanceData = {
      metric: metric.name,
      value: Math.round(metric.value),
      rating,
      timestamp: Date.now(),
      url: window.location.href,
      userAgent: navigator.userAgent,
      connection: (navigator as any).connection?.effectiveType,
      memory: (performance as any).memory?.usedJSHeapSize,
    };

    this.data.push(data);
    
    if (this.debug) {
      console.log(`[Performance] ${metric.name}: ${Math.round(metric.value)}ms (${rating})`);
    }

    // Send to analytics if configured
    if (this.reportEndpoint) {
      this.reportMetric(data);
    }

    // Trigger warning for poor performance
    if (rating === 'poor') {
      this.handlePoorPerformance(metric.name, metric.value);
    }
  }

  // Get rating based on thresholds
  private getRating(metricName: string, value: number): 'good' | 'needs-improvement' | 'poor' {
    const threshold = THRESHOLDS[metricName as keyof typeof THRESHOLDS];
    if (!threshold) return 'good';

    if (value <= threshold.good) return 'good';
    if (value <= threshold.poor) return 'needs-improvement';
    return 'poor';
  }

  // Monitor resource timing
  private initResourceTiming(): void {
    if (!('PerformanceObserver' in window)) return;

    try {
      this.observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (entry.entryType === 'resource') {
            const resource = entry as PerformanceResourceTiming;
            
            // Track slow resources
            if (resource.duration > 1000) {
              if (this.debug) {
                console.warn(`[Performance] Slow resource: ${resource.name} (${Math.round(resource.duration)}ms)`);
              }
              
              this.trackSlowResource(resource);
            }
          }
        }
      });

      this.observer.observe({ entryTypes: ['resource'] });
    } catch (error) {
      console.error('Failed to initialize resource timing:', error);
    }
  }

  // Track slow resources
  private trackSlowResource(resource: PerformanceResourceTiming): void {
    const data = {
      type: 'slow-resource',
      name: resource.name,
      duration: Math.round(resource.duration),
      size: resource.transferSize,
      timestamp: Date.now(),
      sessionId: this.sessionId,
    };

    if (this.reportEndpoint) {
      this.sendBeacon(this.reportEndpoint, data);
    }
  }

  // Monitor long tasks
  private initLongTasks(): void {
    if (!('PerformanceObserver' in window)) return;

    try {
      const longTaskObserver = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (this.debug) {
            console.warn(`[Performance] Long task detected: ${Math.round(entry.duration)}ms`);
          }
          
          this.trackLongTask(entry);
        }
      });

      longTaskObserver.observe({ entryTypes: ['longtask'] });
    } catch (error) {
      // Long task API might not be supported
    }
  }

  // Track long tasks
  private trackLongTask(entry: PerformanceEntry): void {
    const data = {
      type: 'long-task',
      duration: Math.round(entry.duration),
      timestamp: Date.now(),
      sessionId: this.sessionId,
    };

    if (this.reportEndpoint) {
      this.sendBeacon(this.reportEndpoint, data);
    }
  }

  // Monitor memory usage
  private memoryInterval: NodeJS.Timeout | null = null;
  
  private initMemoryMonitoring(): void {
    if (!(performance as any).memory) return;

    this.memoryInterval = setInterval(() => {
      const memory = (performance as any).memory;
      const usedMemory = memory.usedJSHeapSize / 1048576; // Convert to MB
      const totalMemory = memory.jsHeapSizeLimit / 1048576;
      const usage = (usedMemory / totalMemory) * 100;

      if (usage > 90) {
        if (this.debug) {
          console.warn(`[Performance] High memory usage: ${usedMemory.toFixed(2)}MB (${usage.toFixed(1)}%)`);
        }
        
        this.trackHighMemory(usedMemory, usage);
      }
    }, 60000); // Check every 60 seconds instead of 30
  }

  // Track high memory usage
  private trackHighMemory(usedMemory: number, usage: number): void {
    const data = {
      type: 'high-memory',
      usedMemory: Math.round(usedMemory),
      usage: Math.round(usage),
      timestamp: Date.now(),
      sessionId: this.sessionId,
    };

    if (this.reportEndpoint) {
      this.sendBeacon(this.reportEndpoint, data);
    }
  }

  // Track JavaScript errors
  private initErrorTracking(): void {
    window.addEventListener('error', (event) => {
      const data = {
        type: 'js-error',
        message: event.message,
        filename: event.filename,
        line: event.lineno,
        column: event.colno,
        stack: event.error?.stack,
        timestamp: Date.now(),
        sessionId: this.sessionId,
      };

      if (this.debug) {
        console.error('[Performance] JavaScript error:', data);
      }

      if (this.reportEndpoint) {
        this.sendBeacon(this.reportEndpoint, data);
      }
    });

    window.addEventListener('unhandledrejection', (event) => {
      const data = {
        type: 'unhandled-rejection',
        reason: event.reason?.toString(),
        timestamp: Date.now(),
        sessionId: this.sessionId,
      };

      if (this.debug) {
        console.error('[Performance] Unhandled rejection:', data);
      }

      if (this.reportEndpoint) {
        this.sendBeacon(this.reportEndpoint, data);
      }
    });
  }

  // Handle poor performance
  private handlePoorPerformance(metric: string, value: number): void {
    // Log to console in development
    if (this.debug) {
      console.warn(`[Performance Alert] Poor ${metric}: ${Math.round(value)}ms`);
    }

    // Could trigger user-facing warnings or adjustments
    if (metric === 'LCP' && value > 4000) {
      // Consider reducing image quality or lazy loading
      this.optimizeImages();
    }

    if (metric === 'INP' && value > 500) {
      // Consider deferring non-critical JavaScript
      this.deferNonCriticalJS();
    }
  }

  // Optimize images on poor LCP
  private optimizeImages(): void {
    const images = document.querySelectorAll('img[src]');
    images.forEach((img: Element) => {
      const imgElement = img as HTMLImageElement;
      if (!imgElement.loading) {
        imgElement.loading = 'lazy';
      }
    });
  }

  // Defer non-critical JavaScript
  private deferNonCriticalJS(): void {
    // Implementation would defer loading of non-critical scripts
    if (this.debug) {
      console.log('[Performance] Deferring non-critical JavaScript');
    }
  }

  // Report metric to analytics
  private reportMetric(data: PerformanceData): void {
    if (!this.reportEndpoint) return;

    // Use sendBeacon for reliability
    this.sendBeacon(this.reportEndpoint, {
      ...data,
      sessionId: this.sessionId,
    });
  }

  // Send data using beacon API
  private sendBeacon(url: string, data: any): void {
    if ('sendBeacon' in navigator) {
      navigator.sendBeacon(url, JSON.stringify(data));
    } else {
      // Fallback to fetch
      fetch(url, {
        method: 'POST',
        body: JSON.stringify(data),
        headers: { 'Content-Type': 'application/json' },
        keepalive: true,
      }).catch(() => {
        // Silently fail
      });
    }
  }

  // Get current performance data
  getMetrics(): PerformanceData[] {
    return this.data;
  }

  // Get performance summary
  getSummary(): {
    metrics: Record<string, { value: number; rating: string }>;
    score: number;
  } {
    const summary: Record<string, { value: number; rating: string }> = {};
    let totalScore = 0;
    let metricCount = 0;

    for (const item of this.data) {
      if (!summary[item.metric]) {
        summary[item.metric] = {
          value: item.value,
          rating: item.rating,
        };
        
        // Calculate score
        if (item.rating === 'good') totalScore += 100;
        else if (item.rating === 'needs-improvement') totalScore += 50;
        else totalScore += 0;
        
        metricCount++;
      }
    }

    return {
      metrics: summary,
      score: metricCount > 0 ? Math.round(totalScore / metricCount) : 0,
    };
  }

  // Mark custom timing
  mark(name: string): void {
    performance.mark(name);
  }

  // Measure between marks
  measure(name: string, startMark: string, endMark?: string): void {
    try {
      if (endMark) {
        performance.measure(name, startMark, endMark);
      } else {
        performance.measure(name, startMark);
      }
      
      const measures = performance.getEntriesByName(name, 'measure');
      const lastMeasure = measures[measures.length - 1];
      
      if (lastMeasure && this.debug) {
        console.log(`[Performance] ${name}: ${Math.round(lastMeasure.duration)}ms`);
      }
    } catch (error) {
      console.error('Failed to measure performance:', error);
    }
  }

  // Clean up
  destroy(): void {
    if (this.observer) {
      this.observer.disconnect();
    }
    if (this.memoryInterval) {
      clearInterval(this.memoryInterval);
      this.memoryInterval = null;
    }
  }
}

// Create singleton instance
let instance: PerformanceMonitor | null = null;

export const initPerformanceMonitoring = (config?: {
  reportEndpoint?: string;
  debug?: boolean;
}): PerformanceMonitor => {
  if (!instance) {
    instance = new PerformanceMonitor(config);
  }
  return instance;
};

export const getPerformanceMonitor = (): PerformanceMonitor | null => {
  return instance;
};

// Export for use in components
export default PerformanceMonitor;