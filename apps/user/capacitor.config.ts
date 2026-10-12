/* Native wrapper for the subscriber app (ARCHITECTURE §2). `npx cap add android` creates the project.
 * The web build (dist/) is bundled into the APK; the API base URL is set at build time via VITE_API_BASE. */
const config = {
  appId: "ir.gazyar.app",
  appName: "گازیار",
  webDir: "dist",
  server: { androidScheme: "https" },
  android: { allowMixedContent: false },
};
export default config;
