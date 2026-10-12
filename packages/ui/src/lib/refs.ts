/* Ref helpers. Components in this package take `ref` as a plain prop —
   React 19's replacement for forwardRef (which is slated for
   deprecation) — and merge it with their internal refs here. */

import * as React from "react";

export function assignRef<T>(ref: React.Ref<T> | undefined, value: T | null): void {
  if (typeof ref === "function") ref(value);
  else if (ref) (ref as React.RefObject<T | null>).current = value;
}

/**
 * One stable callback ref that feeds several refs. Stable identity
 * matters: a new callback each render makes React detach and re-attach
 * the node on every render, which re-runs every spring writer bound to
 * it. The latest refs are read at attach time.
 */
export function useMergedRefs<T>(...refs: Array<React.Ref<T> | undefined>): React.RefCallback<T> {
  const latest = React.useRef(refs);
  latest.current = refs;
  return React.useCallback((node: T | null) => {
    for (const r of latest.current) assignRef(r, node);
  }, []);
}

/** Direction of the nearest `dir` ancestor (layout mirrors itself; this is
 *  only for key handling and transforms, which CSS cannot mirror). */
export function isRtl(el: Element | null): boolean {
  const host = el?.closest("[dir]");
  if (host) return host.getAttribute("dir") === "rtl";
  if (typeof document !== "undefined") return document.documentElement.dir === "rtl";
  return true;
}
