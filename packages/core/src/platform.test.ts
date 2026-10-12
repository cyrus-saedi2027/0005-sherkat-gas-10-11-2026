import {
  buildFormData,
  createDeviceIdGetter,
  DEVICE_ID_KEY,
  memoryStorage,
  uploadViaFetch,
  uuidV4,
  type KeyValueStore,
} from "./platform";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

describe("uuidV4", () => {
  it("returns RFC 4122 v4 ids", () => {
    const ids = new Set(Array.from({ length: 200 }, uuidV4));
    expect(ids.size).toBe(200);
    for (const id of ids) expect(id).toMatch(UUID);
  });

  it("works without crypto (bare Hermes)", () => {
    vi.stubGlobal("crypto", undefined);
    try {
      expect(uuidV4()).toMatch(UUID);
    } finally {
      vi.unstubAllGlobals();
    }
  });
});

describe("memoryStorage", () => {
  it("gets, sets and removes", async () => {
    const s = memoryStorage({ a: "1" });
    expect(await s.get("a")).toBe("1");
    await s.set("b", "2");
    expect(await s.get("b")).toBe("2");
    await s.remove("a");
    expect(await s.get("a")).toBeNull();
  });
});

describe("createDeviceIdGetter", () => {
  it("generates once, persists, and reuses", async () => {
    const storage = memoryStorage();
    const ids = ["11111111-aaaa", "22222222-bbbb"];
    const get = createDeviceIdGetter(storage, () => ids.shift()!);
    const [a, b] = await Promise.all([get(), get()]);
    expect(a).toBe("11111111-aaaa");
    expect(b).toBe(a); // concurrent first calls share one id
    expect(await storage.get(DEVICE_ID_KEY)).toBe(a);
    // A new getter (next app launch) reads the persisted id.
    expect(await createDeviceIdGetter(storage, () => "33333333-cccc")()).toBe(a);
  });

  it("replaces a corrupted stored value", async () => {
    const storage = memoryStorage({ [DEVICE_ID_KEY]: "bad id!" });
    expect(await createDeviceIdGetter(storage, () => "44444444-dddd")()).toBe("44444444-dddd");
  });

  it("still returns a stable id when storage throws", async () => {
    const broken: KeyValueStore = {
      get: () => Promise.reject(new Error("blocked")),
      set: () => Promise.reject(new Error("quota")),
      remove: () => Promise.reject(new Error("blocked")),
    };
    const get = createDeviceIdGetter(broken, () => "55555555-eeee");
    expect(await get()).toBe("55555555-eeee");
    expect(await get()).toBe("55555555-eeee");
  });
});

describe("uploads over fetch", () => {
  it("builds multipart with fields and a named file", () => {
    const fd = buildFormData(new Blob(["abc"], { type: "image/png" }), "file", { purpose: "meter_photo" });
    expect(fd.get("purpose")).toBe("meter_photo");
    const f = fd.get("file");
    expect(f).toBeInstanceOf(Blob);
    expect((f as File).name).toBe("upload");
  });

  it("posts FormData and reports start/end progress", async () => {
    const seen: RequestInit[] = [];
    const fetchMock = (async (_url: RequestInfo | URL, init?: RequestInit) => {
      seen.push(init!);
      return new Response('{"id":"f"}', { status: 201 });
    }) as typeof fetch;
    const progress = vi.fn();
    const res = await uploadViaFetch(fetchMock)({
      url: "http://api.test/f",
      method: "POST",
      headers: { "X-Request-Id": "r" },
      fileField: "file",
      file: new Blob(["abcd"]),
      fields: { a: "1" },
      withCredentials: true,
      signal: new AbortController().signal,
      onProgress: progress,
    });
    expect(res).toEqual({ status: 201, body: '{"id":"f"}' });
    expect(seen[0]!.body).toBeInstanceOf(FormData);
    expect(seen[0]!.credentials).toBe("include");
    expect(progress).toHaveBeenNthCalledWith(1, { loaded: 0, total: 4, fraction: 0 });
    expect(progress).toHaveBeenLastCalledWith({ loaded: 4, total: 4, fraction: 1 });
  });
});
