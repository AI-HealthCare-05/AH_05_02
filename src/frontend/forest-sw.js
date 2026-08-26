"use strict";

const CACHE_NAME = "gandang-carrot-forest-pwa-v2";
const APP_SHELL = [
  "/forest",
  "/manifest.webmanifest",
  "/static/forest-game.css?v=20260826-7",
  "/static/forest-game.js?v=20260826-7",
  "/static/assets/carrot-forest-avatar-atlas-v1.png",
  "/static/assets/carrot-forest-cosmetics-atlas-v1.png",
  "/static/icons/forest-icon-192.png",
  "/static/icons/forest-icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)));
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
