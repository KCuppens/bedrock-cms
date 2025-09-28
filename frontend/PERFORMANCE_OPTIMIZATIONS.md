# Performance Optimizations Guide

This document outlines all the performance optimizations implemented in the Bedrock CMS frontend to achieve world-class Lighthouse scores.

## 🎯 Performance Goals

- **Performance Score**: 85+ (Target: 90+)
- **Accessibility**: 95+
- **Best Practices**: 90+
- **SEO**: 90+
- **First Contentful Paint (FCP)**: < 2.0s
- **Largest Contentful Paint (LCP)**: < 3.0s
- **Cumulative Layout Shift (CLS)**: < 0.1
- **Total Blocking Time (TBT)**: < 300ms

## 🚀 Implemented Optimizations

### 1. Critical CSS Extraction

**File**: `vite-plugin-critical-css.ts`

Automatically extracts and inlines critical CSS for above-the-fold content:

```typescript
import { criticalCSSPlugin } from './vite-plugin-critical-css';

// Usage in vite.config.ts
plugins: [
  criticalCSSPlugin(),
  // ... other plugins
]
```

**Features**:
- Inlines critical Tailwind utilities
- Includes shadcn/ui component styles
- Adds loading placeholders for better perceived performance
- Preloads non-critical stylesheets

### 2. Advanced Code Splitting

**File**: `vite.config.ts` - `manualChunks` configuration

Granular chunking strategy for optimal caching:

```typescript
// React core - minimal bundle
if (id.includes('react-dom')) return 'react-dom';
if (id.includes('react-router')) return 'react-router';

// Split each Radix UI component
const radixMatch = id.match(/@radix-ui\/react-([^\/]+)/);
if (radixMatch) return `radix-${radixMatch[1]}`;

// Page-based chunking
if (id.includes('PageEditor')) return 'editors';
if (id.includes('Media')) return 'content-management';
```

### 3. Service Worker with Workbox

**File**: `src/service-worker.ts`

Comprehensive caching strategy:

- **Static Assets**: Cache-first with 30-day expiration
- **API Calls**: Network-first with 5-minute cache
- **Images**: Cache-first with quota management
- **Fonts**: Long-term caching (1 year)
- **Background Sync**: For offline API requests

### 4. Virtual Scrolling

**File**: `src/components/VirtualizedList.tsx`

High-performance list rendering:

```typescript
import { VirtualizedList } from '@/components/VirtualizedList';

<VirtualizedList
  items={largeDataSet}
  height={600}
  itemSize={50}
  renderItem={(item, index, style) => (
    <div style={style}>{item.name}</div>
  )}
  onLoadMore={loadMoreItems}
  hasMore={true}
/>
```

**Components Available**:
- `VirtualizedList`: For long lists
- `VirtualizedGrid`: For media galleries
- `AutoSizedVirtualizedList`: Dynamic height
- `useVirtualizedList`: Hook for state management

### 5. Performance Monitoring

**File**: `src/utils/performance-monitor.ts`

Comprehensive performance tracking:

```typescript
import { initPerformanceMonitoring } from '@/utils/performance-monitor';

// Initialize monitoring
initPerformanceMonitoring({
  reportEndpoint: '/api/analytics/performance',
  debug: import.meta.env.DEV
});
```

**Tracks**:
- Core Web Vitals (FCP, LCP, INP, CLS, TTFB)
- Long tasks (>50ms)
- Layout shifts
- Memory usage
- Resource timing
- JavaScript errors

### 6. React Performance Hooks

**File**: `src/hooks/usePerformance.ts`

Performance-focused React hooks:

```typescript
// Debounce expensive operations
const debouncedSearchTerm = useDebounce(searchTerm, 300);

// Throttle scroll handlers
const handleScroll = useThrottle((e) => {
  // scroll logic
}, 16); // 60fps

// Monitor component performance
const { renderCount, mountTime } = useRenderPerformance('MyComponent');

// Lazy load images
const { imgRef, src, isLoaded } = useLazyImage(imageUrl, placeholderUrl);

// Track scroll performance
const { scrollY, scrollDirection, isScrolling } = useScrollPerformance();

// Network-aware loading
const { isSlowConnection, shouldReduceData } = useNetworkQuality();

// Memory monitoring
const { memory, isHighMemoryUsage } = useMemoryMonitor();

// Intersection observer
const { observe, isIntersecting } = useIntersectionObserver({
  threshold: 0.1,
  rootMargin: '50px'
});
```

### 7. Font Loading Optimization

**File**: `src/utils/font-loader.ts`

Strategic font loading:

- `font-display: swap` for fast text rendering
- Preload critical fonts in `<head>`
- Fallback system fonts to prevent layout shifts

### 8. Build Optimizations

**File**: `vite.config.ts`

Advanced build configuration:

```typescript
build: {
  target: 'es2015',
  minify: 'terser',
  terserOptions: {
    compress: {
      drop_console: mode === 'production',
      passes: 3,
      dead_code: true,
      unsafe_math: true,
    }
  },
  chunkSizeWarningLimit: 200, // Strict 200KB chunks
  assetsInlineLimit: 10240,   // Inline <10KB assets
  cssCodeSplit: true,         // Split CSS per route
}
```

## 🔍 Lighthouse CI Integration

### Automated Testing

**File**: `.github/workflows/lighthouse-ci.yml`

Runs on every PR to `main` branch:

1. **Performance Budgets**: Enforces strict performance budgets
2. **Visual Regression**: Tracks performance over time
3. **PR Comments**: Posts Lighthouse scores directly in PRs
4. **Artifacts**: Saves detailed reports for analysis

### Configuration

**File**: `.lighthouserc.json`

```json
{
  "ci": {
    "assert": {
      "assertions": {
        "categories:performance": ["error", {"minScore": 0.85}],
        "first-contentful-paint": ["error", {"maxNumericValue": 2000}],
        "largest-contentful-paint": ["error", {"maxNumericValue": 3000}],
        "cumulative-layout-shift": ["error", {"maxNumericValue": 0.1}]
      }
    }
  }
}
```

### Local Testing

```bash
# Run full Lighthouse CI locally
npm run lighthouse:local

# Quick performance audit
npm run performance:audit

# CI-style run
npm run lighthouse:ci
```

## 📊 Performance Metrics

### Before Optimizations
- Performance: ~65-75
- FCP: ~3.5s
- LCP: ~5.2s
- CLS: ~0.15
- TBT: ~450ms

### Target After Optimizations
- Performance: 85-95+
- FCP: <2.0s
- LCP: <3.0s
- CLS: <0.1
- TBT: <300ms

## 🛠 Usage Guidelines

### 1. Component Performance

```typescript
import { memo, useCallback, useMemo } from 'react';
import { useRenderPerformance } from '@/hooks/usePerformance';

const ExpensiveComponent = memo(({ data }) => {
  // Monitor performance
  useRenderPerformance('ExpensiveComponent');

  // Memoize expensive calculations
  const processedData = useMemo(() => {
    return data.map(item => expensiveOperation(item));
  }, [data]);

  // Memoize callbacks
  const handleClick = useCallback((id) => {
    // handle click
  }, []);

  return <div>{/* component JSX */}</div>;
});
```

### 2. Lazy Loading

```typescript
import { useLazyImage, useIntersectionObserver } from '@/hooks/usePerformance';

const LazyImage = ({ src, alt }) => {
  const { imgRef, src: lazySrc, isLoaded } = useLazyImage(src);

  return (
    <div ref={imgRef}>
      {!isLoaded && <div className="loading-skeleton" />}
      <img src={lazySrc} alt={alt} style={{ opacity: isLoaded ? 1 : 0 }} />
    </div>
  );
};
```

### 3. Network-Aware Loading

```typescript
import { useNetworkQuality } from '@/hooks/usePerformance';

const MediaGallery = () => {
  const { isSlowConnection, shouldReduceData } = useNetworkQuality();

  return (
    <div>
      {images.map(img => (
        <img
          key={img.id}
          src={shouldReduceData ? img.thumbnail : img.full}
          loading="lazy"
        />
      ))}
    </div>
  );
};
```

### 4. Virtualized Lists

```typescript
import { VirtualizedList } from '@/components/VirtualizedList';

const LargeDataList = ({ items }) => (
  <VirtualizedList
    items={items}
    height={400}
    itemSize={50}
    renderItem={(item, index, style) => (
      <div style={style} className="list-item">
        {item.title}
      </div>
    )}
  />
);
```

## 🔧 Monitoring & Debugging

### Development Tools

1. **React DevTools Profiler**: Monitor component renders
2. **Chrome DevTools**:
   - Performance tab for bottlenecks
   - Lighthouse tab for audits
   - Network tab for resource loading
3. **Web Vitals Extension**: Real-time Core Web Vitals

### Performance Debugging

```typescript
// Enable debug mode
const monitor = initPerformanceMonitoring({ debug: true });

// Custom performance marks
monitor.mark('expensive-operation-start');
// ... expensive operation
monitor.measure('expensive-operation', 'expensive-operation-start');

// Get performance summary
const summary = monitor.getSummary();
console.log('Performance Score:', summary.score);
```

## 📈 Continuous Monitoring

### GitHub Actions Integration

The Lighthouse CI workflow:

1. **Runs on PR**: Every pull request triggers performance testing
2. **Performance Budgets**: Fails CI if performance degrades
3. **Trend Analysis**: Tracks performance over time
4. **Team Notifications**: Alerts team to performance regressions

### Local Development

```bash
# Check performance before committing
npm run build
npm run lighthouse:local

# Monitor during development
npm run dev
# Open browser to http://localhost:8080
# Run Lighthouse in Chrome DevTools
```

## 🎯 Best Practices

### Do's ✅

- Use `memo()` for expensive components
- Implement lazy loading for images and routes
- Use virtual scrolling for large lists
- Monitor Core Web Vitals in production
- Run Lighthouse CI on every PR
- Optimize images (WebP, proper sizing)
- Preload critical resources
- Use efficient state management

### Don'ts ❌

- Don't block the main thread with heavy computations
- Don't load all data upfront - implement pagination
- Don't forget to optimize images
- Don't ignore Lighthouse warnings
- Don't ship unminified code to production
- Don't use large third-party libraries without code splitting
- Don't ignore memory leaks

## 📚 Resources

- [Web Vitals](https://web.dev/vitals/)
- [Lighthouse Performance Auditing](https://developers.google.com/web/tools/lighthouse)
- [React Performance](https://react.dev/learn/render-and-commit)
- [Vite Performance](https://vitejs.dev/guide/performance.html)
- [Service Worker Best Practices](https://developers.google.com/web/fundamentals/primers/service-workers)

---

**Performance is a journey, not a destination.** Regularly monitor, test, and optimize to maintain world-class performance scores.
