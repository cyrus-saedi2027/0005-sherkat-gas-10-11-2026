/* Makes the core ApiClient available to hooks. The client is created once per
 * app (outside React, so its onSessionExpired can reach the session store) and
 * injected here; data hooks never construct their own. */

import { createContext, useContext, type ReactNode } from "react";
import { QueryClientProvider, type QueryClient } from "@tanstack/react-query";
import type { ApiClient } from "@gazyar/core";

const ApiContext = createContext<ApiClient | null>(null);

export interface ApiProviderProps {
  client: ApiClient;
  children?: ReactNode;
}

export function ApiProvider({ client, children }: ApiProviderProps) {
  return <ApiContext.Provider value={client}>{children}</ApiContext.Provider>;
}

/** The ApiClient from the nearest <ApiProvider>. Throws outside one — a silent
 *  null would surface later as "cannot read properties of null (reading get)". */
export function useApi(): ApiClient {
  const client = useContext(ApiContext);
  if (!client) throw new Error("useApi() must be used inside <ApiProvider>.");
  return client;
}

export interface DataProviderProps {
  client: ApiClient;
  queryClient: QueryClient;
  children?: ReactNode;
}

/** QueryClientProvider + ApiProvider in one, the order every app needs. */
export function DataProvider({ client, queryClient, children }: DataProviderProps) {
  return (
    <QueryClientProvider client={queryClient}>
      <ApiProvider client={client}>{children}</ApiProvider>
    </QueryClientProvider>
  );
}
