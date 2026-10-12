/* ─────────────────────────────────────────────────────────────
 *  Gesture maths — velocity and resistance. Pure functions over
 *  numbers; the platform layer feeds pointer/touch positions in.
 * ───────────────────────────────────────────────────────────── */

import { now as clock } from "./ticker";

/**
 * Velocity is averaged over the trailing 90ms, not the last two
 * samples. Two samples are far too noisy: one jittery event at release
 * sends a sheet the wrong way. This is the single most common bug in
 * hand-written flick handling.
 */
export const VELOCITY_WINDOW_MS = 90;

/** Past a limit, movement is multiplied by this — resist, never clamp. */
export const RUBBER_K = 0.28;

type Sample = { p: number; t: number };

/** Tracks one axis. Positions in any unit; velocity in units per second. */
export class VelocityTracker {
  private samples: Sample[] = [];
  private readonly windowMs: number;

  constructor(windowMs: number = VELOCITY_WINDOW_MS) {
    this.windowMs = windowMs;
  }

  /** Record a position; `t` in ms (defaults to the engine clock). */
  add(position: number, t: number = clock()): void {
    this.samples.push({ p: position, t });
    // Keep only what the window can still use (+1 sample as the anchor
    // just outside it), so long drags do not grow the array.
    const cutoff = t - this.windowMs;
    let drop = 0;
    while (drop < this.samples.length - 2 && this.samples[drop + 1]!.t < cutoff) drop++;
    if (drop) this.samples.splice(0, drop);
  }

  /**
   * Units per second over the trailing window ending at the newest
   * sample. If the pointer has been still for longer than the window
   * when you ask (`at`, default now), the answer is 0: a finger that
   * stopped and then lifted is not a flick.
   */
  velocity(at?: number): number {
    const n = this.samples.length;
    if (n < 2) return 0;
    const newest = this.samples[n - 1]!;
    if (at !== undefined && at - newest.t > this.windowMs) return 0;

    const cutoff = newest.t - this.windowMs;
    let oldest = newest;
    for (let i = n - 2; i >= 0; i--) {
      const s = this.samples[i]!;
      if (s.t < cutoff) break;
      oldest = s;
    }
    // Only one sample inside the window: fall back to the anchor just
    // outside it rather than reporting a flick as zero.
    if (oldest === newest) oldest = this.samples[n - 2]!;
    const dt = newest.t - oldest.t;
    if (dt <= 0) return 0;
    return ((newest.p - oldest.p) / dt) * 1000;
  }

  reset(): void {
    this.samples = [];
  }
}

/**
 * Rubber-band a displacement: free within ±limit, beyond it every unit
 * of travel counts for `k`. The surface keeps responding but visibly
 * resists — clamping instead makes it feel dead at the edge.
 */
export function rubberband(dx: number, limit: number, k: number = RUBBER_K): number {
  const lim = Math.abs(limit);
  if (dx > lim) return lim + (dx - lim) * k;
  if (dx < -lim) return -lim + (dx + lim) * k;
  return dx;
}

/** Rubber-band a position against [min, max] (e.g. a sheet's 0..1). */
export function rubberClamp(x: number, min: number, max: number, k: number = RUBBER_K): number {
  if (x < min) return min - (min - x) * k;
  if (x > max) return max + (x - max) * k;
  return x;
}

/** Clamp helper shared by gesture code. */
export function clamp(x: number, min: number, max: number): number {
  return x < min ? min : x > max ? max : x;
}
