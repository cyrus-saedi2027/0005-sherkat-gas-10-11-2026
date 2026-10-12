import * as React from "react";
import { cx } from "../lib/cx";
import { useMergedRefs } from "../lib/refs";
import styles from "./motion.module.css";

export type FadeProps = React.HTMLAttributes<HTMLDivElement> & {
  /** Rise distance, px. Default 6. */
  y?: number;
  /** ms. Default 300. */
  duration?: number;
  /** ms. Default 0. */
  delay?: number;
  ref?: React.Ref<HTMLDivElement>;
};

/**
 * Fade + rise on mount — a CSS transition, for entries that are never
 * interrupted. Change `key` to replay. The "on" flag is written to the
 * node in the next frame (not React state), so entering costs no extra
 * render; the reduced-motion media query in global.css collapses it.
 */
export function Fade({ y = 6, duration = 300, delay = 0, className, style, ref, ...rest }: FadeProps) {
  const node = React.useRef<HTMLDivElement | null>(null);
  const setRef = useMergedRefs(node, ref);

  React.useEffect(() => {
    const el = node.current;
    if (!el) return;
    // One frame after insertion, so the browser has painted the "from"
    // state; setting it in the same frame skips the transition.
    const id = requestAnimationFrame(() => el.setAttribute("data-on", ""));
    return () => cancelAnimationFrame(id);
  }, []);

  // Per-instance timing as custom properties (data for the CSS rule,
  // not styling): one class serves every distance/duration.
  const vars = { "--fade-y": `${y}px`, "--fade-dur": `${duration}ms`, "--fade-delay": `${delay}ms` } as React.CSSProperties;
  return <div {...rest} ref={setRef} className={cx(styles.fade, className)} style={{ ...vars, ...style }} />;
}
