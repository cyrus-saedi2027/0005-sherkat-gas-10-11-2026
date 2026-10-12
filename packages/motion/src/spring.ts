/* ─────────────────────────────────────────────────────────────
 *  Spring — no React, no DOM.
 *
 *  Subscribers receive (x, v) and write wherever they like (a DOM
 *  style, an Animated value, a canvas). Nothing here goes through
 *  React state, so a 60fps animation costs zero re-renders.
 *
 *  Integration is semi-implicit Euler — what most reference spring
 *  implementations use, so stiffness/damping numbers carry their feel
 *  across from other systems.
 * ───────────────────────────────────────────────────────────── */

import { isReducedMotion } from "./reduced";
import { join, leave, type Tickable } from "./ticker";

export type SpringConfig = {
  /** k — pull toward the target. Default 300. */
  stiffness?: number;
  /** c — resistance to velocity. Default 30. */
  damping?: number;
  /** m — default 1. */
  mass?: number;
  /**
   * Settle threshold, in the units of the value the spring carries:
   * ~0.002 for a 0..1 progress, ~0.25 for pixels. Too large and the
   * spring "teleports" the last stretch (see presets.ts).
   */
  precision?: number;
};

export type SpringListener = (x: number, v: number) => void;

export class Spring implements Tickable {
  /** Current position. Read freely; write only through set()/springTo(). */
  x: number;
  /** Current velocity, units per second. */
  v = 0;
  target: number;

  private k = 300;
  private c = 30;
  private m = 1;
  private eps = 0.01;
  private subs = new Set<SpringListener>();
  private onRest: (() => void) | null = null;
  /** A finger owns the value: step() is a no-op until springTo(). */
  private held = false;
  /** In the ticker (or about to be). Lets an onRest re-arm the spring. */
  private active = false;

  constructor(initial: number, cfg: SpringConfig = {}) {
    this.x = initial;
    this.target = initial;
    this.configure(cfg);
  }

  /** Change physics live; takes effect on the next step. */
  configure(cfg: SpringConfig): void {
    this.k = cfg.stiffness ?? this.k;
    this.c = cfg.damping ?? this.c;
    this.m = cfg.mass ?? this.m;
    this.eps = cfg.precision ?? this.eps;
  }

  /** True while animating toward a target. */
  get isMoving(): boolean {
    return this.active;
  }

  /** True between set() and the next springTo(). */
  get isHeld(): boolean {
    return this.held;
  }

  /** Subscribe; the listener is called immediately with the current value. */
  subscribe(fn: SpringListener): () => void {
    this.subs.add(fn);
    fn(this.x, this.v);
    return () => {
      this.subs.delete(fn);
    };
  }

  private emit(): void {
    for (const s of this.subs) s(this.x, this.v);
  }

  /**
   * Hard-set the value and hold it — this is what makes a surface feel
   * grabbable. While a finger is down the spring is not animating, it
   * *is* the finger: no physics fights the input. Any pending onRest is
   * dropped (the transition it belonged to was interrupted).
   */
  set(x: number): void {
    this.held = true;
    this.active = false;
    this.onRest = null;
    leave(this);
    this.x = x;
    this.v = 0;
    this.target = x;
    this.emit();
  }

  /**
   * Release toward `target`, optionally with the finger's exit velocity
   * so a flick continues naturally. `onRest` fires exactly once when the
   * spring settles — and also when reduced motion makes it jump, because
   * callers unmount things in onRest and skipping it would leak them.
   * Retargeting before rest replaces (does not fire) the old onRest.
   */
  springTo(target: number, v0 = 0, onRest?: () => void): void {
    this.held = false;
    this.target = target;
    this.v = v0;
    this.onRest = onRest ?? null;

    if (isReducedMotion()) {
      leave(this); // it may have been mid-flight before this call
      this.settle();
      return;
    }
    this.active = true;
    join(this);
  }

  /** Stop where it is, drop velocity and the pending onRest. */
  stop(): void {
    this.active = false;
    this.onRest = null;
    leave(this);
    this.v = 0;
  }

  step(dt: number): boolean {
    if (this.held || !this.active) return false;

    // Reduced motion switched on mid-flight: finish now rather than
    // animating out the rest of a transition the user asked not to see.
    if (isReducedMotion()) return this.settle();

    const a = (-this.k * (this.x - this.target) - this.c * this.v) / this.m;
    this.v += a * dt;
    this.x += this.v * dt;

    if (Math.abs(this.x - this.target) < this.eps && Math.abs(this.v) < this.eps * 4) {
      return this.settle();
    }
    this.emit();
    return true;
  }

  /**
   * Snap to target, emit, fire onRest once. Returns whether the spring
   * should stay in the loop: an onRest that calls springTo() again (a
   * chained animation) re-arms it, and the ticker must not then drop it.
   */
  private settle(): boolean {
    this.active = false;
    this.x = this.target;
    this.v = 0;
    this.emit();
    const cb = this.onRest;
    this.onRest = null;
    cb?.();
    return this.active;
  }

  /** Leave the loop and drop every subscriber. */
  dispose(): void {
    this.stop();
    this.subs.clear();
  }
}

/** Damping ratio ζ = c / (2·√(k·m)). <1 overshoots, ≈1 arrives without overshoot. */
export function dampingRatio(cfg: SpringConfig): number {
  const k = cfg.stiffness ?? 300;
  const c = cfg.damping ?? 30;
  const m = cfg.mass ?? 1;
  return c / (2 * Math.sqrt(k * m));
}
