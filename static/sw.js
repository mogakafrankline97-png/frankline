// static/sw.js
// ============================================================
// SERVICE WORKER - PricePoint POS (Complete Offline Solution)
// ============================================================

const CACHE_NAME = 'pricepoint-v15';
const OFFLINE_URL = '/offline.html';

// ===== PAGES TO CACHE =====
const urlsToCache = [
    '/static/pwa-entry.html',
    '/pos',
    '/offline.html',
    '/manifest.json',
    '/static/icons/icon-72.png',
    '/static/icons/icon-96.png',
    '/static/icons/icon-128.png',
    '/static/icons/icon-144.png',
    '/static/icons/icon-152.png',
    '/static/icons/icon-192.png',
    '/static/icons/icon-384.png',
    '/static/icons/icon-512.png',
    '/favicon.ico'
];

// ============================================================
// INSTALL
// ============================================================

self.addEventListener('install', event => {
    console.log('[SW] 📦 Installing...');
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('[SW] Caching assets...');
                return Promise.allSettled(
                    urlsToCache.map(url => {
                        return cache.add(url)
                            .then(() => console.log('[SW] ✅ Cached:', url))
                            .catch(err => {
                                console.warn('[SW] ⚠️ Failed to cache:', url, err.message);
                                return Promise.resolve();
                            });
                    })
                );
            })
            .then(() => {
                console.log('[SW] ✅ Installation complete');
                return self.skipWaiting();
            })
    );
});

// ============================================================
// ACTIVATE
// ============================================================

self.addEventListener('activate', event => {
    console.log('[SW] 🔧 Activating...');
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cache => {
                    if (cache !== CACHE_NAME) {
                        console.log('[SW] 🗑️ Deleting old cache:', cache);
                        return caches.delete(cache);
                    }
                })
            );
        }).then(() => {
            console.log('[SW] ✅ Activation complete');
            return self.clients.claim();
        })
    );
});

// ============================================================
// FETCH
// ============================================================

self.addEventListener('fetch', event => {
    const request = event.request;
    const url = new URL(request.url);
    
    // Skip non-GET requests
    if (request.method !== 'GET') {
        event.respondWith(fetch(request));
        return;
    }
    
    // Skip Supabase requests
    if (url.hostname.includes('supabase.co')) {
        event.respondWith(
            fetch(request).catch(() => {
                return new Response(JSON.stringify({
                    offline: true,
                    message: 'You are offline. Using cached data.'
                }), {
                    status: 503,
                    headers: { 'Content-Type': 'application/json' }
                });
            })
        );
        return;
    }
    
    // ===== CRITICAL: Keep the POS shell available for offline reloads =====
    if (url.pathname === '/static/pwa-entry.html' || url.pathname === '/pwa-entry.html' || url.pathname === '/pos') {
        event.respondWith(
            caches.match(request)
                .then(cached => {
                    const fetchPromise = fetch(request, { cache: 'reload' })
                        .then(networkResponse => {
                            if (networkResponse && networkResponse.status === 200) {
                                const cloned = networkResponse.clone();
                                caches.open(CACHE_NAME)
                                    .then(cache => cache.put(request, cloned))
                                    .catch(() => {});
                            }
                            return networkResponse;
                        })
                        .catch(async () => {
                            const fallback = await caches.match(request);
                            if (fallback) {
                                console.log('[SW] ✅ Serving cached POS shell:', url.pathname);
                                return fallback;
                            }
                            return caches.match(OFFLINE_URL);
                        });

                    return cached || fetchPromise;
                })
        );
        return;
    }
    
    // ===== HTML PAGES - Network first, fallback to cache =====
    const isHTML = request.headers.get('Accept')?.includes('text/html');
    
    if (isHTML) {
        event.respondWith(
            fetch(request, { cache: 'reload' })
                .then(response => {
                    if (response && response.status === 200) {
                        const cloned = response.clone();
                        caches.open(CACHE_NAME)
                            .then(cache => cache.put(request, cloned))
                            .catch(() => {});
                    }
                    return response;
                })
                .catch(async () => {
                    const cached = await caches.match(request);
                    if (cached) {
                        console.log('[SW] ✅ Serving cached page:', url.pathname);
                        return cached;
                    }
                    return caches.match(OFFLINE_URL);
                })
        );
        return;
    }
    
    // ===== ASSETS - Cache first =====
    event.respondWith(
        caches.match(request)
            .then(response => {
                if (response) {
                    return response;
                }
                return fetch(request)
                    .then(networkResponse => {
                        if (!networkResponse || networkResponse.status !== 200) {
                            return networkResponse;
                        }
                        const responseToCache = networkResponse.clone();
                        caches.open(CACHE_NAME)
                            .then(cache => cache.put(request, responseToCache))
                            .catch(() => {});
                        return networkResponse;
                    })
                    .catch(() => {
                        if (url.pathname.match(/\.(css|js|png|jpg|jpeg|svg|ico|woff|woff2|ttf)$/)) {
                            return new Response('', { status: 404 });
                        }
                        return new Response('Offline', { status: 503 });
                    });
            })
    );
});

// ============================================================
// BACKGROUND SYNC
// ============================================================

self.addEventListener('sync', event => {
    if (event.tag === 'sync-orders') {
        console.log('[SW] 🔄 Background sync triggered');
        event.waitUntil(
            self.clients.matchAll().then(clients => {
                clients.forEach(client => {
                    client.postMessage({
                        type: 'SYNC_ORDERS',
                        payload: { timestamp: Date.now() }
                    });
                });
            })
        );
    }
});

// ============================================================
// MESSAGE HANDLER
// ============================================================

self.addEventListener('message', event => {
    console.log('[SW] 📨 Message received:', event.data);
    if (event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});

console.log('[SW] 🚀 Service Worker loaded');
