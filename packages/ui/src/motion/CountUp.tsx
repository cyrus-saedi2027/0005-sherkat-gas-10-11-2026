/* ─────────────────────────────────────────────────────────────
 *  CountUp — a number that counts to its value.
 *
 *  The spring writes Persian digits straight into the node's
 *  textContent: a 600ms count on a KPI tile costs zero React renders.
 *  The animated digits are aria-hidden and the final value sits next
 *  to them in a visually-hidden span, so a screen reader announces
 *  "۱۲٬۰۰۰" once instead of whatever frame it happened to land on.
 *
 *  Uses MOTION.count (ζ≈1.03, critically damped): a counter that
 *  overshoots shows a wrong number for a moment.
 * ───────────────────────────────────────────────────────────── */

import * as React from "react";
import { MOTION } from "@gazyar/motion";
import { cx } from "../lib/cx";
import { toFa } from "../lib/digits";
import { useMergedRefs } from "../lib/refs";
import { VisuallyHidden } from "../primitives/VisuallyHidden";
import { useSpringBind, useSpringRef } from "./hooks";
import styles from "./motion.module.css";

export type CountUpProps = Omit<React.HTMLAttributes<HTMLSpanElement>, "children"> & {
  value: number;
  /** Start of the first count. Default 0. Later changes count from the current value. */
  from?: number;
  /** Fixed decimals. Default 0. */
  decimals?: number;
  /** ٬ grouping. Default true. */
  group?: boolean;
  /** Custom formatter (receives the rounded value). Default: Persian digits. */
  format?: (n: number) => string;
  ref?: React.Ref<HTMLSpanElement>;
};

function round(n: number, decimals: number): number {
  const f = 10 ** decimals;
  return Math.round(n * f) / f;
}

export function CountUp({ value, from = 0, decimals = 0, group = true, format, className, ref, ...rest }: CountUpProps) {
  // Settle within half of the last displayed digit, not MOTION.count's
  // 0.5 units: with decimals the default would freeze 0.4 short.
  const precision = decimals > 0 ? 0.5 * 10 ** -decimals : MOTION.count.precision;
  const spring = useSpringRef(from, { ...MOTION.count, precision });

  const fmt = (n: number) => {
    const r = round(n, decimals);
    return format ? format(r) : toFa(r, { decimals: decimals || undefined, group });
  };

  const bind = useSpringBind<HTMLSpanElement>(spring, (el, x) => {
    const text = fmt(x);
    if (el.textContent !== text) el.textContent = text;
  });
  const node = React.useRef<HTMLSpanElement | null>(null);
  const setRef = useMergedRefs(bind, node);

  React.useLayoutEffect(() => {
    spring.springTo(value, spring.v);
  }, [spring, value]);

  // Re-apply after every render: a new `format`/`decimals` must show
  // even when the spring is at rest and will not emit again.
  React.useLayoutEffect(() => {
    bind(node.current);
  });

  return (
    <span {...rest} ref={ref} className={cx(styles.count, className)}>
      <span ref={setRef} aria-hidden="true" data-countup="" />
      <VisuallyHidden>{fmt(value)}</VisuallyHidden>
    </span>
  );
}
