import * as React from "react";
import { MOTION } from "@gazyar/motion";
import { cx } from "../lib/cx";
import type { Tone } from "../lib/tones";
import { useSpringBind, useSpringRef } from "../motion/hooks";
import styles from "./Progress.module.css";

const clamp01 = (n: number) => (Number.isFinite(n) ? Math.min(1, Math.max(0, n)) : 0);

/* ── Ring ──────────────────────────────────────────────────── */

export type RingProps = Omit<React.HTMLAttributes<HTMLDivElement>, "children"> & {
  /** 0..1 */
  value: number;
  size?: number;
  thickness?: number;
  tone?: Tone;
  /** Accessible name, e.g. «پیشرفت بارگذاری». */
  label?: string;
  /** Centre content (a percentage, an icon). */
  children?: React.ReactNode;
  ref?: React.Ref<HTMLDivElement>;
};

/**
 * Circular progress (uploads, monthly goal). The arc is a dash offset
 * written by a near-critical spring (`swipe`, ζ≈0.94): progress that
 * overshoots would briefly claim more than is done.
 */
export function Ring({ value, size = 56, thickness = 5, tone, label, children, className, ref, ...rest }: RingProps) {
  const v = clamp01(value);
  const r = (size - thickness) / 2;
  const c = 2 * Math.PI * r;
  const spring = useSpringRef(0, MOTION.swipe);
  const arc = useSpringBind<SVGCircleElement>(spring, (el, x) => {
    el.setAttribute("stroke-dashoffset", (c * (1 - Math.min(1, Math.max(0, x)))).toFixed(2));
  });
  React.useEffect(() => {
    spring.springTo(v, spring.v);
  }, [v, spring]);

  return (
    <div
      {...rest}
      ref={ref}
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(v * 100)}
      className={cx(styles.ring, className)}
      data-gz-tone={tone}
    >
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true">
        <circle className={styles.ringTrack} cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={thickness} />
        <circle
          ref={arc}
          className={styles.ringValue}
          data-gz-tone={tone}
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          strokeWidth={thickness}
          strokeLinecap="round"
          strokeDasharray={c.toFixed(2)}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </svg>
      {children != null ? <div className={styles.ringCenter}>{children}</div> : null}
    </div>
  );
}

/* ── ProgressBar ───────────────────────────────────────────── */

export type ProgressBarProps = Omit<React.HTMLAttributes<HTMLDivElement>, "children"> & {
  /** 0..1, or undefined for indeterminate. */
  value?: number;
  tone?: Tone;
  size?: "sm" | "md";
  label?: string;
  ref?: React.Ref<HTMLDivElement>;
};

export function ProgressBar({ value, tone, size = "md", label, className, ref, ...rest }: ProgressBarProps) {
  const indeterminate = value === undefined;
  const v = indeterminate ? 0 : clamp01(value);
  const spring = useSpringRef(0, MOTION.swipe);
  const fill = useSpringBind<HTMLDivElement>(spring, (el, x) => {
    if (indeterminate) {
      el.style.transform = "";
      return;
    }
    el.style.transform = `scaleX(${Math.min(1, Math.max(0, x)).toFixed(4)})`;
  });
  React.useEffect(() => {
    if (!indeterminate) spring.springTo(v, spring.v);
  }, [v, indeterminate, spring]);

  return (
    <div
      {...rest}
      ref={ref}
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={indeterminate ? undefined : Math.round(v * 100)}
      className={cx(styles.bar, size === "sm" && styles.sm, indeterminate && styles.indeterminate, className)}
    >
      <div ref={fill} className={styles.fill} data-gz-tone={tone} />
    </div>
  );
}
