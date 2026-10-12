import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Spring } from "./spring";
import { MOTION } from "./presets";
import { isTickerAwake, join, leave, liveCount, MAX_DT, resetTicker, type Tickable } from "./ticker";
import { installFakeRaf, type FakeRaf } from "./testing.test-util";

let raf: FakeRaf;

beforeEach(() => {
  resetTicker();
  raf = installFakeRaf();
});

afterEach(() => {
  resetTicker();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("ticker", () => {
  it("sleeps when idle: no frame is scheduled once everything settles", () => {
    expect(isTickerAwake()).toBe(false);
    const s = new Spring(0, MOTION.thumb);
    s.springTo(1);
    expect(isTickerAwake()).toBe(true);
    expect(raf.pending()).toBe(1);
    raf.run();
    expect(isTickerAwake()).toBe(false);
    expect(raf.pending()).toBe(0);
    const callsAtRest = raf.calls();
    raf.frame();
    raf.frame();
    expect(raf.calls()).toBe(callsAtRest);
  });

  it("runs every animation on one shared frame", () => {
    const springs = [0, 1, 2, 3].map(() => new Spring(0, MOTION.thumb));
    for (const s of springs) s.springTo(1);
    expect(raf.pending()).toBe(1);
    raf.frame();
    expect(raf.pending()).toBe(1);
    expect(liveCount()).toBe(4);
  });

  it("clamps dt to 1/30s after a long frame and starts each wake at 1/60", () => {
    const dts: number[] = [];
    const t: Tickable = {
      step: (dt) => {
        dts.push(dt);
        return dts.length < 3;
      },
    };
    join(t);
    raf.frame(16);
    raf.frame(500); // a GC pause
    raf.frame(8);
    expect(dts[0]).toBeCloseTo(1 / 60, 6);
    expect(dts[1]).toBeCloseTo(MAX_DT, 6);
    expect(dts[2]).toBeCloseTo(0.008, 6);
  });

  it("a leave+join inside one frame does not schedule a second loop", () => {
    const other: Tickable = { step: () => true };
    let n = 0;
    const juggler: Tickable = {
      step: () => {
        leave(other);
        leave(juggler);
        join(other);
        return ++n < 3;
      },
    };
    join(other);
    join(juggler);
    raf.frame();
    expect(raf.pending()).toBe(1);
    raf.frame();
    expect(raf.pending()).toBe(1);
  });

  it("a tickable removed earlier in the same frame is not stepped", () => {
    const b: Tickable = { step: vi.fn(() => true) };
    const a: Tickable = {
      step: () => {
        leave(b);
        return false;
      },
    };
    join(a);
    join(b);
    raf.frame();
    expect(b.step).not.toHaveBeenCalled();
    expect(isTickerAwake()).toBe(false);
  });

  it("drops a throwing tickable but keeps the others animating", () => {
    const errors: unknown[] = [];
    vi.stubGlobal("queueMicrotask", (fn: () => void) => {
      try {
        fn();
      } catch (e) {
        errors.push(e);
      }
    });
    const bad: Tickable = {
      step: () => {
        throw new Error("boom");
      },
    };
    const s = new Spring(0, MOTION.thumb);
    join(bad);
    s.springTo(1);
    raf.run();
    expect(errors).toHaveLength(1);
    expect(s.x).toBe(1);
  });

  it("falls back to a timer where requestAnimationFrame does not exist", () => {
    vi.unstubAllGlobals();
    vi.useFakeTimers();
    const g = globalThis as { requestAnimationFrame?: unknown };
    expect(g.requestAnimationFrame).toBeUndefined();
    const s = new Spring(0, MOTION.thumb);
    s.springTo(1);
    vi.advanceTimersByTime(3000);
    expect(s.x).toBe(1);
    expect(isTickerAwake()).toBe(false);
  });
});
