import { defineConfig, devices } from "@playwright/test";

/* E2E: real backend (fresh demo seed) + both apps on Vite dev servers. Chromium 1194 is preinstalled
 * (PLAYWRIGHT_BROWSERS_PATH) and matches @playwright/test 1.56.1. */
export default defineConfig({
  testDir: ".",
  outputDir: ".artifacts/results",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [["list"], ["html", { outputFolder: ".artifacts/report", open: "never" }]],
  use: {
    locale: "fa-IR",
    timezoneId: "Asia/Tehran",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "user-mobile", testMatch: /user\/.*\.spec\.ts/, use: { ...devices["Pixel 7"], baseURL: "http://localhost:5173" } },
    { name: "admin-desktop", testMatch: /admin\/.*\.spec\.ts/, use: { viewport: { width: 1440, height: 900 }, baseURL: "http://localhost:5174/admin/" } },
    { name: "admin-tablet", testMatch: /admin\/.*responsive\.spec\.ts/, use: { viewport: { width: 768, height: 1024 }, baseURL: "http://localhost:5174/admin/" } },
  ],
  webServer: [
    { command: "bash ../scripts/e2e-backend.sh", url: "http://127.0.0.1:8000/api/v1/health", reuseExistingServer: false, timeout: 120_000 },
    { command: "pnpm --filter @gazyar/user dev --port 5173 --strictPort", url: "http://localhost:5173", reuseExistingServer: true, timeout: 120_000 },
    { command: "pnpm --filter @gazyar/admin dev --port 5174 --strictPort", url: "http://localhost:5174/admin/", reuseExistingServer: true, timeout: 120_000 },
  ],
});
