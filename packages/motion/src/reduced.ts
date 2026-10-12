/* ─────────────────────────────────────────────────────────────
 *  Reduced-motion switch — module state, not a media query.
 *
 *  This package must run unchanged under React Native, so it cannot
 *  read `matchMedia` itself. The platform layer (packages/ui on the
 *  web, AccessibilityInfo on native) pushes the OS preference in with
 *  `setReducedMotion`. Every Spring and Tween reads it at the moment
 *  it would move, so flipping the OS setting takes effect mid-session
 *  without a reload — including animations already in flight.
 * ───────────────────────────────────────────────────────────── */

type Listener = (reduced: boolean) => void;

let reduced = false;
const listeners = new Set<Listener>();

/** Push the platform's reduced-motion preference into the engine. */
export function setReducedMotion(on: boolean): void {
  if (reduced === on) return;
  reduced = on;
  // Copy: a listener may unsubscribe itself while being notified.
  for (const l of Array.from(listeners)) l(on);
}

export function isReducedMotion(): boolean {
  return reduced;
}

/**
 * Observe changes (not the current value — read `isReducedMotion()` for
 * that). Shaped for React's `useSyncExternalStore`.
 */
export function subscribeReducedMotion(fn: Listener): () => void {
  listeners.add(fn);
  return () => {
    listeners.delete(fn);
  };
}
