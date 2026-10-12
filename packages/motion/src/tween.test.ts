import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { EASING, tween } from "./tween";
import { setReducedMotion } from "./reduced";
import { isTickerAwake, resetTicker } from "./ticker";
import { installFakeRaf, type FakeRaf } from "./testing.test-util";

let raf: FakeRaf;

beforeEach(() => {
  resetTicker();
  raf = installFakeRaf();
});

afterEach(() => {
  setReducedMotion(false);
  resetTicker();
  vi.unstubAllGlobals();
});

describe("EASING", () => {
  it("every curve starts at 0 and ends at 1", () => {
    for (const [name, ease] of Object.entries(EASING)) {
      expect(ease(0), name).toBeCloseTo(0, 9);
      expect(ease(1), name).toBeCloseTo(1, 9);
    }
  });

  it("out-curves are ahead of linear at the midpoint, outBack overshoots", () => {
    expect(EASING.outCubic(0.5)).toBeGreaterThan(0.5);
    expect(EASING.outQuart(0.5)).toBeGreaterThan(EASING.outCubic(0.5));
    expect(EASING.inOutCubic(0.5)).toBeCloseTo(0.5, 9);
    const peak = Math.max(...Array.from({ length: 101 }, (_, i) => EASING.outBack(i / 100)));
    expect(peak).toBeGreaterThan(1.05);
  });
});

describe("tween", () => {
  it("runs on the shared ticker, lands on `to`, fires onDone once, then sleeps", () => {
    const values: number[] = [];
    const onDone = vi.fn();
    tween({ from: 0, to: 100, duration: 300, onUpdate: (v) => values.push(v), onDone });
    expect(values[0]).toBe(0);
    const frames = raf.run();
    expect(frames).toBeGreaterThanOrEqual(17); // 300ms at 60fps ≈ 18 frames
    expect(frames).toBeLessThanOrEqual(20);
    expect(values[values.length - 1]).toBe(100);
    expect(onDone).toHaveBeenCalledTimes(1);
    expect(isTickerAwake()).toBe(false);
    // monotonic for outCubic
    for (let i = 1; i < values.length; i++) expect(values[i]!).toBeGreaterThanOrEqual(values[i - 1]!);
  });

  it("holds `from` during the delay", () => {
    const values: number[] = [];
    tween({ from: 5, to: 10, duration: 100, delay: 100, onUpdate: (v) => values.push(v) });
    raf.frame();
    raf.frame();
    raf.frame();
    expect(values.every((v) => v === 5)).toBe(true);
    raf.run();
    expect(values[values.length - 1]).toBe(10);
  });

  it("stop() halts without onDone", () => {
    const onDone = vi.fn();
    const t = tween({ from: 0, to: 1, duration: 500, onUpdate: () => {}, onDone });
    raf.frame();
    t.stop();
    raf.run();
    expect(onDone).not.toHaveBeenCalled();
    expect(isTickerAwake()).toBe(false);
  });

  it("under reduced motion jumps to the end and still calls onDone", () => {
    setReducedMotion(true);
    const values: number[] = [];
    const onDone = vi.fn();
    tween({ from: 0, to: 42, duration: 800, onUpdate: (v) => values.push(v), onDone });
    expect(values).toEqual([42]);
    expect(onDone).toHaveBeenCalledTimes(1);
    expect(raf.calls()).toBe(0);
  });
});
