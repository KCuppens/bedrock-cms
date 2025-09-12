import { defineConfig, splitVendorChunkPlugin } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";
import { visualizer } from "rollup-plugin-visualizer";
import viteCompression from 'vite-plugin-compression';

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  server: {
    host: "::",
    port: 8080,
  },
  plugins: [
    react(),
    splitVendorChunkPlugin(),
    mode === 'development' && componentTagger(),
    // Gzip compression
    viteCompression({
      algorithm: 'gzip',
      ext: '.gz',
    }),
    // Brotli compression
    viteCompression({
      algorithm: 'brotliCompress',
      ext: '.br',
    }),
    // Bundle analyzer (only in analyze mode)
    process.env.ANALYZE && visualizer({
      open: true,
      filename: 'dist/stats.html',
      gzipSize: true,
      brotliSize: true,
    }),
  ].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    target: 'es2018', // Better browser support
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: mode === 'production',
        drop_debugger: true,
        pure_funcs: mode === 'production' ? ['console.log', 'console.info'] : [],
        passes: 2, // More aggressive compression
      },
      mangle: {
        safari10: true, // Fix Safari 10 issues
      },
      format: {
        comments: false, // Remove all comments
      },
    },
    rollupOptions: {
      output: {
        manualChunks: {
          // React core (always loaded)
          'react-core': ['react', 'react-dom'],

          // Router (loaded on navigation)
          'react-router': ['react-router-dom'],

          // Forms (lazy loaded)
          'forms': ['react-hook-form', '@hookform/resolvers', 'zod'],

          // Date utilities (lazy loaded)
          'date': ['date-fns'],

          // Charts (lazy loaded)
          'charts': ['recharts'],

          // DND (lazy loaded for editor)
          'dnd': ['@dnd-kit/core', '@dnd-kit/sortable', '@dnd-kit/utilities'],

          // Radix UI - Split into smaller chunks
          'radix-dialog': [
            '@radix-ui/react-dialog',
            '@radix-ui/react-alert-dialog',
            '@radix-ui/react-popover',
          ],
          'radix-form': [
            '@radix-ui/react-checkbox',
            '@radix-ui/react-radio-group',
            '@radix-ui/react-select',
            '@radix-ui/react-switch',
            '@radix-ui/react-slider',
            '@radix-ui/react-toggle',
            '@radix-ui/react-toggle-group',
          ],
          'radix-layout': [
            '@radix-ui/react-accordion',
            '@radix-ui/react-collapsible',
            '@radix-ui/react-tabs',
            '@radix-ui/react-scroll-area',
            '@radix-ui/react-separator',
          ],
          'radix-menu': [
            '@radix-ui/react-dropdown-menu',
            '@radix-ui/react-context-menu',
            '@radix-ui/react-menubar',
            '@radix-ui/react-navigation-menu',
          ],
          'radix-misc': [
            '@radix-ui/react-avatar',
            '@radix-ui/react-aspect-ratio',
            '@radix-ui/react-hover-card',
            '@radix-ui/react-label',
            '@radix-ui/react-progress',
            '@radix-ui/react-toast',
            '@radix-ui/react-tooltip',
            '@radix-ui/react-slot',
          ],

          // Utilities
          'utils': [
            'clsx',
            'class-variance-authority',
            'tailwind-merge',
            'tailwindcss-animate',
          ],

          // Heavy libraries (lazy loaded)
          'heavy': [
            'embla-carousel-react',
            'react-resizable-panels',
            'react-day-picker',
            'cmdk',
            'vaul',
            'input-otp',
          ],

          // Icons (separate chunk)
          'icons': ['lucide-react'],

          // Data fetching
          'query': ['@tanstack/react-query'],

          // Themes and styling
          'themes': ['next-themes'],

          // Notifications
          'notifications': ['sonner'],

          // Virtualization (lazy loaded)
          'virtual': ['react-window'],

          // Performance monitoring
          'monitoring': ['web-vitals'],
        },

        // Better chunk naming for caching
        chunkFileNames: (chunkInfo) => {
          const name = chunkInfo.name || 'chunk';
          return `assets/js/${name}-[hash:8].js`;
        },
        entryFileNames: 'assets/js/[name]-[hash:8].js',
        assetFileNames: (assetInfo) => {
          const ext = path.extname(assetInfo.name || '');
          const folder = ext === '.css' ? 'css' : ext.slice(1);
          return `assets/${folder}/[name]-[hash:8][extname]`;
        },
      },

      // Tree shaking
      treeshake: {
        moduleSideEffects: false,
        propertyReadSideEffects: false,
        tryCatchDeoptimization: false,
      },
    },

    // Chunk size limits
    chunkSizeWarningLimit: 200, // Warn at 200kb

    // Performance improvements
    reportCompressedSize: false,
    sourcemap: mode === 'development',

    // CSS optimizations
    cssCodeSplit: true,
    cssMinify: 'lightningcss',

    // Asset inlining
    assetsInlineLimit: 4096, // Inline assets < 4kb
  },

  // Optimize dependencies
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      '@tanstack/react-query',
      'lucide-react',
    ],
    exclude: [
      '@dnd-kit/core',
      '@dnd-kit/sortable',
      '@dnd-kit/utilities',
      'recharts', // Heavy, lazy load
    ],
    esbuildOptions: {
      target: 'es2018',
    },
  },

  // CSS optimizations
  css: {
    modules: {
      localsConvention: 'camelCase',
    },
    devSourcemap: mode === 'development',
    lightningcss: {
      targets: {
        chrome: 90,
        firefox: 88,
        safari: 14,
        edge: 90,
      },
    },
  },

  // Preview optimizations
  preview: {
    headers: {
      'Cache-Control': 'public, max-age=31536000, immutable',
    },
  },

  // Experimental features
  experimental: {
    renderBuiltUrl(filename) {
      // Use CDN in production
      if (mode === 'production' && process.env.CDN_URL) {
        return `${process.env.CDN_URL}/${filename}`;
      }
      return `/${filename}`;
    },
  },
}));
