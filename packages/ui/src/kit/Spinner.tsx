import * as React from "react";
import { cx } from "../lib/cx";
import styles from "./Spinner.module.css";

export type SpinnerProps = Omit<React.SVGProps<SVGSVGElement>, "ref"> & {
  size?: number;
  /** Announced to screen readers. Default «در حال بارگذاری». Pass "" when a parent already says it (a loading button). */
  label?: string;
  ref?: React.Ref<SVGSVGElement>;
};

/** Indeterminate spinner in currentColor. Keeps turning (slowly) under reduced motion — a frozen one looks hung. */
export function Spinner({ size = 20, label = "در حال بارگذاری", className, ref, ...rest }: SpinnerProps) {
  const a11y = label ? { role: "status", "aria-label": label } : { "aria-hidden": true as const };
  return (
    <svg
      {...a11y}
      {...rest}
      ref={ref}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      data-gz-spinner=""
      className={cx(styles.spinner, className)}
    >
      <circle className={styles.track} cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2.6" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" />
    </svg>
  );
}
