/* HTTP client shared by both apps (and a future React Native app).
 *
 * - JSON in/out, ApiError for every failure (errors.ts).
 * - Access token in memory only; the refresh token is an httpOnly cookie on
 *   web, or in platform.secureStorage on native (ARCHITECTURE §4.2).
 * - A 401 for an expired/invalid access token triggers ONE shared refresh and
 *   one retry. Refresh tokens rotate with reuse detection on the server: two
 *   parallel refreshes would present the same token twice and the server
 *   would revoke the whole family, logging the user out. Hence single-flight. */

import type { Platform, UploadFile, UploadProgress } from "../platform";
import { API_MESSAGES, ApiError, errorFromResponse } from "./errors";

export type ClientKind = "web" | "native";
export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

type QueryScalar = string | number | boolean | null | undefined;
export type QueryValue = QueryScalar | readonly QueryScalar[];
export type Query = Readonly<Record<string, QueryValue>>;

export interface RequestOptions {
  query?: Query;
  /** JSON-serialised. undefined = no body. */
  body?: unknown;
  signal?: AbortSignal;
  /** Overrides the client default (20 s). */
  timeoutMs?: number;
  headers?: Record<string, string>;
  /** false = never attach the access token nor refresh on 401 (public endpoints). */
  auth?: boolean;
}

export interface UploadOptions {
  signal?: AbortSignal;
  /** Overrides the client default (120 s). */
  timeoutMs?: number;
  method?: "POST" | "PUT";
  /** Multipart field name of the file (default "file"). */
  fileField?: string;
}

/** Mirrors backend auth TokenOut. */
export interface TokenResponse {
  access_token: string;
  token_type?: string;
  expires_in: number;
  subject_type: "user" | "staff";
  subject_id: number;
  /** Native clients only (X-Client: native); web gets an httpOnly cookie. */
  refresh_token?: string | null;
}

export interface ApiClientOptions {
  /** API origin, e.g. "https://api.example.ir", or "" for same-origin. */
  baseUrl: string;
  platform: Platform;
  clientKind: ClientKind;
  /** Called once when the session can no longer be renewed (refresh refused). */
  onSessionExpired?: () => void;
  timeoutMs?: number;
  uploadTimeoutMs?: number;
}

export interface ApiClient {
  request<T = unknown>(method: HttpMethod, path: string, options?: RequestOptions): Promise<T>;
  get<T = unknown>(path: string, options?: Omit<RequestOptions, "body">): Promise<T>;
  post<T = unknown>(path: string, body?: unknown, options?: Omit<RequestOptions, "body">): Promise<T>;
  put<T = unknown>(path: string, body?: unknown, options?: Omit<RequestOptions, "body">): Promise<T>;
  patch<T = unknown>(path: string, body?: unknown, options?: Omit<RequestOptions, "body">): Promise<T>;
  del<T = unknown>(path: string, options?: RequestOptions): Promise<T>;
  /** Multipart upload through platform.upload (XHR progress on web). */
  upload<T = unknown>(
    path: string,
    file: UploadFile,
    fields?: Readonly<Record<string, string | number | boolean>>,
    onProgress?: (p: UploadProgress) => void,
    options?: UploadOptions,
  ): Promise<T>;

  getAccessToken(): string | null;
  setAccessToken(token: string | null): void;
  /** Store a login/refresh response: access token in memory, native refresh token in secureStorage. */
  setTokens(tokens: TokenResponse): Promise<void>;
  /** Forget all tokens locally (no request, no onSessionExpired). */
  clearTokens(): Promise<void>;
  /**
   * Boot-time session restore: refresh using the cookie (web) or the stored
   * refresh token (native). Resolves the new tokens, or null when there is no
   * valid session (tokens are cleared, onSessionExpired is NOT called — the
   * person simply is not logged in). Rejects with ApiError on transport/5xx
   * failures so an offline boot does not look like a logout.
   */
  restoreSession(): Promise<TokenResponse | null>;
  /** Best-effort server logout (revokes the refresh token), then clearTokens(). */
  logout(): Promise<void>;
}

export const REFRESH_PATH = "/api/v1/auth/refresh";
export const LOGOUT_PATH = "/api/v1/auth/logout";
/** secureStorage key of the native refresh token. */
export const REFRESH_TOKEN_KEY = "gazyar.refresh_token";

const DEFAULT_TIMEOUT_MS = 20_000;
const DEFAULT_UPLOAD_TIMEOUT_MS = 120_000;

/** 401 codes that mean "your access token is no good" (backend core/deps.py). */
const REFRESHABLE_401 = new Set(["token_expired", "not_authenticated"]);

/* ─── pure helpers ───────────────────────────────────────────────────────── */

/**
 * `?a=1&tags=x&tags=y`. undefined/null are skipped (an unset filter must not
 * become "?status=undefined"); arrays repeat the key, which is what FastAPI's
 * `list[str] = Query()` expects. Hand-rolled: React Native's URLSearchParams
 * polyfill is incomplete.
 */
export function buildQuery(query?: Query): string {
  if (!query) return "";
  const parts: string[] = [];
  const add = (k: string, v: QueryScalar) => {
    if (v === undefined || v === null) return;
    parts.push(`${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`);
  };
  for (const [k, v] of Object.entries(query)) {
    if (Array.isArray(v)) for (const item of v as readonly QueryScalar[]) add(k, item);
    else add(k, v as QueryScalar);
  }
  return parts.length ? `?${parts.join("&")}` : "";
}

/** baseUrl + path, tolerant of a trailing/missing slash; absolute URLs pass through. */
export function joinUrl(baseUrl: string, path: string): string {
  if (/^https?:\/\//i.test(path)) return path;
  return baseUrl.replace(/\/+$/, "") + (path.startsWith("/") ? path : `/${path}`);
}

/** What both transports (fetch, platform.upload) are reduced to. */
interface RawResponse {
  status: number;
  body: string;
  header(name: string): string | null;
}

const ok = (status: number) => status >= 200 && status < 300;

function parseBody<T>(raw: RawResponse): T {
  if (raw.status === 204 || raw.body === "") return undefined as T;
  const type = raw.header("content-type");
  // Upload responses carry no headers; the API only ever answers JSON there.
  if (type === null || /json/i.test(type)) {
    try {
      return JSON.parse(raw.body) as T;
    } catch (e) {
      if (type !== null) {
        throw new ApiError({
          status: raw.status,
          code: "bad_response",
          message: API_MESSAGES.badResponse,
          requestId: raw.header("x-request-id"),
          cause: e,
        });
      }
    }
  }
  // Non-JSON 2xx (a CSV export, plain text): hand back the text.
  return raw.body as T;
}

/**
 * Run `fn` with a signal that aborts on timeout or when `outer` aborts, and
 * map transport failures: timeout → ApiError "timeout"; caller cancellation →
 * the original AbortError (React Query treats that as a cancel, not a failure);
 * anything else thrown by the transport → ApiError "network_error".
 */
async function withTimeout<R>(fn: (signal: AbortSignal) => Promise<R>, timeoutMs: number, outer?: AbortSignal): Promise<R> {
  const ctrl = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    ctrl.abort();
  }, timeoutMs);
  // Linked by hand: AbortSignal.any is missing on Hermes and older Safari.
  const onOuter = () => ctrl.abort(outer?.reason);
  if (outer) {
    if (outer.aborted) ctrl.abort(outer.reason);
    else outer.addEventListener("abort", onOuter, { once: true });
  }
  try {
    return await fn(ctrl.signal);
  } catch (e) {
    if (e instanceof ApiError) throw e;
    if (outer?.aborted) throw e;
    if (timedOut) throw new ApiError({ status: 0, code: "timeout", message: API_MESSAGES.timeout, cause: e });
    throw new ApiError({ status: 0, code: "network_error", message: API_MESSAGES.network, cause: e });
  } finally {
    clearTimeout(timer);
    outer?.removeEventListener("abort", onOuter);
  }
}

/* ─── client ─────────────────────────────────────────────────────────────── */

export function createApiClient(options: ApiClientOptions): ApiClient {
  const { platform, clientKind } = options;
  const native = clientKind === "native";
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const uploadTimeoutMs = options.uploadTimeoutMs ?? DEFAULT_UPLOAD_TIMEOUT_MS;
  // Web sends cookies on every call: the login response sets the refresh
  // cookie, and a cross-origin response's Set-Cookie is dropped without it.
  const credentials: RequestCredentials = native ? "omit" : "include";

  let accessToken: string | null = null;
  let refreshInFlight: Promise<TokenResponse | null> | null = null;

  const url = (path: string, query?: Query) => joinUrl(options.baseUrl, path) + buildQuery(query);

  function baseHeaders(extra?: Record<string, string>): Record<string, string> {
    const h: Record<string, string> = {
      Accept: "application/json",
      "Accept-Language": "fa",
      "X-Request-Id": platform.randomId(),
    };
    // On every call, not only refresh: login endpoints must also see it to
    // return the refresh token in the body instead of setting a cookie.
    if (native) h["X-Client"] = "native";
    return { ...h, ...extra };
  }

  async function fetchRaw(target: string, init: RequestInit): Promise<RawResponse> {
    const res = await platform.fetch(target, init);
    const body = await res.text();
    return { status: res.status, body, header: (n) => res.headers.get(n) };
  }

  async function readStoredRefreshToken(): Promise<string | null> {
    try {
      return await platform.secureStorage.get(REFRESH_TOKEN_KEY);
    } catch {
      return null;
    }
  }

  async function setTokens(t: TokenResponse): Promise<void> {
    accessToken = t.access_token;
    if (native && t.refresh_token) await platform.secureStorage.set(REFRESH_TOKEN_KEY, t.refresh_token);
  }

  async function clearTokens(): Promise<void> {
    accessToken = null;
    if (native) {
      try {
        await platform.secureStorage.remove(REFRESH_TOKEN_KEY);
      } catch {
        /* keystore unavailable: the server-side token still expires */
      }
    }
  }

  /** One refresh round-trip. null = session is gone (4xx); throws on transient failures. */
  async function doRefresh(): Promise<TokenResponse | null> {
    const headers = baseHeaders();
    let body: string | undefined;
    if (native) {
      const rt = await readStoredRefreshToken();
      if (!rt) return null;
      headers["Content-Type"] = "application/json";
      body = JSON.stringify({ refresh_token: rt });
    }
    const raw = await withTimeout(
      (signal) => fetchRaw(url(REFRESH_PATH), { method: "POST", headers, body, credentials, signal }),
      timeoutMs,
    );
    if (ok(raw.status)) {
      const data = parseBody<TokenResponse | undefined>(raw);
      if (!data || typeof data !== "object" || typeof data.access_token !== "string") {
        throw new ApiError({ status: raw.status, code: "bad_response", message: API_MESSAGES.badResponse });
      }
      await setTokens(data);
      return data;
    }
    // 408/429/5xx: the server could not answer now — keep the session.
    if (raw.status >= 400 && raw.status < 500 && raw.status !== 408 && raw.status !== 429) return null;
    throw errorFromResponse(raw.status, raw.body, raw.header);
  }

  /** Single-flight: every caller during a refresh shares the same promise. */
  function refreshShared(): Promise<TokenResponse | null> {
    refreshInFlight ??= doRefresh().finally(() => {
      refreshInFlight = null;
    });
    return refreshInFlight;
  }

  /**
   * Session is unrecoverable: clear and notify. The check-and-clear is
   * synchronous, so of N requests failing together only the first notifies.
   */
  function expireSession(): void {
    const had = accessToken !== null;
    void clearTokens();
    if (had) options.onSessionExpired?.();
  }

  /**
   * Send with the current token; on a refreshable 401 refresh once (shared)
   * and retry once. `send` is called again for the retry, with a new token.
   */
  async function authed(
    send: (token: string | null, signal: AbortSignal) => Promise<RawResponse>,
    auth: boolean,
    timeout: number,
    signal?: AbortSignal,
  ): Promise<RawResponse> {
    const used = auth ? accessToken : null;
    const first = await withTimeout((s) => send(used, s), timeout, signal);
    if (first.status !== 401 || !auth || used === null) return first;
    // A 401 without the envelope (a proxy's) is not ours to fix by refreshing.
    if (!REFRESHABLE_401.has(errorFromResponse(first.status, first.body).code)) return first;

    // Another request may already have refreshed while this one was in
    // flight: retry with the newer token instead of refreshing again.
    if (accessToken === null || accessToken === used) {
      const fresh = await refreshShared();
      if (!fresh) {
        expireSession();
        return first;
      }
    }
    const retryToken = accessToken;
    const second = await withTimeout((s) => send(retryToken, s), timeout, signal);
    // A just-issued token refused too: the account is disabled or revoked.
    if (second.status === 401) expireSession();
    return second;
  }

  async function request<T>(method: HttpMethod, path: string, opts: RequestOptions = {}): Promise<T> {
    const target = url(path, opts.query);
    const hasBody = opts.body !== undefined;
    const payload = hasBody ? JSON.stringify(opts.body) : undefined;
    const raw = await authed(
      (token, signal) => {
        const headers = baseHeaders(opts.headers);
        if (hasBody) headers["Content-Type"] = "application/json";
        if (token) headers.Authorization = `Bearer ${token}`;
        return fetchRaw(target, { method, headers, body: payload, credentials, signal });
      },
      opts.auth !== false,
      opts.timeoutMs ?? timeoutMs,
      opts.signal,
    );
    if (!ok(raw.status)) throw errorFromResponse(raw.status, raw.body, raw.header);
    return parseBody<T>(raw);
  }

  async function upload<T>(
    path: string,
    file: UploadFile,
    fields: Readonly<Record<string, string | number | boolean>> = {},
    onProgress?: (p: UploadProgress) => void,
    opts: UploadOptions = {},
  ): Promise<T> {
    const textFields: Record<string, string> = {};
    for (const [k, v] of Object.entries(fields)) textFields[k] = String(v);
    const raw = await authed(
      async (token, signal) => {
        const headers = baseHeaders();
        if (token) headers.Authorization = `Bearer ${token}`;
        const res = await platform.upload({
          url: url(path),
          method: opts.method ?? "POST",
          headers,
          fileField: opts.fileField ?? "file",
          file,
          fields: textFields,
          withCredentials: !native,
          signal,
          onProgress,
        });
        return { status: res.status, body: res.body, header: () => null };
      },
      true,
      opts.timeoutMs ?? uploadTimeoutMs,
      opts.signal,
    );
    if (!ok(raw.status)) throw errorFromResponse(raw.status, raw.body, raw.header);
    return parseBody<T>(raw);
  }

  async function restoreSession(): Promise<TokenResponse | null> {
    const t = await refreshShared();
    if (!t) await clearTokens();
    return t;
  }

  async function logout(): Promise<void> {
    try {
      const headers = baseHeaders();
      let body: string | undefined;
      if (native) {
        const rt = await readStoredRefreshToken();
        if (rt) {
          headers["Content-Type"] = "application/json";
          body = JSON.stringify({ refresh_token: rt });
        }
      }
      if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
      await withTimeout(
        (signal) => fetchRaw(url(LOGOUT_PATH), { method: "POST", headers, body, credentials, signal }),
        timeoutMs,
      );
    } catch {
      // Offline logout still logs out locally; the token expires server-side.
    }
    await clearTokens();
  }

  return {
    request,
    get: (path, o) => request("GET", path, o),
    post: (path, body, o) => request("POST", path, { ...o, body }),
    put: (path, body, o) => request("PUT", path, { ...o, body }),
    patch: (path, body, o) => request("PATCH", path, { ...o, body }),
    del: (path, o) => request("DELETE", path, o),
    upload,
    getAccessToken: () => accessToken,
    setAccessToken: (t) => {
      accessToken = t;
    },
    setTokens,
    clearTokens,
    restoreSession,
    logout,
  };
}
