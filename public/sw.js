/* ========================================
   每日深度思辨 —— Service Worker
   PWA 离线缓存策略
   ======================================== */

const CACHE_VERSION = 'v2';
const STATIC_CACHE = `insight-static-${CACHE_VERSION}`;
const DATA_CACHE = `insight-data-${CACHE_VERSION}`;

// 预缓存的静态资源
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/css/style.css',
  '/js/data.js',
  '/js/app.js',
  '/js/dialogue.js',
  '/manifest.json'
];

// 安装：预缓存静态资源
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    }).then(() => {
      return self.skipWaiting();
    })
  );
});

// 激活：清理旧缓存
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => {
          return key.startsWith('insight-') && key !== STATIC_CACHE && key !== DATA_CACHE;
        }).map((key) => {
          return caches.delete(key);
        })
      );
    }).then(() => {
      return self.clients.claim();
    })
  );
});

// 请求拦截：根据资源类型选择缓存策略
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // 跳过非 HTTP 请求
  if (!url.protocol.startsWith('http')) return;

  // 策略一：API 数据 —— Network First（获取最新，离线时用缓存）
  if (url.pathname.startsWith('/api/') || url.pathname.includes('/data/')) {
    event.respondWith(networkFirst(request, DATA_CACHE));
    return;
  }

  // 策略二：静态资源 —— Cache First（优先用缓存，加快加载）
  if (
    request.destination === 'script' ||
    request.destination === 'style' ||
    request.destination === 'font' ||
    url.pathname.endsWith('.js') ||
    url.pathname.endsWith('.css') ||
    url.pathname.endsWith('.woff2')
  ) {
    event.respondWith(cacheFirst(request, STATIC_CACHE));
    return;
  }

  // 策略三：HTML 页面 —— Network First（获取最新页面结构）
  if (request.destination === 'document' || request.mode === 'navigate') {
    event.respondWith(networkFirst(request, STATIC_CACHE));
    return;
  }

  // 策略四：图片/图标 —— Stale While Revalidate
  if (request.destination === 'image') {
    event.respondWith(staleWhileRevalidate(request, STATIC_CACHE));
    return;
  }

  // 默认：Network First
  event.respondWith(networkFirst(request, STATIC_CACHE));
});

// ========== 缓存策略实现 ==========

// Network First：优先网络，失败时回退缓存
async function networkFirst(request, cacheName) {
  try {
    const response = await fetch(request);
    // 缓存成功的响应
    const cache = await caches.open(cacheName);
    cache.put(request, response.clone());
    return response;
  } catch (error) {
    // 离线时使用缓存
    const cached = await caches.match(request);
    if (cached) return cached;
    // 如果是导航请求，返回离线页面
    if (request.mode === 'navigate') {
      const offlineCache = await caches.match('/');
      if (offlineCache) return offlineCache;
    }
    throw error;
  }
}

// Cache First：优先缓存，缓存未命中时请求网络
async function cacheFirst(request, cacheName) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    const cache = await caches.open(cacheName);
    cache.put(request, response.clone());
    return response;
  } catch (error) {
    throw error;
  }
}

// Stale While Revalidate：立即返回缓存，后台更新
async function staleWhileRevalidate(request, cacheName) {
  const cached = await caches.match(request);
  const fetchPromise = fetch(request).then((response) => {
    const cache = caches.open(cacheName);
    cache.then((c) => c.put(request, response.clone()));
    return response;
  }).catch(() => {});
  return cached || fetchPromise;
}
