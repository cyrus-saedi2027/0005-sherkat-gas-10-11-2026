/* ─────────────────────────────────────────────────────────────
 *  One requestAnimationFrame loop for every spring and tween.
 *
 *  One rAF per spring is the obvious design and it is wrong: when a
 *  sheet is dragged while a row swipes, the nav pill slides and the
 *  scroll bounces, four loops fight over one frame. Here every live
 *  animation shares a single loop, and the loop goes to sleep (no rAF
 *  scheduled at all) the moment nothing is moving.
 *
 *  Platform-neutral on purpose: no `window`. The frame source is looked
 *  up on `globalThis` each time a frame is scheduled — browsers and
 *  React Native both provide `requestAnimationFrame`; plain Node (SSR,
 *  tests) falls back to a 16ms timer so springs still settle.
 * ───────────────────────────────────────────────────────────── */

export type Tickable = {
  /** Advance by `dt` seconds. Return `true` to stay in the loop. */
  step: (dt: number) => boolean;
};

type FrameGlobals = {
  requestAnimationFrame?: (cb: (now: number) => void) => number;
  cancelAnimationFrame?: (handle: number) => void;
  performance?: { now: () => number };
};

const g = globalThis as unknown as FrameGlobals;

/** Monotonic milliseconds — `performance.now()` where it exists. */
export function now(): number {
  return typeof g.performance?.now === "function" ? g.performance.now() : Date.now();
}

/** Longest step a frame may take, in seconds. */
export const MAX_DT = 1 / 30;

const live = new Set<Tickable>();
let cancelPending: (() => void) | null = null;
let last = 0;
/* True while `frame` is iterating. join()/leave() called from inside a
   step (an onRest that starts the next animation, an unmount that
   disposes a spring) must not schedule or cancel frames themselves:
   the reference did, and a leave-then-join inside one frame scheduled
   two rAFs, so every spring stepped twice per frame from then on. The
   end of `frame` is the single place that decides whether to continue. */
let inFrame = false;

function schedule(): void {
  if (typeof g.requestAnimationFrame === "function") {
    const raf = g.requestAnimationFrame;
    const caf = g.cancelAnimationFrame;
    const id = raf(frame);
    cancelPending = () => caf?.(id);
  } else {
    const id = setTimeout(() => frame(now()), 16);
    cancelPending = () => clearTimeout(id);
  }
}

function frame(t: number): void {
  cancelPending = null;
  // Clamp: after a dropped frame (GC pause, slow paint) an unclamped dt
  // makes every spring visibly jump. Exact timing loses to never looking broken.
  const dt = last ? Math.min(Math.max((t - last) / 1000, 0), MAX_DT) : 1 / 60;
  last = t;

  inFrame = true;
  // Iterate over a copy: a step may remove itself (or others) from the
  // set, and mutating a Set mid-iteration skips entries.
  for (const item of Array.from(live)) {
    if (!live.has(item)) continue; // removed by an earlier step this frame
    try {
      if (!item.step(dt)) live.delete(item);
    } catch (err) {
      // One broken subscriber must not freeze every other animation on
      // screen: drop it, keep the loop alive, surface the error async.
      live.delete(item);
      queueMicrotask(() => {
        throw err;
      });
    }
  }
  inFrame = false;

  if (live.size) schedule();
  else last = 0; // sleep; the next wake starts with a fresh 1/60 step
}

/** Add to the loop (idempotent). Wakes the loop if it was asleep. */
export function join(t: Tickable): void {
  live.add(t);
  if (!inFrame && !cancelPending) schedule();
}

/** Remove from the loop. Stops the loop when nothing is left. */
export function leave(t: Tickable): void {
  live.delete(t);
  if (!inFrame && !live.size && cancelPending) {
    cancelPending();
    cancelPending = null;
    last = 0;
  }
}

/** Whether a frame is currently scheduled (false = the loop is asleep). */
export function isTickerAwake(): boolean {
  return cancelPending !== null;
}

/** Number of animations in the loop. */
export function liveCount(): number {
  return live.size;
}

/**
 * Drop every animation and cancel the pending frame. For test isolation
 * and hot-module reload — a reloaded module must not leave orphaned
 * tickables stepping against a dead closure.
 */
export function resetTicker(): void {
  live.clear();
  cancelPending?.();
  cancelPending = null;
  last = 0;
  inFrame = false;
}
