import * as React from "react";
import { cx } from "../lib/cx";
import { toFa } from "../lib/digits";
import { formatMoney, formatPoints } from "../lib/money";
import type { Tone } from "../lib/tones";
import { Icon } from "../icons";
import { CountUp } from "../motion/CountUp";
import { Pressable, type PressableProps } from "../primitives/Pressable";
import { VisuallyHidden } from "../primitives/VisuallyHidden";
import { Skeleton } from "./Skeleton";
import styles from "./Stat.module.css";

export type StatFormat = "number" | "money" | "points" | "percent";

export type StatDelta = {
  /** Change in percent (signed): −12 means 12% lower. */
  value: number;
  /** Which direction is good. Gas consumption: "down". Points: "up". */
  goodWhen?: "up" | "down";
  /** Context after the number, e.g. «نسبت به سال قبل». */
  note?: React.ReactNode;
};

export type StatProps = Omit<PressableProps, "as" | "children"> & {
  label: React.ReactNode;
  value: number;
  format?: StatFormat;
  decimals?: number;
  /** Unit after the number for "number" format, e.g. «مترمکعب». */
  unit?: React.ReactNode;
  icon?: React.ReactNode;
  tone?: Tone;
  delta?: StatDelta;
  loading?: boolean;
};

function formatter(format: StatFormat, decimals: number): ((n: number) => string) | undefined {
  switch (format) {
    case "money":
      return (n) => formatMoney(n);
    case "points":
      return (n) => formatPoints(n, { unit: false });
    case "percent":
      return (n) => `${toFa(n, { decimals: decimals || undefined })}٪`;
    default:
      return undefined;
  }
}

/** KPI tile: label, a counting number, optional trend vs. a baseline. */
export function Stat({
  label,
  value,
  format = "number",
  decimals = 0,
  unit,
  icon,
  tone,
  delta,
  loading,
  onPress,
  className,
  ...rest
}: StatProps) {
  const tag = rest.href ? "a" : onPress ? "button" : "div";
  let deltaTone: Tone = "neutral";
  if (delta && delta.value !== 0) {
    const up = delta.value > 0;
    const good = (delta.goodWhen ?? "up") === "up" ? up : !up;
    deltaTone = good ? "ok" : "crit";
  }

  return (
    <Pressable
      {...rest}
      as={tag}
      onPress={onPress}
      press={onPress || rest.href ? "subtle" : "none"}
      className={cx(styles.stat, className)}
      aria-busy={loading || undefined}
    >
      <span className={styles.head}>
        {icon ? (
          <span className={styles.icon} data-gz-tone={tone} aria-hidden="true">
            {icon}
          </span>
        ) : null}
        <span className={styles.label}>{label}</span>
      </span>
      {loading ? (
        <Skeleton variant="text" width="60%" height={28} />
      ) : (
        <span className={styles.value}>
          <CountUp value={value} decimals={decimals} format={formatter(format, decimals)} />
          {format === "points" ? <span className={styles.unit}>امتیاز</span> : null}
          {unit && format === "number" ? <span className={styles.unit}>{unit}</span> : null}
        </span>
      )}
      {delta && !loading ? (
        <span className={styles.delta} data-gz-tone={deltaTone}>
          {delta.value > 0 ? (
            <Icon.trendUp size={14} stroke={2.2} />
          ) : delta.value < 0 ? (
            <Icon.trendDown size={14} stroke={2.2} />
          ) : null}
          <VisuallyHidden>{delta.value > 0 ? "افزایش" : delta.value < 0 ? "کاهش" : "بدون تغییر"}</VisuallyHidden>
          <bdi>{toFa(Math.abs(delta.value), { decimals: Number.isInteger(delta.value) ? undefined : 1 })}٪</bdi>
          {delta.note ? <span className={styles.deltaNote}>{delta.note}</span> : null}
        </span>
      ) : null}
    </Pressable>
  );
}
