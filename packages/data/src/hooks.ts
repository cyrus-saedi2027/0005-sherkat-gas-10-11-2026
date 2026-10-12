/* Thin typed wrappers over TanStack Query: the error type is always ApiError
 * (the client normalises every failure to it), and the ApiClient comes from
 * context so feature hooks are one-liners:
 *
 *   const readings = useApiGet<Page<Reading>>(qk.readings.list(p), "/api/v1/app/readings", p);
 *   const approve = useApiMutation((api, id: number) => api.post(`/api/v1/admin/readings/${id}/approve`),
 *                                  { invalidate: [qk.readings.lists(), qk.dashboard.all] });
 */

import {
  useMutation,
  useQuery,
  useQueryClient,
  type QueryKey,
  type UseMutationOptions,
  type UseMutationResult,
  type UseQueryOptions,
  type UseQueryResult,
} from "@tanstack/react-query";
import type { ApiClient, ApiError, Query } from "@gazyar/core";
import { useApi } from "./ApiProvider";
import { useSession } from "./session";

export type ApiQueryOptions<TQueryFnData, TData = TQueryFnData, TKey extends QueryKey = QueryKey> = Omit<
  UseQueryOptions<TQueryFnData, ApiError, TData, TKey>,
  "queryKey" | "queryFn"
>;

/** useQuery with ApiError as the error type and the ApiClient injected. */
export function useApiQuery<TQueryFnData, TData = TQueryFnData, TKey extends QueryKey = QueryKey>(
  queryKey: TKey,
  fetcher: (api: ApiClient, signal: AbortSignal) => Promise<TQueryFnData>,
  options?: ApiQueryOptions<TQueryFnData, TData, TKey>,
): UseQueryResult<TData, ApiError> {
  const api = useApi();
  return useQuery<TQueryFnData, ApiError, TData, TKey>({
    ...options,
    queryKey,
    // The signal lets TanStack cancel a superseded request (filter changed).
    queryFn: ({ signal }) => fetcher(api, signal),
  });
}

/** The common case: GET `path` with `query`. */
export function useApiGet<TQueryFnData, TData = TQueryFnData, TKey extends QueryKey = QueryKey>(
  queryKey: TKey,
  path: string,
  query?: Query,
  options?: ApiQueryOptions<TQueryFnData, TData, TKey>,
): UseQueryResult<TData, ApiError> {
  return useApiQuery<TQueryFnData, TData, TKey>(queryKey, (api, signal) => api.get<TQueryFnData>(path, { query, signal }), options);
}

export type ApiMutationOptions<TData, TVariables, TOnMutateResult = unknown> = Omit<
  UseMutationOptions<TData, ApiError, TVariables, TOnMutateResult>,
  "mutationFn"
> & {
  /**
   * Keys to invalidate after success (prefix match). Awaited before the
   * mutation settles, so `isPending` covers the refetch and a list never
   * flashes its stale row after the success toast.
   */
  invalidate?: readonly QueryKey[] | ((data: TData, variables: TVariables) => readonly QueryKey[]);
};

/** useMutation with ApiError as the error type, the ApiClient injected, and precise invalidation. */
export function useApiMutation<TData = unknown, TVariables = void, TOnMutateResult = unknown>(
  mutate: (api: ApiClient, variables: TVariables) => Promise<TData>,
  options: ApiMutationOptions<TData, TVariables, TOnMutateResult> = {},
): UseMutationResult<TData, ApiError, TVariables, TOnMutateResult> {
  const api = useApi();
  const queryClient = useQueryClient();
  const { invalidate, onSuccess, ...rest } = options;
  return useMutation<TData, ApiError, TVariables, TOnMutateResult>({
    ...rest,
    mutationFn: (variables) => mutate(api, variables),
    onSuccess: async (data, variables, onMutateResult, context) => {
      const keys = typeof invalidate === "function" ? invalidate(data, variables) : (invalidate ?? []);
      await Promise.all(keys.map((queryKey) => queryClient.invalidateQueries({ queryKey })));
      return onSuccess?.(data, variables, onMutateResult, context);
    },
  });
}

/**
 * Log out everywhere this app knows about: revoke the refresh token on the
 * server, drop the in-memory access token, clear the session, and drop the
 * whole query cache — the next person on a shared phone must not see the
 * previous subscriber's readings from cache.
 */
export function useLogout(): () => Promise<void> {
  const api = useApi();
  const queryClient = useQueryClient();
  const { clearSession } = useSession();
  return async () => {
    await api.logout();
    clearSession();
    queryClient.clear();
  };
}
