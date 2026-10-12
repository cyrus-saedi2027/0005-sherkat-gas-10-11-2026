/* Runtime wiring shared by every screen: platform adapter, API client, session store, query client. */
import { createApiClient, type ApiClient } from "@gazyar/core";
import { createWebPlatform } from "@gazyar/core/platform.web";
import { createQueryClient, createSessionStore } from "@gazyar/data";

export const platform = createWebPlatform();
export const sessionStore = createSessionStore();
export const queryClient = createQueryClient();

export const api: ApiClient = createApiClient({
  // "" = same origin (vite proxy in dev, nginx in prod). A Capacitor build sets VITE_API_BASE.
  baseUrl: (import.meta.env.VITE_API_BASE as string | undefined) ?? "",
  platform,
  clientKind: "web",
  onSessionExpired: () => {
    sessionStore.clearSession();
    queryClient.clear();
  },
});
