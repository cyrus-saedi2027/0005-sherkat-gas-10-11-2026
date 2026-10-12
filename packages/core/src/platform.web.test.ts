// @vitest-environment jsdom
import { DEVICE_ID_KEY } from "./platform";
import { createWebPlatform } from "./platform.web";

/** Minimal XHR double: records what was sent and lets the test drive events. */
class FakeXhr {
  static last: FakeXhr | null = null;
  method = "";
  url = "";
  withCredentials = false;
  headers: Record<string, string> = {};
  body: unknown = null;
  status = 0;
  responseText = "";
  aborted = false;
  upload: { onprogress: ((e: { loaded: number; total: number; lengthComputable: boolean }) => void) | null } = { onprogress: null };
  onload: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onabort: (() => void) | null = null;
  constructor() {
    FakeXhr.last = this;
  }
  open(method: string, url: string) {
    this.method = method;
    this.url = url;
  }
  setRequestHeader(k: string, v: string) {
    this.headers[k] = v;
  }
  send(body: unknown) {
    this.body = body;
  }
  abort() {
    this.aborted = true;
    this.onabort?.();
  }
}

afterEach(() => {
  vi.unstubAllGlobals();
  window.localStorage.clear();
});

describe("createWebPlatform", () => {
  it("persists the device id in localStorage", async () => {
    const p = createWebPlatform();
    const id = await p.deviceId();
    expect(id).toMatch(/^[0-9a-f-]{36}$/);
    expect(window.localStorage.getItem(DEVICE_ID_KEY)).toBe(id);
    expect(await createWebPlatform().deviceId()).toBe(id);
  });

  it("falls back to memory when localStorage throws", async () => {
    const throwing = {
      getItem: () => {
        throw new Error("SecurityError");
      },
      setItem: () => {
        throw new Error("QuotaExceededError");
      },
      removeItem: () => {
        throw new Error("SecurityError");
      },
    };
    vi.spyOn(window, "localStorage", "get").mockReturnValue(throwing as unknown as Storage);
    const p = createWebPlatform();
    await p.storage.set("k", "v");
    expect(await p.storage.get("k")).toBe("v");
    await p.storage.remove("k");
    expect(await p.storage.get("k")).toBeNull();
    vi.restoreAllMocks();
  });

  it("keeps secureStorage in memory only", async () => {
    const p = createWebPlatform();
    await p.secureStorage.set("gazyar.refresh_token", "secret");
    expect(await p.secureStorage.get("gazyar.refresh_token")).toBe("secret");
    expect(Object.keys(window.localStorage)).not.toContain("gazyar.refresh_token");
  });

  it("uploads with XHR, reports progress and resolves non-2xx", async () => {
    vi.stubGlobal("XMLHttpRequest", FakeXhr);
    const p = createWebPlatform();
    const progress = vi.fn();
    const ctrl = new AbortController();
    const done = p.upload({
      url: "http://api.test/api/v1/app/files",
      method: "POST",
      headers: { Authorization: "Bearer t", "X-Request-Id": "r1" },
      fileField: "file",
      file: new Blob(["abc"], { type: "image/jpeg" }),
      fields: { purpose: "meter_photo" },
      withCredentials: true,
      signal: ctrl.signal,
      onProgress: progress,
    });
    const xhr = FakeXhr.last!;
    expect(xhr.method).toBe("POST");
    expect(xhr.withCredentials).toBe(true);
    expect(xhr.headers).toEqual({ Authorization: "Bearer t", "X-Request-Id": "r1" });
    expect((xhr.body as FormData).get("purpose")).toBe("meter_photo");
    xhr.upload.onprogress?.({ loaded: 30, total: 120, lengthComputable: true });
    xhr.upload.onprogress?.({ loaded: 5, total: 0, lengthComputable: false });
    expect(progress).toHaveBeenNthCalledWith(1, { loaded: 30, total: 120, fraction: 0.25 });
    expect(progress).toHaveBeenNthCalledWith(2, { loaded: 5, total: 0, fraction: null });
    xhr.status = 413;
    xhr.responseText = '{"error":{}}';
    xhr.onload?.();
    await expect(done).resolves.toEqual({ status: 413, body: '{"error":{}}' });
  });

  it("aborts the XHR when the signal fires and rejects on network errors", async () => {
    vi.stubGlobal("XMLHttpRequest", FakeXhr);
    const p = createWebPlatform();
    const base = {
      url: "http://api.test/f",
      method: "POST" as const,
      headers: {},
      fileField: "file",
      file: new Blob(["x"]),
      fields: {},
      withCredentials: false,
    };
    const ctrl = new AbortController();
    const aborted = p.upload({ ...base, signal: ctrl.signal });
    ctrl.abort();
    await expect(aborted).rejects.toMatchObject({ name: "AbortError" });
    expect(FakeXhr.last!.aborted).toBe(true);

    const failed = p.upload({ ...base, signal: new AbortController().signal });
    FakeXhr.last!.onerror?.();
    await expect(failed).rejects.toBeInstanceOf(TypeError);
  });

  it("binds fetch and never throws from haptics", () => {
    const p = createWebPlatform();
    expect(typeof p.fetch).toBe("function");
    expect(() => p.haptic("success")).not.toThrow();
  });
});
