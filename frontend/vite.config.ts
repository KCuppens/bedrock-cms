import { defineConfig, Plugin } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";
import { translationExtractionPlugin } from "./vite-plugin-translations";
import { criticalCSSPlugin } from "./vite-plugin-critical-css";

// Custom plugin to handle malformed URIs
const malformedUriHandler = (): Plugin => ({
  name: 'malformed-uri-handler',
  configureServer(server) {
    server.middlewares.use((req, res, next) => {
      try {
        // Try to decode the URI, if it fails, skip this request
        if (req.url) {
          decodeURI(req.url);
        }
        next();
      } catch (e) {
        console.warn('Malformed URI detected:', req.url);
        // Return 400 Bad Request for malformed URIs
        res.statusCode = 400;
        res.end('Bad Request: Malformed URI');
      }
    });
  },
});

// Plugin to handle sitemap and SEO redirects before React Router
const seoRedirectHandler = (): Plugin => ({
  name: 'seo-redirect-handler',
  configureServer(server) {
    server.middlewares.use((req, res, next) => {
      const url = req.url;

      // Check if it's a sitemap or robots.txt request
      if (url?.match(/^\/sitemap(-.*)?\.xml$/) || url === '/robots.txt') {
        // Proxy these requests directly to the backend
        const backendUrl = `http://localhost:8082${url}`;

        fetch(backendUrl)
          .then(backendRes => {
            res.statusCode = backendRes.status;
            res.setHeader('Content-Type', backendRes.headers.get('content-type') || 'text/xml');
            return backendRes.text();
          })
          .then(content => {
            res.end(content);
          })
          .catch(err => {
            console.error('Failed to proxy SEO request:', err);
            res.statusCode = 500;
            res.end('Internal Server Error');
          });
        return; // Don't call next() - we handled the request
      }

      next();
    });
  },
});

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  server: {
    host: "::",
    port: 8080,
    proxy: {
      // Proxy API requests to backend
      '/api': {
        target: 'http://localhost:8082',
        changeOrigin: true,
        secure: false,
      },
      // Proxy auth requests to backend
      '/auth': {
        target: 'http://localhost:8082',
        changeOrigin: true,
        secure: false,
      },
      // Proxy admin requests to backend
      '/admin': {
        target: 'http://localhost:8082',
        changeOrigin: true,
        secure: false,
      },
      // Proxy sitemap requests to backend
      '/sitemap*.xml': {
        target: 'http://localhost:8082',
        changeOrigin: true,
        secure: false,
      },
      // Proxy robots.txt to backend
      '/robots.txt': {
        target: 'http://localhost:8082',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  plugins: [
    criticalCSSPlugin(), // Add critical CSS extraction
    malformedUriHandler(),
    seoRedirectHandler(),
    react(),
    // translationExtractionPlugin(), // Disabled due to traverse errors
    mode === 'development' &&
    componentTagger(),
  ].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    target: 'es2015',
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: mode === 'production',
        drop_debugger: true,
        pure_funcs: mode === 'production' ? ['console.log', 'console.info', 'console.debug'] : [],
        passes: 3, // More passes for better optimization
        dead_code: true,
        unused: true,
        reduce_vars: true,
        collapse_vars: true,
        inline: 2,
        toplevel: true,
        unsafe_math: true,
        unsafe_comps: true,
        unsafe_proto: true,
        unsafe_regexp: true,
      },
      mangle: {
        safari10: true,
        properties: {
          regex: /^_/ // Mangle private properties
        }
      },
      format: {
        comments: false,
        ecma: 2015,
      },
    },
    rollupOptions: {
      output: {
        manualChunks(id) {
          // More aggressive chunking for better caching
          if (id.includes('node_modules')) {
            // React core - minimal bundle
            if (id.includes('react-dom')) {
              return 'react-dom';
            }
            if (id.includes('react') && !id.includes('react-')) {
              return 'react-core';
            }
            if (id.includes('react-router')) {
              return 'react-router';
            }

            // Split each Radix UI component into its own chunk for better tree shaking
            const radixMatch = id.match(/@radix-ui\/react-([^\/]+)/);
            if (radixMatch) {
              return `radix-${radixMatch[1]}`;
            }

            // DND Kit - lazy loaded only when needed
            if (id.includes('@dnd-kit/sortable')) {
              return 'dnd-sortable';
            }
            if (id.includes('@dnd-kit/core')) {
              return 'dnd-core';
            }
            if (id.includes('@dnd-kit')) {
              return 'dnd-utils';
            }

            // Heavy charting library - should be dynamically imported
            if (id.includes('recharts')) {
              return 'charts';
            }
            if (id.includes('d3')) {
              return 'd3-utils';
            }

            // Form libraries
            if (id.includes('react-hook-form')) {
              return 'react-hook-form';
            }
            if (id.includes('@hookform')) {
              return 'hookform-resolvers';
            }
            if (id.includes('zod')) {
              return 'zod-validation';
            }

            // Date utilities - split by functionality
            if (id.includes('date-fns/locale')) {
              return 'date-locales';
            }
            if (id.includes('date-fns')) {
              return 'date-utils';
            }

            // React Query and related
            if (id.includes('@tanstack/react-query-devtools')) {
              return 'query-devtools';
            }
            if (id.includes('@tanstack/react-query')) {
              return 'react-query';
            }

            // Icons - split into smaller chunks
            if (id.includes('lucide-react')) {
              return 'icons-lucide';
            }

            // Animation libraries
            if (id.includes('framer-motion')) {
              return 'framer-motion';
            }

            // Virtualization
            if (id.includes('react-window')) {
              return 'react-window';
            }

            // SEO utilities
            if (id.includes('react-helmet')) {
              return 'react-helmet';
            }

            // HTTP client
            if (id.includes('axios')) {
              return 'axios';
            }

            // UI utilities
            if (id.includes('class-variance-authority')) {
              return 'cva';
            }
            if (id.includes('clsx') || id.includes('tailwind-merge')) {
              return 'style-utils';
            }

            // Editor utilities
            if (id.includes('cmdk')) {
              return 'command';
            }

            // All other small vendor code
            return 'vendor-misc';
          }

          // Split large pages into separate chunks
          if (id.includes('src/pages/')) {
            if (id.includes('PageEditor') || id.includes('BlogPostEditor')) {
              return 'editors';
            }
            if (id.includes('Media') || id.includes('Pages') || id.includes('BlogPosts')) {
              return 'content-management';
            }
            if (id.includes('TranslationsQueue') || id.includes('TranslatorWorkspace') || id.includes('UIMessages')) {
              return 'translations';
            }
            if (id.includes('UsersRoles') || id.includes('Profile')) {
              return 'user-management';
            }
            if (id.includes('SEORedirects') || id.includes('APIDocs')) {
              return 'admin-tools';
            }
          }

          // Split UI components into separate chunk
          if (id.includes('src/components/ui')) {
            return 'ui-components';
          }

          // Split modal components
          if (id.includes('src/components/modals')) {
            return 'modals';
          }

          // Split contexts
          if (id.includes('src/contexts')) {
            return 'contexts';
          }
        },
        // Use content hash for better caching
        chunkFileNames: (chunkInfo) => {
          const facadeModuleId = chunkInfo.facadeModuleId ? chunkInfo.facadeModuleId.split('/').pop() : 'chunk';
          return `assets/js/${facadeModuleId}-[hash].js`;
        },
        entryFileNames: 'assets/js/[name]-[hash].js',
        assetFileNames: 'assets/[ext]/[name]-[hash].[ext]',
      },
    },
    chunkSizeWarningLimit: 200, // Stricter limit for better performance
    // Improve build performance
    reportCompressedSize: false,
    sourcemap: mode === 'development' ? 'inline' : false,
    // Enable CSS code splitting
    cssCodeSplit: true,
    // Inline assets smaller than 10kb for fewer requests
    assetsInlineLimit: 10240,
    // Enable module preloading
    modulePreload: {
      polyfill: true,
    },
    // Advanced optimizations
    commonjsOptions: {
      transformMixedEsModules: true,
    },
  },
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      '@tanstack/react-query',
      'axios'
    ],
    exclude: [
      '@dnd-kit/core',
      '@dnd-kit/sortable',
      '@dnd-kit/utilities',
      'recharts'
    ],
  },
  esbuild: {
    // Drop console logs and debugger statements in production
    drop: mode === 'production' ? ['console', 'debugger'] : [],
  },
}));
