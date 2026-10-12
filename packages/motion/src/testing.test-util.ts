/* Deterministic frame source for tests: captures rAF callbacks and
   lets the test fire frames by hand, so "the loop sleeps" can be
   asserted as "no callback is pending". */

import { vi } from "vitest";

export type FakeRaf = {
  /** Callbacks scheduled and not yet fired or cancelled. */
  pending: () => number;
  /** Total requestAnimationFrame calls since install. */
  calls: () => number;
  /** Fire every pending callback once, `ms` after the previous frame. */
  frame: (ms?: number) => void;
  /** Fire frames until nothing is pending; returns frames fired. */
  run: (maxFrames?: number) => number;
};

export function installFakeRaf(): FakeRaf {
  let id = 0;
  let t = 1000;
  let calls = 0;
  const queue = new Map<number, (now: number) => void>();
  vi.stubGlobal("requestAnimationFrame", (cb: (now: number) => void) => {
    calls++;
    queue.set(++id, cb);
    return id;
  });
  vi.stubGlobal("cancelAnimationFrame", (handle: number) => {
    queue.delete(handle);
  });
  const api: FakeRaf = {
    pending: () => queue.size,
    calls: () => calls,
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
