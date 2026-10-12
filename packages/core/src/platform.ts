/* Platform services injected into core (ARCHITECTURE §2).
 *
 * Core must run unchanged in a browser and in React Native, so everything that
 * differs between them — persistent storage, the keystore, file upload with
 * progress, haptics, the device id — goes through this interface. The browser
 * implementation lives in platform.web.ts (the only core file allowed to touch
 * window/document/localStorage); a future apps/mobile supplies its own. */

/** Async key/value store. Async because AsyncStorage / SecureStore are. */
export interface KeyValueStore {
  get(key: string): Promise<string | null>;
  set(key: string, value: string): Promise<void>;
  remove(key: string): Promise<void>;
}

export type HapticKind = "selection" | "light" | "medium" | "heavy" | "success" | "warning" | "error";

/** A file as React Native's FormData takes it (expo-image-picker result etc.). */
export interface NativeFileRef {
  uri: string;
  name: string;
  type: string;
}

/** Web passes a Blob/File; native passes a NativeFileRef. Core never reads the
 *  bytes itself — it only hands the value to Platform.upload. */
export type UploadFile = Blob | NativeFileRef;

export interface UploadProgress {
  loaded: number;
  /** 0 when the platform cannot tell (no Content-Length). */
  total: number;
  /** 0..1, or null when total is unknown. */
  fraction: number | null;
}

export interface UploadRequest {
  /** Absolute URL (baseUrl already applied). */
  url: string;
  method: "POST" | "PUT";
  /** Never contains Content-Type: the multipart boundary must be set by the
   *  platform's FormData encoder, and a hand-written header would lack it. */
  headers: Record<string, string>;
  /** Multipart field name of the file part. */
  fileField: string;
  file: UploadFile;
  /** Extra multipart text fields. */
  fields: Record<string, string>;
  /** Send cookies cross-origin (web refresh cookie lives on the API origin). */
  withCredentials: boolean;
  /** The implementation must reject (any error) once this aborts. */
  signal: AbortSignal;
  onProgress?: (p: UploadProgress) => void;
}

/** Raw response; the API client parses the body and maps errors. A non-2xx
 *  status must RESOLVE, not reject — rejection means the network failed. */
export interface UploadResponse {
  status: number;
  body: string;
}

export interface Platform {
  /** Bound fetch. (An unbound window.fetch throws "Illegal invocation".) */
  fetch: typeof fetch;
  /** Non-sensitive persistent values: device id, UI preferences. */
  storage: KeyValueStore;
  /** Secrets: the native refresh token. Keystore on native; memory-only on web
   *  (the web refresh token is an httpOnly cookie JS never sees). */
  secureStorage: KeyValueStore;
  /** Unique id for X-Request-Id and similar correlation ids (≤ 64 chars). */
  randomId(): string;
  /** Stable per-install id, generated once and persisted (see createDeviceIdGetter). */
  deviceId(): Promise<string>;
  upload(req: UploadRequest): Promise<UploadResponse>;
  /** Fire-and-forget; a no-op where unsupported. */
  haptic(kind: HapticKind): void;
}

/* ─── helpers shared by platform implementations ─────────────────────────── */

export const DEVICE_ID_KEY = "gazyar.device_id";

const hex = (bytes: Uint8Array) => Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");

/**
 * RFC 4122 v4 UUID. Uses crypto.randomUUID / getRandomValues when the engine
 * has them; Hermes without a polyfill has neither, and an app that cannot boot
 * over a correlation id is worse than a Math.random one (these ids are not
 * secrets — the server never trusts them for auth).
 */
export function uuidV4(): string {
  const c = (globalThis as { crypto?: Partial<Crypto> }).crypto;
  if (c && typeof c.randomUUID === "function") return c.randomUUID();
  const bytes = new Uint8Array(16);
  if (c && typeof c.getRandomValues === "function") c.getRandomValues(bytes);
  else for (let i = 0; i < 16; i++) bytes[i] = Math.floor(Math.random() * 256);
  bytes[6] = (bytes[6]! & 0x0f) | 0x40; // version 4
  bytes[8] = (bytes[8]! & 0x3f) | 0x80; // RFC 4122 variant
  const h = hex(bytes);
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
}

/** In-memory KeyValueStore: tests, SSR, and the web "secure" store. */
export function memoryStorage(initial: Record<string, string> = {}): KeyValueStore {
  const m = new Map(Object.entries(initial));
  return {
    get: async (k) => m.get(k) ?? null,
    set: async (k, v) => {
      m.set(k, v);
    },
    remove: async (k) => {
      m.delete(k);
    },
  };
}

const DEVICE_ID_RE = /^[A-Za-z0-9-]{8,64}$/;

/**
 * deviceId() implementation: read the persisted id, or generate and persist one.
 *
 * Single-flight: the first screen fires several requests at once, and without
 * the shared promise each would mint its own id — the server would then see
 * one install as several devices and trip the referral fraud signal
 * (fraud.max_accounts_per_device). A storage failure still yields a stable id
 * for this session rather than failing signup.
 */
export function createDeviceIdGetter(storage: KeyValueStore, randomId: () => string = uuidV4): () => Promise<string> {
  let pending: Promise<string> | null = null;
  const load = async (): Promise<string> => {
    let existing: string | null = null;
    try {
      existing = await storage.get(DEVICE_ID_KEY);
    } catch {
      existing = null;
    }
    // Server column is 64 chars; a corrupted value is replaced, not sent.
    if (existing && DEVICE_ID_RE.test(existing)) return existing;
    const id = randomId();
    try {
      await storage.set(DEVICE_ID_KEY, id);
    } catch {
      // Storage full / blocked: keep the in-memory id for this session.
    }
    return id;
  };
  return () => (pending ??= load());
}

/** Build a multipart body. RN's FormData accepts a NativeFileRef in place of a
 *  Blob; the cast is where the two platforms' typings disagree, not the runtime. */
export function buildFormData(file: UploadFile, fileField: string, fields: Record<string, string>): FormData {
  const fd = new FormData();
  for (const [k, v] of Object.entries(fields)) fd.append(k, v);
  if (typeof Blob !== "undefined" && file instanceof Blob) {
    const name = (file as Blob & { name?: unknown }).name;
    fd.append(fileField, file, typeof name === "string" && name ? name : "upload");
  } else {
    fd.append(fileField, file as unknown as Blob);
  }
  return fd;
}

/**
 * Upload over plain fetch + FormData — works on any platform, but reports
 * progress only as 0 → 1 (fetch has no upload progress events). Web uses XHR
 * instead (platform.web.ts); native may use this or a native uploader.
 */
export function uploadViaFetch(fetchImpl: typeof fetch): (req: UploadRequest) => Promise<UploadResponse> {
  return async (req) => {
    const size = typeof Blob !== "undefined" && req.file instanceof Blob ? req.file.size : 0;
    req.onProgress?.({ loaded: 0, total: size, fraction: 0 });
    const res = await fetchImpl(req.url, {
      method: req.method,
      headers: req.headers,
      body: buildFormData(req.file, req.fileField, req.fields),
      credentials: req.withCredentials ? "include" : "same-origin",
      signal: req.signal,
    });
    const body = await res.text();
    req.onProgress?.({ loaded: size, total: size, fraction: 1 });
    return { status: res.status, body };
  };
}
