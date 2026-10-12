import * as React from "react";
import { cx } from "../lib/cx";
import styles from "./motion.module.css";

export type RevealProps = React.HTMLAttributes<HTMLElement> & {
  /** Position in the list — sets the stagger. */
  i?: number;
  /** ms between items. Default 42. */
  step?: number;
  /** Longest delay, ms. Default 380: item 30 must not wait 1.3s to appear. */
  cap?: number;
  /** Rise distance, px. Default 10. */
  y?: number;
  as?: "div" | "li" | "section" | "article";
  ref?: React.Ref<HTMLElement>;
};

/** Delay for item `i`: linear stagger, capped. */
export function revealDelay(i: number, step = 42, cap = 380): number {
  return Math.min(Math.max(0, i) * step, cap);
}

/**
 * Staggered entry for short lists (a CSS animation, `revealIn`).
 * Deliberately not for virtualised rows: there it replays every time a
 * row scrolls into the window and makes scrolling shimmer.
 */
export function Reveal({ i = 0, step = 42, cap = 380, y = 10, as = "div", className, style, ref, ...rest }: RevealProps) {
  const vars = { "--rv-y": `${y}px`, "--rv-delay": `${revealDelay(i, step, cap)}ms` } as React.CSSProperties;
  return React.createElement(as, { ...rest, ref, className: cx(styles.reveal, className), style: { ...vars, ...style } });
}
