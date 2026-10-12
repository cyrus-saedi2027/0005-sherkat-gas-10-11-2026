import { ApiError } from "@gazyar/core";
import { createQueryClient, MAX_TRANSIENT_RETRIES, QUERY_STALE_TIME_MS, retryDelay, shouldRetry } from "./queryClient";

const err = (status: number, code = "x") => new ApiError({ status, code, message: "پیام" });

describe("shouldRetry", () => {
  it("never retries a 4xx", () => {
    for (const s of [400, 401, 403, 404, 409, 413, 422, 429]) expect(shouldRetry(0, err(s)), String(s)).toBe(false);
  });

  it("retries transport failures and 5xx at most twice", () => {
    for (const e of [err(0, "network_error"), err(0, "timeout"), err(500), err(502), err(503)]) {
      expect(shouldRetry(0, e)).toBe(true);
      expect(shouldRetry(1, e)).toBe(true);
      expect(shouldRetry(2, e)).toBe(false);
    }
    expect(MAX_TRANSIENT_RETRIES).toBe(2);
  });

  it("does not retry cancellations or non-API errors", () => {
    expect(shouldRetry(0, new DOMException("aborted", "AbortError"))).toBe(false);
    expect(shouldRetry(0, new TypeError("x is undefined"))).toBe(false);
    expect(shouldRetry(0, "boom")).toBe(false);
  });
});

describe("retryDelay", () => {
  it("backs off exponentially with a cap", () => {
    expect([0, 1, 2, 3, 4, 10].map(retryDelay)).toEqual([1000, 2000, 4000, 8000, 8000, 8000]);
  });
});

describe("createQueryClient", () => {
  it("applies the defaults", () => {
    const qc = createQueryClient();
    const d = qc.getDefaultOptions();
    expect(d.queries?.staleTime).toBe(QUERY_STALE_TIME_MS);
    expect(QUERY_STALE_TIME_MS).toBe(30_000);
    expect(d.queries?.refetchOnWindowFocus).toBe(false);
    expect(d.queries?.retry).toBe(shouldRetry);
    expect(d.mutations?.retry).toBe(false);
  });

  it("reports query errors once (no retry on 4xx) and skips silent ones", async () => {
    const onError = vi.fn();
    const qc = createQueryClient({ onError });
    const e403 = err(403, "forbidden");
    await expect(qc.fetchQuery({ queryKey: ["a"], queryFn: () => Promise.reject(e403), retry: shouldRetry })).rejects.toBe(e403);
    expect(onError).toHaveBeenCalledTimes(1);
    expect(onError).toHaveBeenCalledWith(e403, { kind: "query", meta: undefined });

    await expect(
      qc.fetchQuery({ queryKey: ["b"], queryFn: () => Promise.reject(e403), meta: { silentError: true } }),
    ).rejects.toBe(e403);
    expect(onError).toHaveBeenCalledTimes(1);
    qc.clear();
  });

  it("retries a 5xx query twice before failing", async () => {
    const qc = createQueryClient();
    const fn = vi.fn(() => Promise.reject(err(503)));
    await expect(qc.fetchQuery({ queryKey: ["c"], queryFn: fn, retry: shouldRetry, retryDelay: 0 })).rejects.toBeInstanceOf(ApiError);
    expect(fn).toHaveBeenCalledTimes(3);
    qc.clear();
  });

  it("reports mutation errors", async () => {
    const onError = vi.fn();
    const qc = createQueryClient({ onError });
    const e = err(422, "validation_error");
    const m = qc.getMutationCache().build(qc, { mutationFn: () => Promise.reject(e) });
    await expect(m.execute(undefined)).rejects.toBe(e);
    expect(onError).toHaveBeenCalledWith(e, { kind: "mutation", meta: undefined });
    qc.clear();
  });
});
