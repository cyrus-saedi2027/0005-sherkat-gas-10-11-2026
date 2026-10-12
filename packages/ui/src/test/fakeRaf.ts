/* Deterministic frames for component tests: captures rAF callbacks so a
   test can step springs by hand (and assert that nothing is pending). */

import { vi } from "vitest";
import { resetTicker } from "@gazyar/motion";

export type FakeRaf = {
  pending: () => number;
  /** Fire every pending callback once, `ms` after the previous frame. */
  frame: (ms?: number) => void;
  /** Fire frames until nothing is pending; returns frames fired. */
  run: (maxFrames?: number) => number;
};

export function installFakeRaf(): FakeRaf {
  resetTicker();
  let id = 0;
  let t = 1000;
  const queue = new Map<number, FrameRequestCallback>();
  vi.stubGlobal("requestAnimationFrame", (cb: FrameRequestCallback) => {
    queue.set(++id, cb);
    return id;
  });
  vi.stubGlobal("cancelAnimationFrame", (handle: number) => {
    queue.delete(handle);
  });
  const api: FakeRaf = {
    pending: () => queue.size,
    frame(ms = 1000 / 60) {
      t += ms;
      const cbs = Array.from(queue.values());
      queue.clear();
      for (const cb of cbs) cb(t);
    },
    run(maxFrames = 2000) {
      let n = 0;
      while (queue.size && n < maxFrames) {
        api.frame();
        n++;
      }
      return n;
    },
  };
  return api;
}

/** Install a matchMedia stub; returns a setter that fires change events. */
export function installMatchMedia(initial: Record<string, boolean> = {}) {
  const state = { ...initial };
  const lists = new Map<string, Set<(e: MediaQueryListEvent) => void>>();
  vi.stubGlobal("matchMedia", (query: string) => {
    const set = lists.get(query) ?? new Set();
    lists.set(query, set);
    return {
      get matches() {
        return !!state[query];
      },
      media: query,
      onchange: null,
      addEventListener: (_: "change", fn: (e: MediaQueryListEvent) => void) => set.add(fn),
      removeEventListener: (_: "change", fn: (e: MediaQueryListEvent) => void) => set.delete(fn),
      addListener: (fn: (e: MediaQueryListEvent) => void) => set.add(fn),
      removeListener: (fn: (e: MediaQueryListEvent) => void) => set.delete(fn),
      dispatchEvent: () => true,
    } as unknown as MediaQueryList;
  });
  return {
    set(query: string, matches: boolean) {
      state[query] = matches;
      for (const fn of Array.from(lists.get(query) ?? [])) fn({ matches, media: query } as MediaQueryListEvent);
    },
    listeners: (query: string) => lists.get(query)?.size ?? 0,
  };
}
