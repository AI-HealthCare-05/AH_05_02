"use strict";

const CACHE_NAME = "gandang-carrot-forest-pwa-v11";
const CORE_SHELL = [
  "/forest",
  "/manifest.webmanifest",
  "/static/forest-game.css?v=20260827-9",
  "/static/vendor/phaser-3.90.0.min.js",
  "/static/forest-phaser.js?v=20260827-1",
  "/static/forest-game.js?v=20260827-8",
  "/static/icons/forest-icon-192.png",
  "/static/icons/forest-icon-512.png",
];
const MEDIA_ASSETS = [
  "/static/assets/carrot-forest-avatar-atlas-v1.png",
  "/static/assets/carrot-forest-basic-walk-atlas-v1.png",
  "/static/assets/carrot-forest-basic-scooter-atlas-v1.png",
  "/static/assets/carrot-forest-preset-red-bow-v1.png",
  "/static/assets/carrot-forest-preset-cow-hood-v1.png",
  "/static/assets/carrot-forest-preset-midnight-v1.png",
  "/static/assets/carrot-forest-preset-blue-cap-v1.png",
  "/static/assets/carrot-forest-preset-teal-bob-v1.png",
  "/static/assets/carrot-forest-cosmetics-atlas-v1.png",
  "/static/assets/carrot-forest-cat-pets-v1.png",
  "/static/assets/carrot-forest-storage-atlas-v1.png",
  "/static/assets/carrot-forest-world-v2.png",
  "/static/assets/carrot-forest-home-v1.png",
  "/static/assets/carrot-forest-garden-v1.png",
  "/static/assets/lpc/body-female.png",
  "/static/assets/lpc/body-male.png",
  "/static/assets/lpc/pants-female.png",
  "/static/assets/lpc/pants-male.png",
  "/static/assets/lpc/shoes-female.png",
  "/static/assets/lpc/shoes-male.png",
  "/static/assets/lpc/top-long-female.png",
  "/static/assets/lpc/top-long-male.png",
  "/static/assets/lpc/top-polo-female.png",
  "/static/assets/lpc/top-polo-male.png",
  "/static/assets/lpc/top-vneck-female.png",
  "/static/assets/lpc/top-vneck-male.png",
  "/static/assets/lpc/hair-bob.png",
  "/static/assets/lpc/hair-long.png",
  "/static/assets/lpc/hair-messy.png",
  "/static/assets/lpc/hair-pixie.png",
  "/static/assets/lpc/hair-ponytail-bg.png",
  "/static/assets/lpc/hair-ponytail-fg.png",
  "/static/assets/lpc/hair-spiked.png",
  "/static/assets/lpc/hat-cap.png",
  "/static/assets/lpc/hat-headband.png",
  "/static/assets/lpc/glasses-round.png",
  "/static/assets/lpc/glasses-sun.png",
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
