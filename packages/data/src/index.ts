/* @gazyar/data — React (no DOM) data layer over @gazyar/core's ApiClient. */

export { createQueryClient, shouldRetry, retryDelay, QUERY_STALE_TIME_MS, MAX_TRANSIENT_RETRIES } from "./queryClient";
export type { CreateQueryClientOptions, QueryErrorSource } from "./queryClient";
export { ApiProvider, DataProvider, useApi } from "./ApiProvider";
export type { ApiProviderProps, DataProviderProps } from "./ApiProvider";
export { ANONYMOUS, LOADING, can, canAny, createSessionStore } from "./sessionStore";
export type { SessionState, SessionStatus, SessionStore, SessionSubject } from "./sessionStore";
export { SessionProvider, useCan, useSession } from "./session";
export type { SessionContextValue, SessionProviderProps } from "./session";
export { cleanParams, qk } from "./keys";
export type { CleanParams, Id, ListParams, ParamValue, QueryDomain } from "./keys";
export { useApiGet, useApiMutation, useApiQuery, useLogout } from "./hooks";
export type { ApiMutationOptions, ApiQueryOptions } from "./hooks";
