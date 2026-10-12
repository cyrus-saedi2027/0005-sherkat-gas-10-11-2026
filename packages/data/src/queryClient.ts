/* QueryClient defaults for both apps (and a future React Native app).
 *
 * Retry policy: a 4xx is an answer, not a failure — retrying a 403 or a 422
 * just shows the same error three seconds later, and retrying a 429 makes the
 * rate limit worse. Only transport failures (offline, timeout) and 5xx are
 * retried, at most twice. Mutations are never retried automatically: a POST
 * that timed out may have succeeded, and replaying a redemption or an award
 * request is how points get spent twice. */

import { MutationCache, QueryCache, QueryClient, type MutationMeta, type QueryMeta } from "@tanstack/react-query";
import { ApiError, isAbortError } from "@gazyar/core";

export const QUERY_STALE_TIME_MS = 30_000;
export const MAX_TRANSIENT_RETRIES = 2;
const MAX_RETRY_DELAY_MS = 8_000;

/**
 * TanStack `retry` callback. `failureCount` is the number of failures before
 * this one (0 on the first failure), so `< MAX_TRANSIENT_RETRIES` allows
 * exactly two retries.
 */
export function shouldRetry(failureCount: number, error: unknown): boolean {
  if (failureCount >= MAX_TRANSIENT_RETRIES) return false;
  if (isAbortError(error)) return false;
  // Anything that is not an ApiError is a bug in our own code (a bad
  // `select`, a TypeError); retrying it only delays the error screen.
  if (!(error instanceof ApiError)) return false;
  return error.isTransport || error.isServerError;
}

/** 1 s, 2 s, 4 s … capped at 8 s: a phone on a flaky network recovers in seconds, and a longer wait just looks frozen. */
export function retryDelay(failureCount: number): number {
  return Math.min(1_000 * 2 ** failureCount, MAX_RETRY_DELAY_MS);
}

export interface QueryErrorSource {
  kind: "query" | "mutation";
  meta: QueryMeta | MutationMeta | undefined;
}

export interface CreateQueryClientOptions {
  /**
   * Called for every failed query/mutation except cancellations — the place
   * for the "toast the server message" rule (ARCHITECTURE §6.2). Set
   * `meta: { silentError: true }` on a query/mutation that shows its own error.
   */
  onError?: (error: unknown, source: QueryErrorSource) => void;
}

export function createQueryClient(options: CreateQueryClientOptions = {}): QueryClient {
  const report = (error: unknown, source: QueryErrorSource) => {
    if (isAbortError(error) || source.meta?.silentError === true) return;
    options.onError?.(error, source);
  };
  return new QueryClient({
    queryCache: new QueryCache({ onError: (error, query) => report(error, { kind: "query", meta: query.meta }) }),
    mutationCache: new MutationCache({
      onError: (error, _vars, _ctx, mutation) => report(error, { kind: "mutation", meta: mutation.meta }),
    }),
    defaultOptions: {
      queries: {
        staleTime: QUERY_STALE_TIME_MS,
        retry: shouldRetry,
        retryDelay,
        // The admin panel lives in a tab people switch away from constantly;
        // refetching every list on every focus floods the API (R36 rate limits).
        refetchOnWindowFocus: false,
      },
      mutations: { retry: false },
    },
  });
}
