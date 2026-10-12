import * as React from "react";
import { cx } from "../lib/cx";
import styles from "./Feedback.module.css";

export type SkeletonProps = Omit<React.HTMLAttributes<HTMLSpanElement>, "children"> & {
  variant?: "text" | "rect" | "circle";
  /** CSS length or px. For circle, the diameter. */
  width?: number | string;
  height?: number | string;
  /** text only: number of lines (the last one shorter). */
  lines?: number;
  ref?: React.Ref<HTMLSpanElement>;
};

const len = (v: number | string | undefined) => (typeof v === "number" ? `${v}px` : v);

/**
 * Placeholder with a shimmer sweep (background-position only — never
 * layout). Hidden from screen readers; the container should carry
 * aria-busy while loading.
 */
export function Skeleton({ variant = "text", width, height, lines = 1, className, style, ref, ...rest }: SkeletonProps) {
  // Size as custom properties: data for the shared rule, one class for every size.
  const vars = { "--sk-w": len(width), "--sk-h": len(height) } as React.CSSProperties;
  const cls = cx(styles.skeleton, variant === "circle" && styles.circle, variant === "rect" && styles.rect);
  if (variant === "text" && lines > 1) {
    return (
      <span {...rest} ref={ref} aria-hidden="true" className={cx(styles.lines, className)} style={style}>
        {Array.from({ length: lines }, (_, i) => (
          <span key={i} className={cls} style={vars} />
        ))}
      </span>
    );
  }
  return <span {...rest} ref={ref} aria-hidden="true" className={cx(cls, className)} style={{ ...vars, ...style }} />;
}
