"use strict";

const CACHE_NAME = "gandang-carrot-forest-pwa-v68";
const CORE_SHELL = [
  "/forest",
  "/manifest.webmanifest",
  "/static/forest-game.css?v=20260901-15",
  "/static/vendor/phaser-3.90.0.min.js",
  "/static/avatar-compositor.js?v=20260827-10",
  "/static/lpc-avatar-engine.js?v=20260901-21",
  "/static/forest-phaser.js?v=20260901-13",
  "/static/forest-game.js?v=20260901-36",
  "/static/icons/forest-icon-192.png",
  "/static/icons/forest-icon-512.png",
];
const MEDIA_ASSETS = [
  "/static/assets/when-the-morning-comes.mp3",
  "/static/assets/avatar-title.mp3",
  "/static/assets/home-elfwood.mp3",
  "/static/assets/garden-floral-life.mp3",
  "/static/assets/reward-chest-success.mp3",
  "/static/assets/carrot-forest-cat-pets-v1.png",
  "/static/assets/carrot-forest-storage-atlas-v1.png",
  "/static/assets/carrot-forest-storage-atlas-v2.png",
  "/static/assets/carrot-forest-storage-atlas-v3.png?v=20260831-1",
  "/static/assets/carrot-forest-animated-objects-v1.png?v=20260831-1",
  "/static/assets/carrot-forest-reward-cow-v1.png",
  "/static/assets/carrot-forest-lpc-pets-v1.png",
  "/static/assets/carrot-forest-lpc-rat-v1.png",
  "/static/assets/carrot-forest-loading-v1.png?v=20260831-1",
  "/static/assets/carrot-forest-world-v3.png?v=20260831-1",
  "/static/assets/carrot-forest-home-v1.png",
  "/static/assets/carrot-forest-garden-v1.png",
  "/static/assets/lpc-pack/manifest.json?v=20260901-10",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(async (cache) => {
      await cache.addAll(CORE_SHELL);
      await Promise.allSettled(MEDIA_ASSETS.map((asset) => cache.add(asset)));
    })
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin || url.pathname.startsWith("/api/")) return;

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put("/forest", copy));
          return response;
        })
        .catch(() => caches.match("/forest"))
    );
    return;
  }

  event.respondWith(
    caches.match(request).then((cached) => cached || fetch(request).then((response) => {
      if (response.ok) caches.open(CACHE_NAME).then((cache) => cache.put(request, response.clone()));
      return response;
    }))
  );
});
