import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Spring, dampingRatio } from "./spring";
import { MOTION } from "./presets";
import { setReducedMotion } from "./reduced";
import { isTickerAwake, liveCount, resetTicker } from "./ticker";
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

describe("Spring", () => {
  it("settles exactly on its target and leaves the loop", () => {
    const s = new Spring(0, MOTION.sheet);
    s.springTo(1);
    expect(s.isMoving).toBe(true);
    const frames = raf.run();
    expect(frames).toBeGreaterThan(5);
    expect(s.x).toBe(1);
    expect(s.v).toBe(0);
    expect(s.isMoving).toBe(false);
    expect(liveCount()).toBe(0);
  });

  it("settles in roughly the time its damping ratio predicts", () => {
    const s = new Spring(0, MOTION.sheet);
    s.springTo(1);
    const frames = raf.run();
    // ζ≈0.8, ω≈13.8 → ~0.36s to 2%; precision 0.002 takes a little longer.
    expect(frames / 60).toBeGreaterThan(0.25);
    expect(frames / 60).toBeLessThan(0.9);
  });

  it("fires onRest exactly once", () => {
    const s = new Spring(0, MOTION.thumb);
    const onRest = vi.fn();
    s.springTo(1, 0, onRest);
    raf.run();
    raf.frame();
    raf.frame();
    expect(onRest).toHaveBeenCalledTimes(1);
  });

  it("retargeting before rest replaces the pending onRest", () => {
    const s = new Spring(0, MOTION.thumb);
    const first = vi.fn();
    const second = vi.fn();
    s.springTo(1, 0, first);
    raf.frame();
    raf.frame();
    s.springTo(0, s.v, second);
    raf.run();
    expect(first).not.toHaveBeenCalled();
    expect(second).toHaveBeenCalledTimes(1);
    expect(s.x).toBe(0);
  });

  it("emits the current value on subscribe and every step", () => {
    const s = new Spring(0.25, MOTION.thumb);
    const seen: number[] = [];
    s.subscribe((x) => seen.push(x));
    expect(seen).toEqual([0.25]);
    s.springTo(1);
    raf.run();
    expect(seen.length).toBeGreaterThan(3);
    expect(seen[seen.length - 1]).toBe(1);
  });

  it("an underdamped preset overshoots, a critically damped one never does", () => {
    const pop = new Spring(0, MOTION.pop);
    let popMax = 0;
    pop.subscribe((x) => (popMax = Math.max(popMax, x)));
    pop.springTo(1);
    raf.run();
    expect(popMax).toBeGreaterThan(1.05);

    const count = new Spring(0, MOTION.count);
    let countMax = 0;
    count.subscribe((x) => (countMax = Math.max(countMax, x)));
    count.springTo(1000);
    raf.run();
    expect(countMax).toBeLessThanOrEqual(1000);
    expect(count.x).toBe(1000);
  });

  it("set() holds the value: no stepping, no loop, until released", () => {
    const s = new Spring(0, MOTION.sheet);
    const onRest = vi.fn();
    s.springTo(1, 0, onRest);
    raf.frame();
    s.set(0.3);
    expect(s.isHeld).toBe(true);
    expect(liveCount()).toBe(0);
    raf.run();
    raf.frame();
    expect(s.x).toBe(0.3);
    expect(s.v).toBe(0);
    // The interrupted transition's onRest must not fire later.
    expect(onRest).not.toHaveBeenCalled();
    expect(s.step(1 / 60)).toBe(false);

    // Release with a flick velocity: it continues from the held value.
    s.springTo(0, -2);
    expect(s.isHeld).toBe(false);
    raf.frame();
    expect(s.x).toBeLessThan(0.3);
    raf.run();
    expect(s.x).toBe(0);
  });

  it("an onRest that chains another springTo keeps the spring in the loop", () => {
    const s = new Spring(0, MOTION.thumb);
    const done = vi.fn();
    s.springTo(1, 0, () => s.springTo(0, 0, done));
    raf.run();
    expect(done).toHaveBeenCalledTimes(1);
    expect(s.x).toBe(0);
    expect(isTickerAwake()).toBe(false);
  });

  it("dispose() leaves the loop and drops subscribers", () => {
    const s = new Spring(0, MOTION.thumb);
    const sub = vi.fn();
    s.subscribe(sub);
    s.springTo(1);
    s.dispose();
    raf.run();
    expect(sub).toHaveBeenCalledTimes(1); // only the immediate subscribe call
    expect(liveCount()).toBe(0);
  });

  it("dampingRatio matches the textbook formula", () => {
    expect(dampingRatio({ stiffness: 100, damping: 20 })).toBeCloseTo(1, 6);
    expect(dampingRatio({ stiffness: 100, damping: 10, mass: 4 })).toBeCloseTo(0.25, 6);
  });
});

describe("Spring under reduced motion", () => {
  it("jumps to the target synchronously and still fires onRest once", () => {
    setReducedMotion(true);
    const s = new Spring(0, MOTION.sheet);
    const seen: number[] = [];
    s.subscribe((x) => seen.push(x));
    const onRest = vi.fn();
    s.springTo(1, 3, onRest);
    expect(s.x).toBe(1);
    expect(s.v).toBe(0);
    expect(onRest).toHaveBeenCalledTimes(1);
    expect(seen).toEqual([0, 1]);
    // Nothing was scheduled: reduced motion costs no frames at all.
    expect(raf.calls()).toBe(0);
    expect(isTickerAwake()).toBe(false);
  });

  it("finishes an in-flight animation on the next frame when switched on", () => {
    const s = new Spring(0, MOTION.sheet);
    const onRest = vi.fn();
    s.springTo(1, 0, onRest);
    raf.frame();
    expect(s.x).toBeGreaterThan(0);
    expect(s.x).toBeLessThan(1);
    setReducedMotion(true);
    raf.frame();
    expect(s.x).toBe(1);
    expect(onRest).toHaveBeenCalledTimes(1);
    expect(raf.pending()).toBe(0);
  });
});
