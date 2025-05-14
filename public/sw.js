// This is the service worker with the combined offline experience
const CACHE = "clem-todo-offline-v1";
const FALLBACK_HTML = '/offline.html';

const offlineFallbackPages = [
  FALLBACK_HTML,
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png',
  '/manifest.webmanifest'
];

self.addEventListener('install', (event) => {
  console.log('[ServiceWorker] Install');
  
  event.waitUntil(
    caches.open(CACHE).then((cache) => {
      console.log('[ServiceWorker] Pre-caching offline page');
      return cache.addAll(offlineFallbackPages);
    })
  );
});

self.addEventListener('activate', (event) => {
  console.log('[ServiceWorker] Activate');
  // Clean up old caches
  event.waitUntil(
    caches.keys().then((keyList) => {
      return Promise.all(keyList.map((key) => {
        if (key !== CACHE) {
          console.log('[ServiceWorker] Removing old cache', key);
          return caches.delete(key);
        }
      }));
    })
  );
  // Ensure the service worker takes control immediately
  return self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  console.log('[ServiceWorker] Fetch', event.request.url);
  
  // Skip cross-origin requests
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request)
        .catch(() => {
          return caches.open(CACHE)
            .then((cache) => {
              return cache.match(FALLBACK_HTML);
            });
        })
    );
  } else {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          // Cache successful responses
          if (response && response.status === 200) {
            const responseClone = response.clone();
            caches.open(CACHE).then((cache) => {
              cache.put(event.request, responseClone);
            });
          }
          return response;
        })
        .catch(() => {
          return caches.match(event.request)
            .then((response) => {
              if (response) {
                return response;
              }
            });
        })
    );
  }
}); 