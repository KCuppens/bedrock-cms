import { defineConfig, Plugin } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";
import { translationExtractionPlugin } from "./vite-plugin-translations";

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
        const backendUrl = `http://localhost:8000${url}`;

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
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      // Proxy auth requests to backend
      '/auth': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      // Proxy admin requests to backend
      '/admin': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      // Proxy sitemap requests to backend
      '/sitemap*.xml': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      // Proxy robots.txt to backend
      '/robots.txt': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  plugins: [
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
        pure_funcs: mode === 'production' ? ['console.log', 'console.info'] : [],
        passes: 2,
        dead_code: true,
        unused: true,
      },
      mangle: {
        safari10: true,
      },
      format: {
        comments: false,
      },
    },
    rollupOptions: {
      output: {
        manualChunks(id) {
          // Core vendor chunk
          if (id.includes('node_modules')) {
            if (id.includes('react') || id.includes('react-dom') || id.includes('react-router')) {
              return 'react-vendor';
            }
            // Radix UI components - split into smaller chunks
            if (id.includes('@radix-ui/react-dialog') || id.includes('@radix-ui/react-alert-dialog')) {
              return 'radix-dialogs';
            }
            if (id.includes('@radix-ui/react-dropdown-menu') || id.includes('@radix-ui/react-context-menu')) {
              return 'radix-menus';
            }
            if (id.includes('@radix-ui/react-select') || id.includes('@radix-ui/react-combobox')) {
              return 'radix-inputs';
            }
            if (id.includes('@radix-ui')) {
              return 'radix-ui';
            }
            // DND Kit (only loaded when PageEditor is used)
            if (id.includes('@dnd-kit')) {
              return 'dnd-kit';
            }
            // Heavy charting library (removed - using lightweight alternative)
            if (id.includes('recharts')) {
              return 'charts-legacy';
            }
            // Form libraries
            if (id.includes('react-hook-form') || id.includes('@hookform')) {
              return 'forms';
            }
            // Date utilities
            if (id.includes('date-fns')) {
              return 'date-utils';
            }
            // React Query
            if (id.includes('@tanstack/react-query')) {
              return 'query';
            }
            // Split other heavy libraries
            if (id.includes('lucide-react')) {
              return 'icons';
            }
            if (id.includes('framer-motion')) {
              return 'animation';
            }
            // React window for virtualization
            if (id.includes('react-window')) {
              return 'virtualization';
            }
            // Helmet for SEO
            if (id.includes('react-helmet')) {
              return 'helmet';
            }
            // Axios for HTTP
            if (id.includes('axios')) {
              return 'http';
            }
            // All other vendor code
            return 'vendor';
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
    chunkSizeWarningLimit: 300, // Stricter limit for better performance
    // Improve build performance
    reportCompressedSize: false,
    sourcemap: mode === 'development',
    // Enable CSS code splitting
    cssCodeSplit: true,
    // Inline assets smaller than 4kb
    assetsInlineLimit: 4096,
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
