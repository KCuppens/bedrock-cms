/**
 * Speculation Rules API for prerendering and prefetching
 * This provides instant navigation to likely next pages
 */

interface SpeculationRule {
  source: 'list' | 'document';
  urls?: string[];
  where?: {
    href_matches?: string;
    selector_matches?: string;
    and?: SpeculationRule['where'][];
    or?: SpeculationRule['where'][];
    not?: SpeculationRule['where'];
  };
  eagerness?: 'immediate' | 'eager' | 'moderate' | 'conservative';
  requires?: string[];
}

interface SpeculationRules {
  prerender?: SpeculationRule[];
  prefetch?: SpeculationRule[];
}

class SpeculationManager {
  private scriptElement: HTMLScriptElement | null = null;
  private currentRules: SpeculationRules = {};
  private observer: IntersectionObserver | null = null;
  private performanceObserver: PerformanceObserver | null = null;

  constructor() {
    this.initializePerformanceMonitoring();
  }

  /**
   * Check if Speculation Rules API is supported
   */
  isSupported(): boolean {
    return HTMLScriptElement.supports && HTMLScriptElement.supports('speculationrules');
  }

  /**
   * Initialize speculation rules for the application
   */
  initialize(defaultRules?: SpeculationRules): void {
    if (!this.isSupported()) {
      console.log('Speculation Rules API not supported, falling back to traditional prefetching');
      this.setupFallbackPrefetching();
      return;
    }

    // Set default rules based on common navigation patterns
    const rules = defaultRules || this.getDefaultRules();
    this.updateRules(rules);

    // Setup adaptive speculation based on user behavior
    this.setupAdaptiveSpeculation();
  }

  /**
   * Get default speculation rules for the CMS
   */
  private getDefaultRules(): SpeculationRules {
    const currentPath = window.location.pathname;
    const rules: SpeculationRules = {
      prefetch: [
        {
          source: 'document',
          where: {
            and: [
              { href_matches: '/dashboard/*' },
              { not: { href_matches: '*.pdf' } }
            ]
          },
          eagerness: 'moderate'
        }
      ],
      prerender: []
    };

    // Add context-specific prerendering
    if (currentPath === '/dashboard') {
      rules.prerender?.push({
        source: 'list',
        urls: [
          '/dashboard/pages',
          '/dashboard/media',
          '/dashboard/blog-posts'
        ],
        eagerness: 'moderate'
      });
    } else if (currentPath.includes('/dashboard/pages')) {
      rules.prerender?.push({
        source: 'list',
        urls: [
          '/dashboard/pages/new',
          '/dashboard/blog-posts'
        ],
        eagerness: 'conservative'
      });
    }

    return rules;
  }

  /**
   * Update speculation rules
   */
  updateRules(rules: SpeculationRules): void {
    if (!this.isSupported()) return;

    // Remove existing script if present
    if (this.scriptElement) {
      this.scriptElement.remove();
    }

    // Create new script element
    this.scriptElement = document.createElement('script');
    this.scriptElement.type = 'speculationrules';
    this.scriptElement.textContent = JSON.stringify(rules);
    document.head.appendChild(this.scriptElement);

    this.currentRules = rules;
  }

  /**
   * Add URLs for prerendering
   */
  addPrerenderUrls(urls: string[]): void {
    const newRules = { ...this.currentRules };

    if (!newRules.prerender) {
      newRules.prerender = [];
    }

    // Find or create list rule
    let listRule = newRules.prerender.find(r => r.source === 'list');
    if (!listRule) {
      listRule = { source: 'list', urls: [], eagerness: 'moderate' };
      newRules.prerender.push(listRule);
    }

    // Add unique URLs
    const existingUrls = new Set(listRule.urls || []);
    urls.forEach(url => existingUrls.add(url));
    listRule.urls = Array.from(existingUrls);

    this.updateRules(newRules);
  }

  /**
   * Setup adaptive speculation based on user behavior
   */
  private setupAdaptiveSpeculation(): void {
    // Monitor hover/focus on links
    document.addEventListener('pointerover', (e) => {
      const link = (e.target as Element).closest('a');
      if (link && this.shouldSpeculate(link)) {
        this.speculateLink(link as HTMLAnchorElement);
      }
    }, { passive: true });

    // Monitor visible links for speculation
    this.setupIntersectionObserver();
  }

  /**
   * Setup intersection observer for visible links
   */
  private setupIntersectionObserver(): void {
    this.observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting && entry.intersectionRatio > 0.5) {
            const link = entry.target as HTMLAnchorElement;
            if (this.shouldSpeculate(link)) {
              // Prefetch visible important links
              this.prefetchUrl(link.href);
            }
          }
        });
      },
      {
        root: null,
        rootMargin: '50px',
        threshold: 0.5
      }
    );

    // Observe important navigation links
    document.querySelectorAll('a[data-prefetch], nav a').forEach(link => {
      this.observer?.observe(link);
    });
  }

  /**
   * Check if we should speculate a link
   */
  private shouldSpeculate(link: HTMLAnchorElement): boolean {
    // Don't speculate external links
    if (link.origin !== window.location.origin) return false;

    // Don't speculate downloads
    if (link.download) return false;

    // Don't speculate if user has data saver enabled
    if ((navigator as any).connection?.saveData) return false;

    // Don't speculate on slow connections
    const connection = (navigator as any).connection;
    if (connection && (connection.effectiveType === 'slow-2g' || connection.effectiveType === '2g')) {
      return false;
    }

    return true;
  }

  /**
   * Speculate a specific link
   */
  private speculateLink(link: HTMLAnchorElement): void {
    const url = link.href;
    const importance = link.dataset.importance || 'low';

    if (importance === 'high') {
      // Prerender high importance links
      this.addPrerenderUrls([url]);
    } else {
      // Prefetch others
      this.prefetchUrl(url);
    }
  }

  /**
   * Fallback prefetching for browsers without Speculation Rules API
   */
  private setupFallbackPrefetching(): void {
    // Use traditional link prefetching
    document.addEventListener('pointerover', (e) => {
      const link = (e.target as Element).closest('a');
      if (link && this.shouldSpeculate(link as HTMLAnchorElement)) {
        this.prefetchUrl((link as HTMLAnchorElement).href);
      }
    }, { passive: true });
  }

  /**
   * Prefetch a URL using link element
   */
  private prefetchUrl(url: string): void {
    // Check if already prefetched
    if (document.querySelector(`link[rel="prefetch"][href="${url}"]`)) {
      return;
    }

    const link = document.createElement('link');
    link.rel = 'prefetch';
    link.href = url;
    document.head.appendChild(link);
  }

  /**
   * Monitor performance of speculations
   */
  private initializePerformanceMonitoring(): void {
    if (!('PerformanceObserver' in window)) return;

    try {
      this.performanceObserver = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (entry.entryType === 'navigation') {
            const navEntry = entry as PerformanceNavigationTiming;

            // Log speculation success
            if ((navEntry as any).deliveryType === 'prerendered') {
              console.log(`✨ Page was prerendered: ${navEntry.name}`);
              this.trackSpeculationSuccess(navEntry.name, 'prerender');
            }
          }
        }
      });

      this.performanceObserver.observe({ type: 'navigation' });
    } catch (e) {
      // Performance observer not supported for this entry type
    }
  }

  /**
   * Track speculation success for analytics
   */
  private trackSpeculationSuccess(url: string, type: 'prerender' | 'prefetch'): void {
    // Send to analytics
    if (import.meta.env.DEV) {
      console.log(`Speculation success: ${type} for ${url}`);
    }

    // Could send to analytics endpoint
    if (navigator.sendBeacon && import.meta.env.VITE_ANALYTICS_ENDPOINT) {
      const data = {
        type: 'speculation_success',
        speculation_type: type,
        url,
        timestamp: Date.now()
      };

      navigator.sendBeacon(
        import.meta.env.VITE_ANALYTICS_ENDPOINT,
        JSON.stringify(data)
      );
    }
  }

  /**
   * Cleanup resources
   */
  destroy(): void {
    if (this.scriptElement) {
      this.scriptElement.remove();
    }

    if (this.observer) {
      this.observer.disconnect();
    }

    if (this.performanceObserver) {
      this.performanceObserver.disconnect();
    }
  }
}

// Export singleton instance
export const speculationManager = new SpeculationManager();

// Auto-initialize if supported
if (typeof window !== 'undefined') {
  // Wait for DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      speculationManager.initialize();
    });
  } else {
    speculationManager.initialize();
  }
}
