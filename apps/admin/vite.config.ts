import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Staff panel, served under /admin/ next to the subscriber app (deploy/nginx.conf).
export default defineConfig({
  base: "/admin/",
  plugins: [react()],
  server: { port: 5174, proxy: { "/api": "http://localhost:8000" } },
  preview: { port: 4174, proxy: { "/api": "http://localhost:8000" } },
  build: { target: "es2022", sourcemap: false, chunkSizeWarningLimit: 1200 },
});
