/* Error contract (ARCHITECTURE §4.1): every failure a screen can see is an
 * ApiError with a stable `code` to switch on and a Persian `message` to show.
 * Server errors carry the server's own message; transport failures (offline,
 * timeout, a proxy's HTML 502) get the client-side Persian fallbacks below. */

export const API_MESSAGES = {
  network: "اتصال به اینترنت برقرار نیست",
  timeout: "پاسخی از سرور دریافت نشد؛ دوباره تلاش کنید",
  server: "خطای سرور؛ دوباره تلاش کنید",
  rateLimited: "تعداد درخواست‌ها بیش از حد مجاز است؛ کمی بعد دوباره تلاش کنید",
  notAuthenticated: "ابتدا وارد حساب کاربری شوید",
  forbidden: "شما به این بخش دسترسی ندارید",
  notFound: "موردی پیدا نشد",
  badResponse: "پاسخ نامعتبر از سرور دریافت شد",
  generic: "درخواست قابل انجام نیست",
  unknown: "خطای پیش‌بینی‌نشده؛ دوباره تلاش کنید",
} as const;

/** Codes produced by the client itself (status 0 = no HTTP response). */
export type ClientErrorCode = "network_error" | "timeout" | "server_error" | "rate_limited" | "bad_response" | "http_error";

export interface ApiErrorInit {
  status: number;
  code: string;
  message: string;
  details?: Record<string, unknown>;
  requestId?: string | null;
  retryAfter?: number | null;
  cause?: unknown;
}

export class ApiError extends Error {
  override readonly name = "ApiError";
  /** HTTP status; 0 when no response arrived (offline, timeout). */
  readonly status: number;
  /** Stable snake_case code from the server, or a ClientErrorCode. */
  readonly code: string;
  readonly details: Record<string, unknown>;
  /** X-Request-Id of the failed call — what support asks for. */
  readonly requestId: string | null;
  /** Seconds to wait (429 Retry-After), when the server said. */
  readonly retryAfter: number | null;

  constructor(init: ApiErrorInit) {
    super(init.message, init.cause === undefined ? undefined : { cause: init.cause });
    this.status = init.status;
    this.code = init.code;
    this.details = init.details ?? {};
    this.requestId = init.requestId ?? null;
    this.retryAfter = init.retryAfter ?? null;
  }

  /** No HTTP response at all: offline or timed out. Worth retrying. */
  get isTransport(): boolean {
    return this.status === 0;
  }

  /** 4xx: the request itself is wrong or not allowed — retrying cannot help. */
  get isClientError(): boolean {
    return this.status >= 400 && this.status < 500;
  }

  get isServerError(): boolean {
    return this.status >= 500;
  }

  /** Per-field Persian messages of a 422 validation_error (`details.fields`). */
  get fieldErrors(): Record<string, string> {
    const f = this.details.fields;
    if (!f || typeof f !== "object" || Array.isArray(f)) return {};
    const out: Record<string, string> = {};
    for (const [k, v] of Object.entries(f as Record<string, unknown>)) if (typeof v === "string") out[k] = v;
    return out;
  }
}

export function isApiError(e: unknown): e is ApiError {
  return e instanceof ApiError;
}

/** True for a cancellation (AbortController), which must not be shown as an error. */
export function isAbortError(e: unknown): boolean {
  return typeof e === "object" && e !== null && (e as { name?: unknown }).name === "AbortError";
}

/** The Persian message to show for any thrown value (toasts, error states). */
export function errorMessage(e: unknown): string {
  if (e instanceof ApiError) return e.message;
  return API_MESSAGES.unknown;
}

function fallbackMessage(status: number): string {
  if (status === 401) return API_MESSAGES.notAuthenticated;
  if (status === 403) return API_MESSAGES.forbidden;
  if (status === 404) return API_MESSAGES.notFound;
  if (status === 429) return API_MESSAGES.rateLimited;
  if (status >= 500) return API_MESSAGES.server;
  return API_MESSAGES.generic;
}

function parseRetryAfter(header: string | null, details: Record<string, unknown>): number | null {
  const fromDetails = details.retry_after;
  if (typeof fromDetails === "number" && Number.isFinite(fromDetails)) return Math.max(0, fromDetails);
  if (header && /^\d+$/.test(header.trim())) return Number(header.trim());
  return null;
}

/**
 * Non-2xx response → ApiError. Accepts the server envelope
 * `{"error": {"code","message","details"}}`; anything else (an nginx HTML 502,
 * an empty body) falls back to a status-based code and Persian message.
 */
export function errorFromResponse(
  status: number,
  body: string,
  header: (name: string) => string | null = () => null,
): ApiError {
  let code: string | null = null;
  let message: string | null = null;
  let details: Record<string, unknown> = {};
  try {
    const parsed: unknown = body ? JSON.parse(body) : null;
    const env = parsed && typeof parsed === "object" ? (parsed as { error?: unknown }).error : null;
    if (env && typeof env === "object") {
      const e = env as { code?: unknown; message?: unknown; details?: unknown };
      if (typeof e.code === "string" && e.code) code = e.code;
      if (typeof e.message === "string" && e.message.trim()) message = e.message;
      if (e.details && typeof e.details === "object" && !Array.isArray(e.details)) {
        details = e.details as Record<string, unknown>;
      }
    }
  } catch {
    /* not JSON — use the fallbacks */
  }
  if (status === 429) code = "rate_limited"; // clients key back-off UI on this one code
  return new ApiError({
    status,
    code: code ?? (status >= 500 ? "server_error" : "http_error"),
    message: message ?? fallbackMessage(status),
    details,
    requestId: header("x-request-id"),
    retryAfter: status === 429 ? parseRetryAfter(header("retry-after"), details) : null,
  });
}
