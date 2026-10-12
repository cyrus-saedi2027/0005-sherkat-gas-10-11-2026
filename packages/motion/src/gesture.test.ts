import { describe, expect, it } from "vitest";
import { RUBBER_K, VelocityTracker, clamp, rubberClamp, rubberband } from "./gesture";

describe("VelocityTracker", () => {
  it("averages over the trailing 90ms window, so one jittery sample does not flip a flick", () => {
    const vt = new VelocityTracker();
    // A steady drag at +1px/ms (1000px/s), sampled every 8ms…
    for (let t = 0; t <= 200; t += 8) vt.add(t, t);
    // …then a jittery last event 1ms later that moved *backwards* 4px.
    vt.add(196, 201);
    const windowed = vt.velocity();
    const twoSample = ((196 - 200) / (201 - 200)) * 1000; // what a two-sample tracker would say
    expect(twoSample).toBeLessThan(0);
    expect(windowed).toBeGreaterThan(800);
    expect(windowed).toBeLessThan(1100);
  });

  it("ignores samples older than the window", () => {
    const vt = new VelocityTracker(90);
    // Fast early movement, then slow movement over the last 90ms.
    vt.add(0, 0);
    vt.add(500, 50);
    for (let t = 100; t <= 300; t += 10) vt.add(500 + (t - 100) * 0.1, t);
    expect(vt.velocity()).toBeCloseTo(100, 0); // 0.1px/ms
  });

  it("reports 0 when the pointer was still for longer than the window before release", () => {
    const vt = new VelocityTracker();
    vt.add(0, 0);
    vt.add(80, 40);
    expect(vt.velocity(60)).toBeGreaterThan(0);
    expect(vt.velocity(400)).toBe(0);
  });

  it("needs two samples and resets cleanly", () => {
    const vt = new VelocityTracker();
    expect(vt.velocity()).toBe(0);
    vt.add(10, 0);
    expect(vt.velocity()).toBe(0);
    vt.add(20, 10);
    expect(vt.velocity()).toBeCloseTo(1000, 6);
    vt.reset();
    expect(vt.velocity()).toBe(0);
  });

  it("uses the anchor just outside the window when only one sample is inside", () => {
    const vt = new VelocityTracker(90);
    vt.add(0, 0);
    vt.add(100, 200); // sparse events on a slow device
    expect(vt.velocity()).toBeCloseTo(500, 6);
  });
});

describe("rubberband", () => {
  it("is free inside the limit", () => {
    expect(rubberband(30, 40)).toBe(30);
    expect(rubberband(-40, 40)).toBe(-40);
  });

  it("resists beyond the limit with k=0.28 by default (resist, never clamp)", () => {
    expect(RUBBER_K).toBe(0.28);
    expect(rubberband(140, 40)).toBeCloseTo(40 + 100 * 0.28, 9);
    expect(rubberband(-140, 40)).toBeCloseTo(-40 - 100 * 0.28, 9);
    // still responsive: more travel always means more displacement
    expect(rubberband(200, 40)).toBeGreaterThan(rubberband(199, 40));
  });

  it("accepts a custom k and a zero limit", () => {
    expect(rubberband(100, 0, 0.5)).toBe(50);
  });

  it("rubberClamp resists past either end of a range", () => {
    expect(rubberClamp(0.5, 0, 1)).toBe(0.5);
    expect(rubberClamp(-0.5, 0, 1)).toBeCloseTo(-0.14, 9);
    expect(rubberClamp(1.5, 0, 1)).toBeCloseTo(1.14, 9);
    expect(clamp(5, 0, 1)).toBe(1);
  });
});
