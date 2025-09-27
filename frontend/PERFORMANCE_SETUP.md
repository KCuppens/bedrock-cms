# 🚀 Performance Optimization Setup Guide

## Installation

To enable all performance optimizations, install the following dependencies:

```bash
# Core performance dependencies
npm install --save web-vitals

# Build optimization plugins
npm install --save-dev vite-plugin-compression vite-plugin-pwa

# Optional: Bundle analysis
npm install --save-dev rollup-plugin-visualizer

# Workbox for advanced service worker features
npm install --save-dev workbox-precaching workbox-routing workbox-strategies workbox-expiration workbox-cacheable-response workbox-background-sync
```

## Configuration Files Created

### ✅ Completed Implementations

1. **OptimizedImage Component** (`src/components/OptimizedImage.tsx`)
   - Lazy loading with Intersection Observer
   - Modern format support (WebP, AVIF)
   - Responsive images with srcSet
   - Blur placeholder while loading

2. **Service Worker** (`src/service-worker.ts`)
   - Offline support
   - Smart caching strategies
   - Background sync for API requests
   - Push notification support

3. **Web Vitals Monitoring** (`src/utils/webVitals.ts`)
   - Core Web Vitals tracking (LCP, FID, CLS, FCP, TTFB, INP)
   - Performance data collection
   - Analytics integration ready

4. **Performance Hooks** (`src/hooks/usePerformance.ts`)
   - Component render performance tracking
   - Long task monitoring
   - Layout shift detection
   - Network quality detection
   - Memory monitoring

5. **Resource Hints** (`index.html`)
   - DNS prefetch for external domains
   - Preconnect for critical resources
   - Preload for fonts and critical JS
   - Prefetch for likely user journeys

6. **Vite Configuration** (`vite.config.ts`)
   - PWA plugin configuration
   - Brotli & Gzip compression
   - Optimized chunk splitting
   - Reduced bundle size limits

7. **PWA Manifest** (`public/manifest.json`)
   - App installability
   - Shortcuts for quick access
   - Theme and display configuration

8. **Offline Fallback** (`public/offline.html`)
   - Beautiful offline page
   - Auto-reload when back online

## Usage Examples

### Using OptimizedImage Component

```tsx
import { OptimizedImage } from '@/components/OptimizedImage';

// Basic usage
<OptimizedImage
  src="/images/hero.jpg"
  alt="Hero image"
  width={1920}
  height={1080}
  priority // Load immediately for above-fold images
/>

// Responsive image
<OptimizedImage
  src="/images/product.jpg"
  alt="Product"
  sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
  className="rounded-lg"
/>
```

### Using Performance Hooks

```tsx
import { useRenderPerformance, useLongTaskMonitor } from '@/hooks/usePerformance';

function MyComponent() {
  // Track component performance
  const { renderCount, mountTime } = useRenderPerformance('MyComponent');

  // Monitor long tasks
  const { hasLongTasks, averageDuration } = useLongTaskMonitor();

  if (hasLongTasks) {
    console.warn(`Long tasks detected, avg: ${averageDuration}ms`);
  }

  return <div>...</div>;
}
```

### Lazy Loading with Intersection Observer

```tsx
import { useIntersectionObserver } from '@/hooks/usePerformance';

function LazyComponent() {
  const { observe, isIntersecting } = useIntersectionObserver({
    threshold: 0.1,
    rootMargin: '50px'
  });

  return (
    <div ref={observe}>
      {isIntersecting ? <ExpensiveComponent /> : <Placeholder />}
    </div>
  );
}
```

## Performance Checklist

### Quick Wins (Immediate Impact)
- [x] Resource hints in HTML head
- [x] Optimized images with lazy loading
- [x] Web Vitals monitoring
- [x] Service Worker for caching

### Medium Effort (1-2 days)
- [x] PWA configuration
- [x] Compression (Brotli & Gzip)
- [x] Performance monitoring hooks
- [ ] Critical CSS extraction
- [ ] Font optimization

### Advanced (1 week)
- [ ] Edge computing with Cloudflare Workers
- [ ] Advanced prefetching strategies
- [ ] A/B testing for performance
- [ ] Custom performance budgets

## Build Commands

```bash
# Development build with performance monitoring
npm run dev

# Production build with all optimizations
npm run build

# Analyze bundle size
npm run build -- --mode production
# Then check dist/stats.html

# Preview production build locally
npm run preview
```

## Environment Variables

Add to your `.env.production`:

```env
# Analytics endpoint for Web Vitals
VITE_ANALYTICS_ENDPOINT=https://your-analytics.com/vitals

# Enable PWA features
VITE_ENABLE_PWA=true

# Enable performance monitoring
VITE_ENABLE_MONITORING=true
```

## Testing Performance

### Local Testing
1. Run production build: `npm run build`
2. Serve locally: `npm run preview`
3. Open Chrome DevTools → Lighthouse
4. Run audit for Performance, PWA, etc.

### Online Testing
- [PageSpeed Insights](https://pagespeed.web.dev/)
- [WebPageTest](https://www.webpagetest.org/)
- [GTmetrix](https://gtmetrix.com/)

## Expected Improvements

With all optimizations implemented:

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| **Lighthouse Performance** | 60-70 | 90-95 | 90+ |
| **First Contentful Paint** | 2.5s | 1.2s | < 1.8s |
| **Largest Contentful Paint** | 4.0s | 2.0s | < 2.5s |
| **Total Blocking Time** | 500ms | 150ms | < 200ms |
| **Cumulative Layout Shift** | 0.25 | 0.05 | < 0.1 |
| **Bundle Size (gzipped)** | 500KB | 250KB | < 300KB |

## Monitoring Dashboard

Access performance metrics:

```typescript
// In browser console
localStorage.getItem('web-vitals-data')

// Get performance summary
import { getPerformanceSummary } from '@/utils/webVitals';
const summary = getPerformanceSummary();
console.table(summary);
```

## Troubleshooting

### Service Worker Issues
- Clear cache: Chrome DevTools → Application → Clear Storage
- Update manually: `navigator.serviceWorker.getRegistration().then(r => r.update())`

### Image Loading Issues
- Check network tab for failed requests
- Verify image formats are supported
- Check CORS headers for external images

### Performance Regressions
- Use bundle analyzer to identify large dependencies
- Check for unnecessary re-renders with React DevTools
- Monitor Web Vitals trends over time

## Next Steps

1. **Set up monitoring dashboard** - Track real user metrics
2. **Implement performance budgets** - Prevent regressions
3. **Add E2E performance tests** - Automate performance testing
4. **Configure CDN** - Serve assets from edge locations
5. **Implement critical CSS** - Inline above-fold styles

## Resources

- [Web.dev Performance](https://web.dev/performance/)
- [Core Web Vitals](https://web.dev/vitals/)
- [Chrome DevTools Performance](https://developer.chrome.com/docs/devtools/performance/)
- [Vite Performance Guide](https://vitejs.dev/guide/performance.html)
