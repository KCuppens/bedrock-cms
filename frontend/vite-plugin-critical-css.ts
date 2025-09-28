import { Plugin } from 'vite';

/**
 * Vite plugin to inline critical CSS for faster initial render
 * Prevents render-blocking and improves FCP/LCP metrics
 */
export function criticalCSSPlugin(): Plugin {
  let config: any;

  return {
    name: 'vite-plugin-critical-css',

    configResolved(resolvedConfig) {
      config = resolvedConfig;
    },

    transformIndexHtml: {
      order: 'post',
      handler(html: string) {
        // Only apply in production builds
        const isProduction = config?.command === 'build';

        // Enhanced critical CSS for above-the-fold content
        const criticalCSS = `
          /* Critical CSS for immediate render - Tailwind + shadcn/ui variables */
          :root {
            --background: 0 0% 100%;
            --foreground: 222.2 84% 4.9%;
            --primary: 222.2 47.4% 11.2%;
            --primary-foreground: 210 40% 98%;
            --secondary: 210 40% 96.1%;
            --secondary-foreground: 222.2 47.4% 11.2%;
            --muted: 210 40% 96.1%;
            --muted-foreground: 215.4 16.3% 46.9%;
            --accent: 210 40% 96.1%;
            --accent-foreground: 222.2 47.4% 11.2%;
            --destructive: 0 84.2% 60.2%;
            --destructive-foreground: 210 40% 98%;
            --border: 214.3 31.8% 91.4%;
            --input: 214.3 31.8% 91.4%;
            --ring: 222.2 84% 4.9%;
            --radius: 0.5rem;
          }

          .dark {
            --background: 222.2 84% 4.9%;
            --foreground: 210 40% 98%;
            --primary: 210 40% 98%;
            --primary-foreground: 222.2 47.4% 11.2%;
            --secondary: 217.2 32.6% 17.5%;
            --secondary-foreground: 210 40% 98%;
            --muted: 217.2 32.6% 17.5%;
            --muted-foreground: 215 20.2% 65.1%;
            --accent: 217.2 32.6% 17.5%;
            --accent-foreground: 210 40% 98%;
            --destructive: 0 62.8% 30.6%;
            --destructive-foreground: 210 40% 98%;
            --border: 217.2 32.6% 17.5%;
            --input: 217.2 32.6% 17.5%;
            --ring: 212.7 26.8% 83.9%;
          }

          /* Reset and base styles */
          *, *::before, *::after { box-sizing: border-box; }
          * { margin: 0; padding: 0; }

          html {
            -webkit-text-size-adjust: 100%;
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
            text-rendering: optimizeLegibility;
            scroll-behavior: smooth;
            overflow-y: scroll; /* Prevent layout shift from scrollbar */
          }

          body {
            margin: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
            background: hsl(var(--background));
            color: hsl(var(--foreground));
            min-height: 100vh;
            line-height: 1.5;
            -webkit-tap-highlight-color: transparent;
          }

          #root {
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            isolation: isolate;
          }

          /* Loading states for better perceived performance */
          .loading-spinner {
            display: inline-block;
            width: 2rem;
            height: 2rem;
            border: 3px solid hsl(var(--muted));
            border-radius: 50%;
            border-top-color: hsl(var(--primary));
            animation: spin 0.6s linear infinite;
          }

          @keyframes spin {
            to { transform: rotate(360deg); }
          }

          /* Layout stability - Prevent CLS */
          img, video, canvas, svg, iframe {
            display: block;
            max-width: 100%;
            height: auto;
            aspect-ratio: attr(width) / attr(height);
          }

          button, input, select, textarea {
            font: inherit;
            color: inherit;
          }

          a {
            color: inherit;
            text-decoration: none;
          }

          /* Dark mode support */
          @media (prefers-color-scheme: dark) {
            html { color-scheme: dark; }
          }

          /* Critical layout containers */
          .container {
            width: 100%;
            max-width: 1280px;
            margin: 0 auto;
            padding: 0 1rem;
          }

          .flex { display: flex; }
          .grid { display: grid; }
          .hidden { display: none !important; }
          .sr-only {
            position: absolute;
            width: 1px;
            height: 1px;
            padding: 0;
            margin: -1px;
            overflow: hidden;
            clip: rect(0, 0, 0, 0);
            white-space: nowrap;
            border-width: 0;
          }

          /* Critical typography */
          h1, h2, h3, h4, h5, h6 {
            margin: 0;
            font-weight: 600;
            line-height: 1.2;
          }

          p {
            margin: 0;
          }

          /* Skeleton loading states */
          .skeleton {
            position: relative;
            overflow: hidden;
            background: hsl(var(--muted));
          }

          .skeleton::after {
            content: "";
            position: absolute;
            top: 0;
            right: 0;
            bottom: 0;
            left: 0;
            transform: translateX(-100%);
            background: linear-gradient(
              90deg,
              transparent,
              hsl(var(--muted) / 0.5),
              transparent
            );
            animation: skeleton-loading 2s infinite;
          }

          @keyframes skeleton-loading {
            100% { transform: translateX(100%); }
          }

          /* Prevent FOUC and FOIT */
          .fonts-loading { opacity: 0; }
          .fonts-loaded {
            opacity: 1;
            transition: opacity 0.3s ease-in-out;
          }

          /* Performance optimizations */
          .gpu-accelerated {
            transform: translateZ(0);
            will-change: transform;
            backface-visibility: hidden;
          }

          /* Reduced motion support */
          @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
              animation-duration: 0.01ms !important;
              animation-iteration-count: 1 !important;
              transition-duration: 0.01ms !important;
              scroll-behavior: auto !important;
            }
          }

          /* Initial loading screen */
          .app-loading {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            background: hsl(var(--background));
            z-index: 9999;
          }

          .app-loaded .app-loading {
            display: none;
          }
        `;

        // Minify critical CSS in production
        const minifiedCSS = isProduction
          ? criticalCSS.replace(/\s+/g, ' ').replace(/:\s+/g, ':').replace(/;\s+/g, ';').trim()
          : criticalCSS;

        // Inject critical CSS into head
        const cssTag = `<style id="critical-css">${minifiedCSS}</style>`;

        // Add script to mark JS as available and handle font loading
        const jsDetectScript = `
          <script>
            // Mark JS as available immediately
            document.documentElement.classList.add('js');
            document.documentElement.classList.remove('no-js');

            // Font loading observer
            if ('fonts' in document) {
              document.documentElement.classList.add('fonts-loading');
              Promise.all([
                document.fonts.load('400 1em system-ui'),
                document.fonts.load('600 1em system-ui')
              ]).then(() => {
                document.documentElement.classList.remove('fonts-loading');
                document.documentElement.classList.add('fonts-loaded');
              });
            }

            // Mark app as loaded when React mounts
            window.addEventListener('DOMContentLoaded', () => {
              requestAnimationFrame(() => {
                document.documentElement.classList.add('app-loaded');
              });
            });
          </script>
        `;

        // Insert critical CSS and JS detection before other styles
        html = html.replace('</head>', `${cssTag}${jsDetectScript}</head>`);

        // Add comprehensive resource hints for faster loading
        const resourceHints = `
          <!-- DNS Prefetch for third-party domains -->
          <link rel="dns-prefetch" href="https://fonts.googleapis.com">
          <link rel="dns-prefetch" href="https://fonts.gstatic.com">

          <!-- Preconnect for critical domains -->
          <link rel="preconnect" href="https://fonts.googleapis.com" crossorigin>
          <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>

          <!-- Preload critical fonts -->
          <link rel="preload" as="font" type="font/woff2" href="/fonts/inter-var.woff2" crossorigin>

          <!-- Prefetch for next likely navigation -->
          <link rel="prefetch" href="/dashboard">
          <link rel="prefetch" href="/api/v1/auth/user">
        `;

        html = html.replace('<head>', `<head>${resourceHints}`);

        // Add loading placeholder in body
        const loadingPlaceholder = `
          <div class="app-loading" id="app-loading">
            <div class="loading-spinner" role="status" aria-label="Loading application">
              <span class="sr-only">Loading...</span>
            </div>
          </div>
        `;

        html = html.replace('<div id="root"></div>', `<div id="root"></div>${loadingPlaceholder}`);

        return html;
      }
    }
  };
}
