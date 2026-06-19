const CACHE = 'should-i-bike-v3';
const ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './css/style.css',
  './js/db.js',
  './js/weather.js',
  './js/rules.js',
  './js/app.js',
  'https://unpkg.com/vue@3/dist/vue.global.prod.js',
  'https://unpkg.com/dexie@3/dist/dexie.min.js',
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
  ));
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  // Network-first for NOAA/Nominatim; cache-first for everything else
  const url = new URL(e.request.url);
  const isApi = url.hostname.includes('weather.gov') || url.hostname.includes('nominatim');
  if (isApi) {
    e.respondWith(fetch(e.request).catch(() => new Response('', { status: 503 })));
  } else {
    e.respondWith(
      caches.match(e.request).then(hit => hit || fetch(e.request))
    );
  }
});
