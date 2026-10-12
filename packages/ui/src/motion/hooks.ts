/* ─────────────────────────────────────────────────────────────
 *  React bindings for @gazyar/motion — two paths, deliberately apart.
 *
 *  Hot path (useSpringBind): the spring writes straight to a DOM node.
 *  Zero re-renders per frame. For anything above a large subtree:
 *  screens, sheets, the nav pill, rows, overscroll.
 *
 *  Cold path (useSpringState): the value goes through React state with
 *  a threshold. Only for tiny subtrees where a render per frame is
 *  cheaper than the bookkeeping (a 3-segment control's labels).
 * ───────────────────────────────────────────────────────────── */

import * as React from "react";
import {
  Spring,
  isReducedMotion,
  setReducedMotion,
  subscribeReducedMotion,
  type SpringConfig,
} from "@gazyar/motion";

/**
 * One Spring for the component's lifetime. Created lazily once (the
 * config is read at creation; call `spring.configure()` to retune).
 * On unmount it leaves the ticker so a dead component never steps.
 */
export function useSpringRef(initial: number, cfg?: SpringConfig): Spring {
  const [spring] = React.useState(() => new Spring(initial, cfg));
  React.useEffect(() => {
    // stop(), not dispose(): subscribers own their subscriptions and
    // remove them in their own effects. Disposing here would also drop
    // the subscriptions of children whose effects do not re-run — after
    // a Fast Refresh of this component, or StrictMode's simulated
    // unmount — leaving them silently unbound.
    return () => spring.stop();
  }, [spring]);
  return spring;
}

export type SpringWriter<T> = (el: T, x: number, v: number) => void;

/**
 * Hot path: bind a spring to a DOM node. Returns a stable callback ref.
 *
 * ── Why there is no `if (!node) return` in the effect ──────────────
 * The reference had one. A closed sheet rendered `null`, so when the
 * effect ran there was no node and it bailed — and because the deps
 * were `[spring]` and the spring never changes, the effect never ran
 * again. Every sheet in that app appeared instantly with no animation
 * — what users described as "opens and closes dryly". So: subscribe unconditionally, and let the writer skip a
 * missing node.
 *
 * One step further than the reference: the ref callback also writes
 * the spring's *current* value the moment a node attaches. A node that
 * mounts while the spring is at rest (a sheet opened at its resting
 * position, a row re-mounted by a list) would otherwise sit unstyled
 * until the spring next moved.
 */
export function useSpringBind<T extends Element>(spring: Spring, write: SpringWriter<T>): React.RefCallback<T> {
  const node = React.useRef<T | null>(null);
  const writer = React.useRef(write);
  // Latest writer without re-subscribing: the writer closes over props
  // (height, direction) that change, the subscription must not.
  React.useLayoutEffect(() => {
    writer.current = write;
  });

  React.useLayoutEffect(() => {
    return spring.subscribe((x, v) => {
      const el = node.current;
      if (el) writer.current(el, x, v);
    });
  }, [spring]);

  return React.useCallback(
    (el: T | null) => {
      node.current = el;
      if (el) writer.current(el, spring.x, spring.v);
    },
    [spring],
  );
}

/**
 * Cold path: the spring's value as React state. Renders only when the
 * value moved by more than `threshold` — a spring settling over its
 * last thousandths would otherwise render a dozen identical frames.
 */
export function useSpringState(spring: Spring, threshold = 0.0005): number {
  const [x, setX] = React.useState(spring.x);
  React.useEffect(
    () =>
      spring.subscribe((next) => {
        // Always land exactly on the target; filter only the in-between.
        setX((prev) => (next === spring.target || Math.abs(prev - next) > threshold ? next : prev));
      }),
    [spring, threshold],
  );
  return x;
}

const REDUCED_QUERY = "(prefers-reduced-motion: reduce)";

/**
 * Wire the OS "reduce motion" setting into the motion engine — live, so
 * toggling it mid-session takes effect without a reload, including on
 * animations already in flight. Call once near the root of each app.
 * (The engine itself cannot read matchMedia: it must run on React
 * Native unchanged.)
 */
export function useReducedMotionSync(): void {
  React.useLayoutEffect(() => {
    if (typeof matchMedia !== "function") return;
    const mql = matchMedia(REDUCED_QUERY);
    setReducedMotion(mql.matches);
    const onChange = (e: MediaQueryListEvent) => setReducedMotion(e.matches);
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, []);
}

/** Whether reduced motion is on (re-renders when it changes). */
export function useReducedMotion(): boolean {
  return React.useSyncExternalStore(subscribeReducedMotion, isReducedMotion, isReducedMotion);
}
