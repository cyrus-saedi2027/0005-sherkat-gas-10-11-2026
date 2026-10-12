import { hashKey, matchQuery, Query, QueryCache, QueryClient } from "@tanstack/react-query";
import { cleanParams, qk } from "./keys";

describe("cleanParams", () => {
  it("drops unset filters and sorts keys", () => {
    expect(cleanParams()).toEqual({});
    expect(cleanParams({ status: undefined, q: "", region: null, tags: [], page: 1 })).toEqual({ page: 1 });
    expect(Object.keys(cleanParams({ z: 1, a: 2, m: false }))).toEqual(["a", "m", "z"]);
    expect(cleanParams({ status: ["pending", "flagged"], zero: 0, no: false })).toEqual({
      no: false,
      status: ["pending", "flagged"],
      zero: 0,
    });
  });
});

describe("qk", () => {
  it("follows the [domain, kind, …] convention", () => {
    expect(qk.readings.all).toEqual(["readings"]);
    expect(qk.readings.lists()).toEqual(["readings", "list"]);
    expect(qk.readings.list({ status: "pending", page: 2 })).toEqual(["readings", "list", { page: 2, status: "pending" }]);
    expect(qk.readings.details()).toEqual(["readings", "detail"]);
    expect(qk.readings.detail(5)).toEqual(["readings", "detail", "5"]);
    expect(qk.readings.events(5)).toEqual(["readings", "detail", "5", "events"]);
    expect(qk.readings.period("1405-07")).toEqual(["readings", "period", "1405-07"]);
    expect(qk.points.balance()).toEqual(["points", "balance"]);
    expect(qk.points.balance(9)).toEqual(["points", "balance", "9"]);
    expect(qk.settings.detail("finance.free_cap_rial")).toEqual(["settings", "detail", "finance.free_cap_rial"]);
  });

  it("treats numeric and string ids as the same entity", () => {
    expect(hashKey(qk.cases.detail(12))).toBe(hashKey(qk.cases.detail("12")));
  });

  it("makes unset filters hash to the same cache entry", () => {
    expect(hashKey(qk.tickets.list({ status: undefined, q: "" }))).toBe(hashKey(qk.tickets.list()));
    expect(hashKey(qk.tickets.list({ b: 1, a: 2 }))).toBe(hashKey(qk.tickets.list({ a: 2, b: 1 })));
  });

  it("gives every domain a distinct root", () => {
    const roots = Object.values(qk).map((d) => d.all[0]);
    expect(new Set(roots).size).toBe(roots.length);
  });

  it("lets prefixes invalidate exactly the intended queries", () => {
    const client = new QueryClient({ queryCache: new QueryCache() });
    const keys = [
      qk.readings.list({ status: "pending" }),
      qk.readings.list({ status: "approved", page: 2 }),
      qk.readings.detail(5),
      qk.readings.events(5),
      qk.readings.detail(6),
      qk.cases.list(),
    ];
    for (const k of keys) client.setQueryData(k, 1);
    const queries = client.getQueryCache().getAll();
    const hit = (filterKey: readonly unknown[]) =>
      queries.filter((q: Query) => matchQuery({ queryKey: filterKey }, q)).map((q) => q.queryHash);

    expect(hit(qk.readings.lists())).toHaveLength(2);
    expect(hit(qk.readings.detail(5))).toEqual([hashKey(qk.readings.detail(5)), hashKey(qk.readings.events(5))]);
    expect(hit(qk.readings.all)).toHaveLength(5);
    expect(hit(qk.cases.all)).toHaveLength(1);
    client.clear();
  });
});
