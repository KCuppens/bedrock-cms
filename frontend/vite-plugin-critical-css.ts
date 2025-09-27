import { Plugin } from 'vite';

/**
 * Vite plugin to inline critical CSS for faster initial render
 */
export function criticalCSSPlugin(): Plugin {
  return {
    name: 'vite-plugin-critical-css',
    transformIndexHtml: {
      order: 'post',
      handler(html: string) {
        // Extract critical CSS for above-the-fold content
        const criticalCSS = `
          /* Critical CSS for immediate render */
          *, *::before, *::after { box-sizing: border-box; }
          html { -webkit-text-size-adjust: 100%; line-height: 1.5; }
          body { margin: 0; font-family: system-ui, -apple-system, sans-serif; }

          /* Loading state styles */
          .loading-spinner {
            display: inline-block;
            width: 2rem;
            height: 2rem;
            border: 3px solid rgba(0,0,0,0.1);
            border-radius: 50%;
            border-top-color: #3b82f6;
            animation: spin 0.6s linear infinite;
          }

          @keyframes spin {
            to { transform: rotate(360deg); }
          }

          /* Layout stability */
          img, video, canvas, svg { display: block; max-width: 100%; height: auto; }
          button, input, select, textarea { font: inherit; }

          /* Dark mode support */
          @media (prefers-color-scheme: dark) {
            html { color-scheme: dark; }
            body { background: #0f172a; color: #f8fafc; }
          }

          /* Prevent layout shift from scrollbar */
          html { overflow-y: scroll; }

          /* Critical layout containers */
          .container { width: 100%; max-width: 1280px; margin: 0 auto; padding: 0 1rem; }
          .flex { display: flex; }
          .grid { display: grid; }
          .hidden { display: none; }

          /* Critical typography */
          h1, h2, h3, h4, h5, h6 { margin: 0; font-weight: 600; }
          p { margin: 0; }

          /* Skeleton loading states */
          .skeleton {
            background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
            background-size: 200% 100%;
            animation: skeleton-loading 1.5s infinite;
          }

          @keyframes skeleton-loading {
            0% { background-position: 200% 0; }
            100% { background-position: -200% 0; }
          }

          /* Prevent FOUC */
          .no-js { display: none; }
          html.js .no-js { display: block; }
        `;

        // Inject critical CSS into head
        const cssTag = `<style id="critical-css">${criticalCSS.replace(/\s+/g, ' ').trim()}</style>`;

        // Add script to mark JS as available
        const jsDetectScript = `<script>document.documentElement.classList.add('js');</script>`;

        // Insert critical CSS and JS detection before other styles
        html = html.replace('</head>', `${cssTag}${jsDetectScript}</head>`);

        // Add resource hints for faster loading
        const resourceHints = `
          <link rel="preconnect" href="https://fonts.googleapis.com">
          <link rel="dns-prefetch" href="https://fonts.gstatic.com">
        `;

        html = html.replace('<head>', `<head>${resourceHints}`);

        return html;
      }
    }
  };
}
