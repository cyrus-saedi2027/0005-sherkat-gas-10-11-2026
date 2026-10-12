import { memoryStorage, type Platform, type UploadRequest, type UploadResponse } from "../platform";
import {
  buildQuery,
  createApiClient,
  joinUrl,
  REFRESH_PATH,
  REFRESH_TOKEN_KEY,
  type ApiClientOptions,
  type TokenResponse,
} from "./client";
import { API_MESSAGES, ApiError, errorMessage, isAbortError } from "./errors";

/* ─── harness ────────────────────────────────────────────────────────────── */

const BASE = "http://api.test";

interface Call {
  url: string;
  method: string;
  headers: Record<string, string>;
  body: string | undefined;
  credentials: RequestCredentials | undefined;
}

type Handler = (call: Call, signal: AbortSignal | undefined) => Response | Promise<Response>;

const json = (status: number, data: unknown, headers: Record<string, string> = {}) =>
  new Response(JSON.stringify(data), { status, headers: { "content-type": "application/json", ...headers } });

const envelope = (status: number, code: string, message: string, details: Record<string, unknown> = {}, headers = {}) =>
  json(status, { error: { code, message, details } }, headers);

const expired = () => envelope(401, "token_expired", "نشست شما منقضی شده است.");

const tokens = (access: string, refresh?: string): TokenResponse => ({
  access_token: access,
  token_type: "bearer",
  expires_in: 900,
  subject_type: "user",
  subject_id: 7,
  ...(refresh ? { refresh_token: refresh } : {}),
});

const tick = (ms = 0) => new Promise((r) => setTimeout(r, ms));

function setup(handler: Handler, opts: Partial<ApiClientOptions> & { secure?: Record<string, string> } = {}) {
  const calls: Call[] = [];
  const uploads: UploadRequest[] = [];
  let seq = 0;
  const fetchMock = (async (input: RequestInfo | URL, init: RequestInit = {}) => {
    const call: Call = {
      url: String(input),
      method: init.method ?? "GET",
      headers: { ...(init.headers as Record<string, string>) },
      body: init.body as string | undefined,
      credentials: init.credentials,
    };
    calls.push(call);
    return handler(call, init.signal ?? undefined);
  }) as typeof fetch;
  const secureStorage = memoryStorage(opts.secure);
  let uploadImpl: (req: UploadRequest) => Promise<UploadResponse> = async () => ({ status: 200, body: "{}" });
  const platform: Platform = {
    fetch: fetchMock,
    storage: memoryStorage(),
    secureStorage,
    randomId: () => `rid-${++seq}`,
    deviceId: async () => "device-1",
    upload: (req) => {
      uploads.push(req);
      return uploadImpl(req);
    },
    haptic: () => {},
  };
  const onSessionExpired = vi.fn();
  const client = createApiClient({ baseUrl: BASE, platform, clientKind: "web", onSessionExpired, ...opts });
  const refreshCalls = () => calls.filter((c) => c.url === BASE + REFRESH_PATH);
  return {
    client,
    calls,
    uploads,
    secureStorage,
    onSessionExpired,
    refreshCalls,
    setUpload: (f: typeof uploadImpl) => {
      uploadImpl = f;
    },
  };
}

async function caught(p: Promise<unknown>): Promise<unknown> {
  try {
    await p;
  } catch (e) {
    return e;
  }
  throw new Error("expected a rejection");
}

/* ─── pure helpers ───────────────────────────────────────────────────────── */

describe("buildQuery / joinUrl", () => {
  it("skips undefined/null, repeats arrays, encodes values", () => {
    expect(buildQuery()).toBe("");
    expect(buildQuery({ a: undefined, b: null })).toBe("");
    expect(buildQuery({ page: 2, status: ["pending", "flagged"], q: "علی رضا", ok: true, n: null })).toBe(
      "?page=2&status=pending&status=flagged&q=%D8%B9%D9%84%DB%8C%20%D8%B1%D8%B6%D8%A7&ok=true",
    );
    expect(buildQuery({ list: [1, null, 3] })).toBe("?list=1&list=3");
    expect(buildQuery({ "a&b": "x=y" })).toBe("?a%26b=x%3Dy");
  });

  it("joins base and path regardless of slashes", () => {
    expect(joinUrl("http://a.test/", "/api/v1/x")).toBe("http://a.test/api/v1/x");
    expect(joinUrl("http://a.test", "api/v1/x")).toBe("http://a.test/api/v1/x");
    expect(joinUrl("", "/api/v1/x")).toBe("/api/v1/x");
    expect(joinUrl("http://a.test", "https://cdn.test/f")).toBe("https://cdn.test/f");
  });
});

/* ─── requests ───────────────────────────────────────────────────────────── */

describe("requests", () => {
  it("sends JSON with the standard headers and parses JSON", async () => {
    const h = setup(() => json(200, { ok: 1 }));
    const out = await h.client.get<{ ok: number }>("/api/v1/app/me", { query: { a: 1, b: undefined, tags: ["x", "y"] } });
    expect(out).toEqual({ ok: 1 });
    const c = h.calls[0]!;
    expect(c.url).toBe(`${BASE}/api/v1/app/me?a=1&tags=x&tags=y`);
    expect(c.method).toBe("GET");
    expect(c.headers["Accept-Language"]).toBe("fa");
    expect(c.headers["X-Request-Id"]).toBe("rid-1");
    expect(c.headers.Authorization).toBeUndefined();
    expect(c.headers["X-Client"]).toBeUndefined();
    expect(c.headers["Content-Type"]).toBeUndefined();
    expect(c.credentials).toBe("include");
  });

  it("serialises bodies and attaches the bearer token", async () => {
    const h = setup(() => json(201, { id: 5 }));
    h.client.setAccessToken("tok");
    expect(h.client.getAccessToken()).toBe("tok");
    await h.client.post("/api/v1/x", { value: 12, note: "سلام" });
    await h.client.put("/api/v1/x/5", { a: 1 });
    await h.client.patch("/api/v1/x/5", { b: 2 });
    await h.client.del("/api/v1/x/5");
    expect(h.calls.map((c) => c.method)).toEqual(["POST", "PUT", "PATCH", "DELETE"]);
    expect(h.calls[0]!.body).toBe(JSON.stringify({ value: 12, note: "سلام" }));
    expect(h.calls[0]!.headers["Content-Type"]).toBe("application/json");
    expect(h.calls[3]!.body).toBeUndefined();
    for (const c of h.calls) expect(c.headers.Authorization).toBe("Bearer tok");
    // A fresh id per request.
    expect(new Set(h.calls.map((c) => c.headers["X-Request-Id"])).size).toBe(4);
  });

  it("returns undefined for 204 and text for non-JSON bodies", async () => {
    const h = setup((c) =>
      c.url.endsWith("/csv") ? new Response("a,b\n1,2", { headers: { "content-type": "text/csv" } }) : new Response(null, { status: 204 }),
    );
    expect(await h.client.del("/api/v1/x/1")).toBeUndefined();
    expect(await h.client.get("/api/v1/csv")).toBe("a,b\n1,2");
  });

  it("does not attach the token when auth is false", async () => {
    const h = setup(() => json(200, {}));
    h.client.setAccessToken("tok");
    await h.client.post("/api/v1/app/auth/signup/start", { mobile: "09121234567" }, { auth: false });
    expect(h.calls[0]!.headers.Authorization).toBeUndefined();
  });

  it("sends X-Client: native on every native request, without cookies", async () => {
    const h = setup(() => json(200, {}), { clientKind: "native" });
    await h.client.get("/api/v1/x");
    expect(h.calls[0]!.headers["X-Client"]).toBe("native");
    expect(h.calls[0]!.credentials).toBe("omit");
  });
});

/* ─── error contract ─────────────────────────────────────────────────────── */

describe("error mapping", () => {
  it("maps the server envelope to ApiError", async () => {
    const h = setup(() =>
      envelope(422, "validation_error", "اطلاعات واردشده کامل یا معتبر نیست.", { fields: { mobile: "این فیلد الزامی است.", n: 3 } }, {
        "x-request-id": "srv-1",
      }),
    );
    const e = (await caught(h.client.post("/api/v1/x", {}))) as ApiError;
    expect(e).toBeInstanceOf(ApiError);
    expect(e.status).toBe(422);
    expect(e.code).toBe("validation_error");
    expect(e.message).toBe("اطلاعات واردشده کامل یا معتبر نیست.");
    expect(e.requestId).toBe("srv-1");
    expect(e.fieldErrors).toEqual({ mobile: "این فیلد الزامی است." });
    expect(e.isClientError).toBe(true);
    expect(errorMessage(e)).toBe(e.message);
  });

  it("maps 429 to rate_limited with retryAfter", async () => {
    const h = setup(() => envelope(429, "rate_limited", "کمی بعد دوباره تلاش کنید.", { retry_after: 42 }));
    const e = (await caught(h.client.get("/api/v1/x"))) as ApiError;
    expect(e.code).toBe("rate_limited");
    expect(e.retryAfter).toBe(42);

    const h2 = setup(() => new Response("slow down", { status: 429, headers: { "retry-after": "17" } }));
    const e2 = (await caught(h2.client.get("/api/v1/x"))) as ApiError;
    expect(e2.code).toBe("rate_limited");
    expect(e2.retryAfter).toBe(17);
    expect(e2.message).toBe(API_MESSAGES.rateLimited);
  });

  it("falls back to Persian messages for non-envelope 5xx", async () => {
    const h = setup(() => new Response("<html>502 Bad Gateway</html>", { status: 502, headers: { "content-type": "text/html" } }));
    const e = (await caught(h.client.get("/api/v1/x"))) as ApiError;
    expect(e.status).toBe(502);
    expect(e.code).toBe("server_error");
    expect(e.message).toBe("خطای سرور؛ دوباره تلاش کنید");
    expect(e.isServerError).toBe(true);
  });

  it("keeps the server's own 5xx message when present", async () => {
    const h = setup(() => envelope(500, "server_error", "خطای داخلی سرور؛ لطفاً دوباره تلاش کنید."));
    const e = (await caught(h.client.get("/api/v1/x"))) as ApiError;
    expect(e.message).toBe("خطای داخلی سرور؛ لطفاً دوباره تلاش کنید.");
  });

  it("maps a failed fetch to network_error (status 0)", async () => {
    const h = setup(() => {
      throw new TypeError("Failed to fetch");
    });
    const e = (await caught(h.client.get("/api/v1/x"))) as ApiError;
    expect(e).toBeInstanceOf(ApiError);
    expect(e.status).toBe(0);
    expect(e.code).toBe("network_error");
    expect(e.message).toBe("اتصال به اینترنت برقرار نیست");
    expect(e.isTransport).toBe(true);
  });

  it("times out via AbortController", async () => {
    const h = setup(
      (_c, signal) =>
        new Promise<Response>((_res, rej) => {
          signal?.addEventListener("abort", () => rej(new DOMException("aborted", "AbortError")));
        }),
      { timeoutMs: 15 },
    );
    const e = (await caught(h.client.get("/api/v1/x"))) as ApiError;
    expect(e).toBeInstanceOf(ApiError);
    expect(e.code).toBe("timeout");
    expect(e.status).toBe(0);
    expect(e.message).toBe(API_MESSAGES.timeout);
  });

  it("propagates caller cancellation as an AbortError, not an ApiError", async () => {
    const h = setup(
      (_c, signal) =>
        new Promise<Response>((_res, rej) => {
          signal?.addEventListener("abort", () => rej(new DOMException("aborted", "AbortError")));
        }),
    );
    const ctrl = new AbortController();
    const p = h.client.get("/api/v1/x", { signal: ctrl.signal });
    ctrl.abort();
    const e = await caught(p);
    expect(e).not.toBeInstanceOf(ApiError);
    expect(isAbortError(e)).toBe(true);
  });

  it("rejects malformed JSON in a 2xx response as bad_response", async () => {
    const h = setup(() => new Response("{oops", { status: 200, headers: { "content-type": "application/json" } }));
    const e = (await caught(h.client.get("/api/v1/x"))) as ApiError;
    expect(e.code).toBe("bad_response");
  });

  it("gives a generic Persian message for non-ApiErrors", () => {
    expect(errorMessage(new Error("x"))).toBe(API_MESSAGES.unknown);
  });
});

/* ─── refresh ────────────────────────────────────────────────────────────── */

describe("token refresh (web)", () => {
  it("single-flights concurrent 401s: exactly one refresh, each request retried once", async () => {
    let releaseRefresh: () => void = () => {};
    const gate = new Promise<void>((r) => (releaseRefresh = r));
    const h = setup(async (c) => {
      if (c.url === BASE + REFRESH_PATH) {
        await gate;
        return json(200, tokens("new"));
      }
      return c.headers.Authorization === "Bearer new" ? json(200, { url: c.url }) : expired();
    });
    h.client.setAccessToken("old");
    const a = h.client.get<{ url: string }>("/api/v1/a");
    const b = h.client.get<{ url: string }>("/api/v1/b");
    await tick(5);
    expect(h.refreshCalls()).toHaveLength(1);
    releaseRefresh();
    expect((await a).url).toBe(`${BASE}/api/v1/a`);
    expect((await b).url).toBe(`${BASE}/api/v1/b`);
    expect(h.refreshCalls()).toHaveLength(1);
    expect(h.client.getAccessToken()).toBe("new");
    // 2 originals + 1 refresh + 2 retries
    expect(h.calls).toHaveLength(5);
    const r = h.refreshCalls()[0]!;
    expect(r.method).toBe("POST");
    expect(r.credentials).toBe("include");
    expect(r.body).toBeUndefined();
    expect(r.headers["X-Client"]).toBeUndefined();
    expect(h.onSessionExpired).not.toHaveBeenCalled();
  });

  it("also refreshes on not_authenticated when a token was sent", async () => {
    const h = setup((c) => {
      if (c.url === BASE + REFRESH_PATH) return json(200, tokens("new"));
      return c.headers.Authorization === "Bearer new" ? json(200, { ok: true }) : envelope(401, "not_authenticated", "ابتدا وارد شوید.");
    });
    h.client.setAccessToken("old");
    expect(await h.client.get("/api/v1/x")).toEqual({ ok: true });
    expect(h.refreshCalls()).toHaveLength(1);
  });

  it("does not refresh without a token, for other 401 codes, or with auth: false", async () => {
    const h = setup((c) => {
      if (c.url === BASE + REFRESH_PATH) return json(200, tokens("new"));
      if (c.url.endsWith("/login")) return envelope(401, "invalid_credentials", "نام کاربری یا رمز عبور نادرست است.");
      return envelope(401, "not_authenticated", "ابتدا وارد شوید.");
    });
    expect(((await caught(h.client.get("/api/v1/x"))) as ApiError).code).toBe("not_authenticated");
    h.client.setAccessToken("tok");
    expect(((await caught(h.client.post("/api/v1/login", {}))) as ApiError).code).toBe("invalid_credentials");
    expect(((await caught(h.client.get("/api/v1/x", { auth: false }))) as ApiError).code).toBe("not_authenticated");
    expect(h.refreshCalls()).toHaveLength(0);
    expect(h.client.getAccessToken()).toBe("tok");
  });

  it("retries only once: a 401 after a successful refresh expires the session", async () => {
    const h = setup((c) => (c.url === BASE + REFRESH_PATH ? json(200, tokens("new")) : expired()));
    h.client.setAccessToken("old");
    const e = (await caught(h.client.get("/api/v1/x"))) as ApiError;
    expect(e.status).toBe(401);
    expect(h.refreshCalls()).toHaveLength(1);
    expect(h.calls).toHaveLength(3);
    expect(h.onSessionExpired).toHaveBeenCalledTimes(1);
    expect(h.client.getAccessToken()).toBeNull();
  });

  it("clears tokens and calls onSessionExpired once when refresh is refused", async () => {
    const h = setup((c) =>
      c.url === BASE + REFRESH_PATH ? envelope(401, "invalid_refresh", "نشست نامعتبر است.") : expired(),
    );
    h.client.setAccessToken("old");
    const [e1, e2] = await Promise.all([caught(h.client.get("/api/v1/a")), caught(h.client.get("/api/v1/b"))]);
    expect((e1 as ApiError).code).toBe("token_expired");
    expect((e2 as ApiError).code).toBe("token_expired");
    expect(h.refreshCalls()).toHaveLength(1);
    expect(h.onSessionExpired).toHaveBeenCalledTimes(1);
    expect(h.client.getAccessToken()).toBeNull();
  });

  it("keeps the session when refresh fails for a transient reason", async () => {
    const h = setup((c) => {
      if (c.url === BASE + REFRESH_PATH) throw new TypeError("offline");
      return expired();
    });
    h.client.setAccessToken("old");
    const e = (await caught(h.client.get("/api/v1/x"))) as ApiError;
    expect(e.code).toBe("network_error");
    expect(h.onSessionExpired).not.toHaveBeenCalled();
    expect(h.client.getAccessToken()).toBe("old");

    const h2 = setup((c) => (c.url === BASE + REFRESH_PATH ? envelope(503, "server_error", "سرور در دسترس نیست.") : expired()));
    h2.client.setAccessToken("old");
    expect(((await caught(h2.client.get("/api/v1/x"))) as ApiError).status).toBe(503);
    expect(h2.onSessionExpired).not.toHaveBeenCalled();
  });

  it("retries with a token refreshed meanwhile instead of refreshing again", async () => {
    const h = setup((c) => {
      if (c.url === BASE + REFRESH_PATH) return json(200, tokens("never"));
      if (c.headers.Authorization === "Bearer old") {
        h.client.setAccessToken("new"); // another request's refresh landed first
        return expired();
      }
      return json(200, { ok: true });
    });
    h.client.setAccessToken("old");
    expect(await h.client.get("/api/v1/x")).toEqual({ ok: true });
    expect(h.refreshCalls()).toHaveLength(0);
    expect(h.calls[1]!.headers.Authorization).toBe("Bearer new");
  });
});

describe("token refresh (native)", () => {
  it("sends the stored refresh token in the body with X-Client: native and stores the rotated one", async () => {
    const h = setup(
      (c) => {
        if (c.url === BASE + REFRESH_PATH) return json(200, tokens("new", "rt-2"));
        return c.headers.Authorization === "Bearer new" ? json(200, { ok: true }) : expired();
      },
      { clientKind: "native", secure: { [REFRESH_TOKEN_KEY]: "rt-1" } },
    );
    h.client.setAccessToken("old");
    expect(await h.client.get("/api/v1/x")).toEqual({ ok: true });
    const r = h.refreshCalls()[0]!;
    expect(r.headers["X-Client"]).toBe("native");
    expect(r.headers["Content-Type"]).toBe("application/json");
    expect(JSON.parse(r.body!)).toEqual({ refresh_token: "rt-1" });
    expect(r.credentials).toBe("omit");
    expect(await h.secureStorage.get(REFRESH_TOKEN_KEY)).toBe("rt-2");
  });

  it("expires without a request when no refresh token is stored", async () => {
    const h = setup(() => expired(), { clientKind: "native" });
    h.client.setAccessToken("old");
    await caught(h.client.get("/api/v1/x"));
    expect(h.refreshCalls()).toHaveLength(0);
    expect(h.onSessionExpired).toHaveBeenCalledTimes(1);
  });

  it("removes the stored refresh token when refresh is refused", async () => {
    const h = setup((c) => (c.url === BASE + REFRESH_PATH ? envelope(401, "invalid_refresh", "x") : expired()), {
      clientKind: "native",
      secure: { [REFRESH_TOKEN_KEY]: "rt-1" },
    });
    h.client.setAccessToken("old");
    await caught(h.client.get("/api/v1/x"));
    await tick();
    expect(await h.secureStorage.get(REFRESH_TOKEN_KEY)).toBeNull();
    expect(h.onSessionExpired).toHaveBeenCalledTimes(1);
  });
});

/* ─── session lifecycle ──────────────────────────────────────────────────── */

describe("session lifecycle", () => {
  it("setTokens stores the refresh token only on native", async () => {
    const web = setup(() => json(200, {}));
    await web.client.setTokens(tokens("a", "rt"));
    expect(web.client.getAccessToken()).toBe("a");
    expect(await web.secureStorage.get(REFRESH_TOKEN_KEY)).toBeNull();

    const nat = setup(() => json(200, {}), { clientKind: "native" });
    await nat.client.setTokens(tokens("a", "rt"));
    expect(await nat.secureStorage.get(REFRESH_TOKEN_KEY)).toBe("rt");
    await nat.client.clearTokens();
    expect(nat.client.getAccessToken()).toBeNull();
    expect(await nat.secureStorage.get(REFRESH_TOKEN_KEY)).toBeNull();
  });

  it("restoreSession returns tokens, or null without calling onSessionExpired", async () => {
    const h = setup(() => json(200, tokens("restored")));
    expect((await h.client.restoreSession())?.subject_id).toBe(7);
    expect(h.client.getAccessToken()).toBe("restored");

    const anon = setup(() => envelope(401, "invalid_refresh", "x"));
    expect(await anon.client.restoreSession()).toBeNull();
    expect(anon.onSessionExpired).not.toHaveBeenCalled();

    const offline = setup(() => {
      throw new TypeError("offline");
    });
    expect(((await caught(offline.client.restoreSession())) as ApiError).code).toBe("network_error");

    const nat = setup(() => json(200, tokens("x")), { clientKind: "native" });
    expect(await nat.client.restoreSession()).toBeNull();
    expect(nat.calls).toHaveLength(0);
  });

  it("logout revokes server-side and clears locally, even offline", async () => {
    const h = setup(() => new Response(null, { status: 204 }), { clientKind: "native", secure: { [REFRESH_TOKEN_KEY]: "rt" } });
    h.client.setAccessToken("a");
    await h.client.logout();
    expect(h.calls[0]!.url).toBe(`${BASE}/api/v1/auth/logout`);
    expect(JSON.parse(h.calls[0]!.body!)).toEqual({ refresh_token: "rt" });
    expect(h.client.getAccessToken()).toBeNull();
    expect(await h.secureStorage.get(REFRESH_TOKEN_KEY)).toBeNull();

    const off = setup(() => {
      throw new TypeError("offline");
    });
    off.client.setAccessToken("a");
    await off.client.logout();
    expect(off.client.getAccessToken()).toBeNull();
    expect(off.onSessionExpired).not.toHaveBeenCalled();
  });
});

/* ─── upload ─────────────────────────────────────────────────────────────── */

describe("upload", () => {
  it("delegates to platform.upload with auth headers, fields and progress", async () => {
    const h = setup(() => json(200, {}));
    h.client.setAccessToken("tok");
    h.setUpload(async (req) => {
      req.onProgress?.({ loaded: 50, total: 100, fraction: 0.5 });
      return { status: 201, body: JSON.stringify({ id: "f1" }) };
    });
    const progress = vi.fn();
    const file = new Blob(["abc"], { type: "image/jpeg" });
    const out = await h.client.upload<{ id: string }>("/api/v1/app/files", file, { purpose: "meter_photo", n: 3 }, progress);
    expect(out).toEqual({ id: "f1" });
    const req = h.uploads[0]!;
    expect(req.url).toBe(`${BASE}/api/v1/app/files`);
    expect(req.method).toBe("POST");
    expect(req.fileField).toBe("file");
    expect(req.file).toBe(file);
    expect(req.fields).toEqual({ purpose: "meter_photo", n: "3" });
    expect(req.headers.Authorization).toBe("Bearer tok");
    expect(req.headers["X-Request-Id"]).toMatch(/^rid-/);
    expect(req.headers["Content-Type"]).toBeUndefined();
    expect(req.withCredentials).toBe(true);
    expect(progress).toHaveBeenCalledWith({ loaded: 50, total: 100, fraction: 0.5 });
  });

  it("maps upload errors and refreshes on 401", async () => {
    const h = setup(() => json(200, tokens("new")));
    h.client.setAccessToken("old");
    h.setUpload(async (req) =>
      req.headers.Authorization === "Bearer new"
        ? { status: 413, body: JSON.stringify({ error: { code: "file_too_large", message: "حجم فایل زیاد است.", details: {} } }) }
        : { status: 401, body: JSON.stringify({ error: { code: "token_expired", message: "x", details: {} } }) },
    );
    const e = (await caught(h.client.upload("/api/v1/app/files", new Blob(["x"])))) as ApiError;
    expect(e.code).toBe("file_too_large");
    expect(e.message).toBe("حجم فایل زیاد است.");
    expect(h.refreshCalls()).toHaveLength(1);
    expect(h.uploads).toHaveLength(2);
  });

  it("maps a rejected platform upload to network_error and honours the upload timeout", async () => {
    const h = setup(() => json(200, {}), { uploadTimeoutMs: 15 });
    h.setUpload(async () => {
      throw new TypeError("Network request failed");
    });
    expect(((await caught(h.client.upload("/f", new Blob(["x"])))) as ApiError).code).toBe("network_error");
    h.setUpload(
      (req) =>
        new Promise((_r, rej) => {
          req.signal.addEventListener("abort", () => rej(new DOMException("aborted", "AbortError")));
        }),
    );
    expect(((await caught(h.client.upload("/f", new Blob(["x"])))) as ApiError).code).toBe("timeout");
  });
});
