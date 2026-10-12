import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

// Subscriber app: installable PWA (web-app option) and the web layer for a Capacitor build (native option).
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "prompt",
      includeAssets: ["icons/favicon.png", "icons/apple-touch-icon.png"],
      manifest: {
        name: "گازیار — طرح بهینه‌سازی مصرف گاز",
        short_name: "گازیار",
        description: "ثبت قرائت کنتور، پیگیری مصرف، امتیاز و جایزه برای صرفه‌جویی در مصرف گاز",
        lang: "fa",
        dir: "rtl",
        start_url: "/",
        scope: "/",
        display: "standalone",
        orientation: "portrait",
        background_color: "#F4F6FB",
        theme_color: "#1034A0",
        icons: [
          { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
          { src: "/icons/maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
        ],
      },
      workbox: {
        // Shell is cache-first; the API is never cached by the service worker (personal data, always fresh).
        navigateFallback: "/index.html",
        navigateFallbackDenylist: [/^\/api\//],
        globPatterns: ["**/*.{js,css,html,woff2,png,svg}"],
        runtimeCaching: [],
      },
    }),
  ],
  server: { port: 5173, proxy: { "/api": "http://localhost:8000" } },
  preview: { port: 4173, proxy: { "/api": "http://localhost:8000" } },
  build: { target: "es2022", sourcemap: false, chunkSizeWarningLimit: 900 },
});
