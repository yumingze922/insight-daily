/* ========================================
   每日深度思辨 —— Service Worker v3
   清除旧缓存 + 轻量缓存策略
   ======================================== */

const CACHE_VERSION = 'v3-clear';
const CACHE_NAME = `insight-${CACHE_VERSION}`;

// 激活时清除所有旧缓存
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((names) => {
      return Promise.all(
        names.filter(n => n !== CACHE_NAME).map(n => caches.delete(n))
      );
    }).then(() => {
      return self.clients.claim();
    })
  );
});

// 网络优先：数据文件永远从网络获取，失败才用缓存兜底
self.addEventListener('fetch', (event) => {
  const url = event.request.url;
  
  // 数据文件：网络优先，不缓存
  if (url.includes('/public/data/') || url.includes('/data/')) {
    event.respondWith(
      fetch(event.request).catch(() => caches.match(event.request))
    );
    return;
  }
  
  // 静态资源：缓存优先，后台更新
  event.respondWith(
    caches.match(event.request).then((cached) => {
      const fetchPromise = fetch(event.request).then((response) => {
        const respClone = response.clone();
        caches.open(CACHE_NAME).then((cache) => {
          cache.put(event.request, respClone);
        });
        return response;
      });
      return cached || fetchPromise;
    })
  );
});
