// Service Worker for Career Beacon PWA
const CACHE_NAME = 'career-beacon-shell-v2';
const PRECACHE_ASSETS = [
  '/',
  '/index.html',
  '/manifest.webmanifest',
  '/favicon.svg',
  '/icon-192.png',
  '/icon-512.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRECACHE_ASSETS).catch((err) => {
        console.warn('Pre-caching partial failure, proceeding:', err);
      });
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((name) => {
          if (name !== CACHE_NAME) {
            return caches.delete(name);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // 1. Only intercept same-origin HTTP(S) GET requests; bypass extensions, external origins, APIs, and Supabase
  if (
    event.request.method !== 'GET' ||
    (url.protocol !== 'http:' && url.protocol !== 'https:') ||
    url.origin !== self.location.origin ||
    url.pathname.startsWith('/api')
  ) {
    return;
  }

  // 2. Stale-While-Revalidate for same-origin app assets, always resolving to a valid Response
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      const fetchPromise = fetch(event.request)
        .then((networkResponse) => {
          if (
            networkResponse &&
            networkResponse.status === 200 &&
            networkResponse.type === 'basic'
          ) {
            const responseToCache = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(event.request, responseToCache);
            });
          }
          return networkResponse;
        })
        .catch(async () => {
          if (cachedResponse) {
            return cachedResponse;
          }
          if (event.request.mode === 'navigate') {
            const shell = (await caches.match('/index.html')) || (await caches.match('/'));
            if (shell) return shell;
          }
          return Response.error();
        });

      return cachedResponse || fetchPromise;
    })
  );
});

