/**
 * Optimized font loading strategy
 */

interface FontConfig {
  family: string;
  source: string;
  descriptors?: FontFaceDescriptors;
  fallback?: string[];
  preload?: boolean;
}

class FontLoader {
  private loaded = new Set<string>();
  private loading = new Map<string, Promise<void>>();

  /**
   * Load fonts with optimal strategy
   */
  async loadFont(config: FontConfig): Promise<void> {
    const key = `${config.family}-${config.source}`;

    // Return if already loaded
    if (this.loaded.has(key)) {
      return Promise.resolve();
    }

    // Return existing promise if loading
    if (this.loading.has(key)) {
      return this.loading.get(key)!;
    }

    // Start loading
    const loadPromise = this.performFontLoad(config);
    this.loading.set(key, loadPromise);

    try {
      await loadPromise;
      this.loaded.add(key);
      this.loading.delete(key);
    } catch (error) {
      this.loading.delete(key);
      throw error;
    }
  }

  private async performFontLoad(config: FontConfig): Promise<void> {
    // Use CSS Font Loading API if available
    if ('fonts' in document) {
      const font = new FontFace(
        config.family,
        `url(${config.source})`,
        config.descriptors || {}
      );

      try {
        const loadedFont = await font.load();
        document.fonts.add(loadedFont);

        // Trigger reflow only once
        document.body.style.fontFamily = document.body.style.fontFamily;
      } catch (error) {
        console.warn(`Failed to load font ${config.family}:`, error);
        this.applyFallback(config);
      }
    } else {
      // Fallback for older browsers
      this.loadFontViaCSS(config);
    }
  }

  private loadFontViaCSS(config: FontConfig): void {
    const style = document.createElement('style');
    const fallbackStack = config.fallback?.join(', ') || 'sans-serif';

    style.innerHTML = `
      @font-face {
        font-family: '${config.family}';
        src: url('${config.source}') format('woff2');
        font-display: swap;
        ${config.descriptors?.weight ? `font-weight: ${config.descriptors.weight};` : ''}
        ${config.descriptors?.style ? `font-style: ${config.descriptors.style};` : ''}
      }

      body {
        font-family: '${config.family}', ${fallbackStack};
      }
    `;

    document.head.appendChild(style);
  }

  private applyFallback(config: FontConfig): void {
    if (config.fallback && config.fallback.length > 0) {
      document.body.style.fontFamily = config.fallback.join(', ');
    }
  }

  /**
   * Preload critical fonts
   */
  preloadFonts(fonts: FontConfig[]): void {
    fonts
      .filter(f => f.preload)
      .forEach(font => {
        const link = document.createElement('link');
        link.rel = 'preload';
        link.as = 'font';
        link.href = font.source;
        link.type = 'font/woff2';
        link.crossOrigin = 'anonymous';
        document.head.appendChild(link);
      });
  }

  /**
   * Load fonts based on viewport
   */
  async loadFontsForViewport(): Promise<void> {
    const isMobile = window.matchMedia('(max-width: 768px)').matches;

    if (isMobile) {
      // Load only essential fonts for mobile
      await this.loadFont({
        family: 'Inter',
        source: '/fonts/inter-var-latin-subset.woff2',
        descriptors: { weight: '400 700' },
        fallback: ['system-ui', '-apple-system', 'sans-serif']
      });
    } else {
      // Load full font set for desktop
      await Promise.all([
        this.loadFont({
          family: 'Inter',
          source: '/fonts/inter-var-latin.woff2',
          descriptors: { weight: '100 900' },
          fallback: ['system-ui', '-apple-system', 'sans-serif']
        }),
        this.loadFont({
          family: 'JetBrains Mono',
          source: '/fonts/jetbrains-mono.woff2',
          descriptors: { weight: '400' },
          fallback: ['Consolas', 'Monaco', 'monospace']
        })
      ]);
    }
  }

  /**
   * Create optimized font face CSS
   */
  generateFontFaceCSS(): string {
    return `
      /* Optimized font loading with subsetting */
      @font-face {
        font-family: 'Inter';
        font-style: normal;
        font-weight: 100 900;
        font-display: optional; /* Prevents FOIT */
        src: url('/fonts/inter-var-latin.woff2') format('woff2-variations');
        unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+2000-206F, U+2074, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD;
      }

      /* Fallback for browsers without variable font support */
      @supports not (font-variation-settings: normal) {
        @font-face {
          font-family: 'Inter';
          font-style: normal;
          font-weight: 400;
          font-display: swap;
          src: url('/fonts/inter-regular.woff2') format('woff2');
        }

        @font-face {
          font-family: 'Inter';
          font-style: normal;
          font-weight: 700;
          font-display: swap;
          src: url('/fonts/inter-bold.woff2') format('woff2');
        }
      }

      /* System font stack fallback */
      .system-font {
        font-family: system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
      }

      /* Monospace font for code */
      @font-face {
        font-family: 'JetBrains Mono';
        font-style: normal;
        font-weight: 400;
        font-display: swap;
        src: url('/fonts/jetbrains-mono.woff2') format('woff2');
        unicode-range: U+0000-00FF;
        font-feature-settings: 'liga' 1, 'calt' 1; /* Enable ligatures */
      }

      code, pre {
        font-family: 'JetBrains Mono', Consolas, Monaco, 'Andale Mono', 'Ubuntu Mono', monospace;
      }
    `;
  }
}

// Export singleton instance
export const fontLoader = new FontLoader();

// Auto-initialize on page load
if (typeof window !== 'undefined') {
  // Use requestIdleCallback for non-critical font loading
  const loadFonts = () => fontLoader.loadFontsForViewport();

  if ('requestIdleCallback' in window) {
    requestIdleCallback(loadFonts, { timeout: 2000 });
  } else {
    // Fallback for Safari
    setTimeout(loadFonts, 100);
  }
}
