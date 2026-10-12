/* ─────────────────────────────────────────────────────────────
 *  Tween — time-based interpolation on the shared ticker.
 *
 *  Springs are for anything interruptible or gesture-driven. A few
 *  things want a fixed duration instead: a chart line drawing in, a
 *  progress sweep that must finish in step with a sound or haptic.
 *  This runs on the same loop as the springs (one rAF for everything)
 *  and honours reduced motion the same way: jump to the end, still
 *  call onDone.
 *
 *  Time advances by the ticker's clamped dt, not wall-clock: after a
 *  dropped frame a tween runs a few ms late rather than jumping — the
 *  same trade the springs make.
 * ───────────────────────────────────────────────────────────── */

import { isReducedMotion } from "./reduced";
import { join, leave, type Tickable } from "./ticker";

export type Easing = (t: number) => number;

export const EASING = {
  linear: (t: number) => t,
  /** Fast start, gentle landing — the default for draw-ins. */
  outCubic: (t: number) => 1 - (1 - t) ** 3,
  /** Stronger deceleration — long count-ups, chart bars. */
  outQuart: (t: number) => 1 - (1 - t) ** 4,
  /** Symmetric — progress sweeps that start and end at rest. */
  inOutCubic: (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2),
  /** Overshoots ~10% then returns — small celebratory pops. */
  outBack: (t: number) => {
    const c1 = 1.70158;
    const c3 = c1 + 1;
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2;
  },
} as const satisfies Record<string, Easing>;

export type TweenOptions = {
  from: number;
  to: number;
  /** Milliseconds. */
  duration: number;
  ease?: Easing;
  /** Milliseconds before the value starts moving (it holds `from`). */
  delay?: number;
  onUpdate: (value: number, progress: number) => void;
  /** Fires once on completion — also under reduced motion. Not on stop(). */
  onDone?: () => void;
};

export class Tween implements Tickable {
  private elapsed = 0;
  private running = false;
  private opts: TweenOptions;

  constructor(opts: TweenOptions) {
    this.opts = opts;
  }

  get isRunning(): boolean {
    return this.running;
  }

  /** (Re)start from the beginning. Emits `from` immediately. */
  start(): this {
    this.elapsed = 0;
    if (isReducedMotion() || this.opts.duration <= 0) {
      leave(this);
      this.finish();
      return this;
    }
    this.running = true;
    this.opts.onUpdate(this.opts.from, 0);
    join(this);
    return this;
  }

  /** Halt where it is; onDone does not fire. */
  stop(): void {
    this.running = false;
    leave(this);
  }

  step(dt: number): boolean {
    if (!this.running) return false;
    if (isReducedMotion()) {
      this.finish();
      return false;
    }
    this.elapsed += dt * 1000;
    const { duration, delay = 0, from, to, ease = EASING.outCubic } = this.opts;
    const t = Math.min(1, Math.max(0, (this.elapsed - delay) / duration));
    if (t >= 1) {
      this.finish();
      return this.running; // onDone may have restarted it
    }
    this.opts.onUpdate(from + (to - from) * ease(t), t);
    return true;
  }

  private finish(): void {
    this.running = false;
    this.opts.onUpdate(this.opts.to, 1);
    this.opts.onDone?.();
  }
}

/** Start a tween and return it (call `.stop()` to cancel). */
export function tween(opts: TweenOptions): Tween {
  return new Tween(opts).start();
}
