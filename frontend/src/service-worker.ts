/// <reference lib="webworker" />
declare const self: ServiceWorkerGlobalScope;

import { precacheAndRoute, cleanupOutdatedCaches } from 'workbox-precaching';
import { registerRoute, NavigationRoute } from 'workbox-routing';
import {
  NetworkFirst,
  StaleWhileRevalidate,
  CacheFirst,
  NetworkOnly
} from 'workbox-strategies';
import { ExpirationPlugin } from 'workbox-expiration';
import { CacheableResponsePlugin } from 'workbox-cacheable-response';
import { BackgroundSyncPlugin } from 'workbox-background-sync';

// Precache all static assets generated at build time
precacheAndRoute(self.__WB_MANIFEST);

// Clean up old caches
cleanupOutdatedCaches();

// Skip waiting and claim clients immediately
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

self.addEventListener('activate', (event) => {
  event.waitUntil(clients.claim());
});

// Cache the Google Fonts stylesheets with a stale-while-revalidate strategy
registerRoute(
  ({ url }) => url.origin === 'https://fonts.googleapis.com',
  new StaleWhileRevalidate({
    cacheName: 'google-fonts-stylesheets',
    plugins: [
      new CacheableResponsePlugin({
        statuses: [0, 200],
      }),
      new ExpirationPlugin({
        maxAgeSeconds: 60 * 60 * 24 * 365, // 1 year
        maxEntries: 30,
      }),
    ],
  })
);

// Cache the Google Fonts webfont files with a cache-first strategy
registerRoute(
  ({ url }) => url.origin === 'https://fonts.gstatic.com',
  new CacheFirst({
    cacheName: 'google-fonts-webfonts',
    plugins: [
      new CacheableResponsePlugin({
        statuses: [0, 200],
      }),
      new ExpirationPlugin({
        maxAgeSeconds: 60 * 60 * 24 * 365, // 1 year
        maxEntries: 30,
      }),
    ],
  })
);

// Cache images with a cache-first strategy
registerRoute(
  ({ request }) => request.destination === 'image',
  new CacheFirst({
    cacheName: 'images',
    plugins: [
      new CacheableResponsePlugin({
        statuses: [0, 200],
      }),
      new ExpirationPlugin({
        maxEntries: 100,
        maxAgeSeconds: 30 * 24 * 60 * 60, // 30 days
        purgeOnQuotaError: true,
      }),
    ],
  })
);

// Cache API GET requests with network-first strategy
registerRoute(
  ({ url, request }) =>
    url.pathname.startsWith('/api/') && request.method === 'GET',
  new NetworkFirst({
    cacheName: 'api-cache',
    networkTimeoutSeconds: 5,
    plugins: [
      new CacheableResponsePlugin({
        statuses: [0, 200],
      }),
      new ExpirationPlugin({
        maxEntries: 50,
        maxAgeSeconds: 5 * 60, // 5 minutes
      }),
    ],
  })
);

// Handle API POST/PUT/DELETE requests with background sync
const bgSyncPlugin = new BackgroundSyncPlugin('api-queue', {
  maxRetentionTime: 24 * 60, // Retry for up to 24 hours
});

registerRoute(
  ({ url, request }) =>
    url.pathname.startsWith('/api/') &&
    ['POST', 'PUT', 'DELETE', 'PATCH'].includes(request.method),
  new NetworkOnly({
    plugins: [bgSyncPlugin],
  })
);

// Cache static assets (JS, CSS) with stale-while-revalidate
registerRoute(
  ({ request }) =>
    request.destination === 'script' ||
    request.destination === 'style',
  new StaleWhileRevalidate({
    cacheName: 'static-assets',
    plugins: [
      new CacheableResponsePlugin({
        statuses: [0, 200],
      }),
      new ExpirationPlugin({
        maxEntries: 60,
        maxAgeSeconds: 30 * 24 * 60 * 60, // 30 days
      }),
    ],
  })
);

// Handle navigation requests (HTML pages) with network-first strategy
// This enables offline support for visited pages
registerRoute(
  new NavigationRoute(
    new NetworkFirst({
      cacheName: 'pages',
      networkTimeoutSeconds: 3,
      plugins: [
        new CacheableResponsePlugin({
          statuses: [0, 200],
        }),
        new ExpirationPlugin({
          maxEntries: 50,
          maxAgeSeconds: 24 * 60 * 60, // 24 hours
        }),
      ],
    }),
    {
      // Don't cache admin pages
      denylist: [/\/dashboard/, /\/admin/, /\/sign-in/],
    }
  )
);

// Offline fallback page
const FALLBACK_HTML_URL = '/offline.html';
const FALLBACK_IMAGE_URL = '/images/offline.svg';

// Cache the offline fallback page during install
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open('offline-fallbacks').then((cache) => {
      return cache.addAll([FALLBACK_HTML_URL, FALLBACK_IMAGE_URL]);
    })
  );
});

// Serve offline fallback when network fails
self.addEventListener('fetch', (event) => {
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).catch(() => {
        return caches.match(FALLBACK_HTML_URL);
      })
    );
    return;
  }

  if (event.request.destination === 'image') {
    event.respondWith(
      caches.match(event.request).then((cachedResponse) => {
        return cachedResponse || fetch(event.request).catch(() => {
          return caches.match(FALLBACK_IMAGE_URL);
        });
      })
    );
  }
});

// Listen for push notifications
self.addEventListener('push', (event) => {
  const options = {
    body: event.data?.text() || 'New notification',
    icon: '/favicon-192x192.png',
    badge: '/favicon-96x96.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1,
    },
  };

  event.waitUntil(
    self.registration.showNotification('Bedrock CMS', options)
  );
});

// Handle notification clicks
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  event.waitUntil(
    clients.openWindow('/')
  );
});

// Export for TypeScript
export {};
