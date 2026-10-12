/* Runtime wiring shared by every screen: platform adapter, API client, session store, query client. */
import { createApiClient, type ApiClient } from "@gazyar/core";
import { createWebPlatform } from "@gazyar/core/platform.web";
import { createQueryClient, createSessionStore } from "@gazyar/data";

const web = createWebPlatform();
/* Capacitor build (VITE_CLIENT_KIND=native): the refresh token travels in the body and is kept in the
 * WebView's app-private storage (Android/iOS sandbox) so the user stays logged in across restarts. */
const native = import.meta.env.VITE_CLIENT_KIND === "native";
export const platform = native ? { ...web, secureStorage: web.storage } : web;
export const sessionStore = createSessionStore();
export const queryClient = createQueryClient();

export const api: ApiClient = createApiClient({
  // "" = same origin (vite proxy in dev, nginx in prod). A Capacitor build sets VITE_API_BASE.
  baseUrl: (import.meta.env.VITE_API_BASE as string | undefined) ?? "",
  platform,
  clientKind: native ? "native" : "web",
  onSessionExpired: () => {
    sessionStore.clearSession();
    queryClient.clear();
  },
});
