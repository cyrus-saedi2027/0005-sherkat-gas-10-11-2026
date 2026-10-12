import * as React from "react";
import { cx } from "../lib/cx";
import { toFa } from "../lib/digits";
import type { StatusLabel, Tone } from "../lib/tones";
import { Icon } from "../icons";
import { Pressable, type PressableProps } from "../primitives/Pressable";
import { VisuallyHidden } from "../primitives/VisuallyHidden";
import styles from "./Badge.module.css";

/* ── Chip ──────────────────────────────────────────────────── */

export type ChipProps = Omit<PressableProps, "as" | "children"> & {
  children?: React.ReactNode;
  /** Toggle state for filter chips — announced as aria-pressed. */
  selected?: boolean;
  icon?: React.ReactNode;
  /** A tinted, non-toggle chip (e.g. a category tag). */
  tone?: Tone;
  size?: "sm" | "md";
  /** Adds a remove (×) button, e.g. for an applied filter. */
  onRemove?: () => void;
  removeLabel?: string;
};

export function Chip({
  selected,
  icon,
  tone,
  size = "md",
  onRemove,
  removeLabel = "حذف",
  onPress,
  className,
  children,
  ...rest
}: ChipProps) {
  const cls = cx(styles.chip, size === "sm" && styles.sm, className);
  const toneAttr = tone && tone !== "neutral" ? tone : undefined;
  const content = (
    <>
      {icon}
      <span>{children}</span>
    </>
  );

  if (onRemove) {
    // Two actions cannot nest (a button in a button), so a removable
    // chip is a plain container with one real button inside.
    return (
      <span className={cls} data-gz-tone={toneAttr} data-selected={selected || undefined}>
        {content}
        <button type="button" className={styles.remove} aria-label={`${removeLabel}: ${typeof children === "string" ? children : ""}`.trim()} onClick={onRemove}>
          <Icon.close size={14} stroke={2.4} />
        </button>
      </span>
    );
  }

  return (
    <Pressable
      {...rest}
      as={onPress ? "button" : "span"}
      onPress={onPress}
      press="firm"
      aria-pressed={onPress && selected !== undefined ? selected : undefined}
      data-selected={!onPress && selected ? true : undefined}
      data-gz-tone={toneAttr}
      className={cls}
    >
      {content}
    </Pressable>
  );
}

/* ── Badge ─────────────────────────────────────────────────── */

export type BadgeProps = Omit<React.HTMLAttributes<HTMLSpanElement>, "children"> & {
  /** A count (Persian digits, capped by `max`) or short text. Omit for a dot. */
  count?: number;
  children?: React.ReactNode;
  max?: number;
  tone?: Tone;
  /** Solid fill (count on an icon) vs. soft wash (inline). Default soft. */
  solid?: boolean;
  /** Screen-reader text, e.g. «۳ اعلان خوانده‌نشده». A bare number means nothing out of context. */
  label?: string;
  ref?: React.Ref<HTMLSpanElement>;
};

export function Badge({ count, children, max = 99, tone = "neutral", solid, label, className, ref, ...rest }: BadgeProps) {
  const dot = count === undefined && children == null;
  const text = count !== undefined ? (count > max ? `${toFa(max)}+` : toFa(count)) : children;
  return (
    <span
      {...rest}
      ref={ref}
      data-gz-tone={tone}
      className={cx(styles.badge, solid && styles.solid, dot && styles.dotOnly, className)}
    >
      {label ? <span aria-hidden="true">{text}</span> : text}
      {label ? <VisuallyHidden>{label}</VisuallyHidden> : null}
    </span>
  );
}

/* ── StatusPill ────────────────────────────────────────────── */

export type StatusPillProps = Omit<React.HTMLAttributes<HTMLSpanElement>, "children"> & {
  /** A status from @gazyar/core's label tables: `{ fa, tone }`. */
  status?: StatusLabel;
  /** Or label + tone directly. */
  label?: React.ReactNode;
  tone?: Tone;
  /** Leading dot. Default true — status must not rely on colour alone, so the label is always text. */
  dot?: boolean;
  size?: "sm" | "md";
  ref?: React.Ref<HTMLSpanElement>;
};

export function StatusPill({ status, label, tone, dot = true, size = "md", className, ref, ...rest }: StatusPillProps) {
  const t: Tone = tone ?? status?.tone ?? "neutral";
  return (
    <span {...rest} ref={ref} data-gz-tone={t} className={cx(styles.pill, size === "sm" && styles.sm, className)}>
      {dot ? <i className={styles.dot} aria-hidden="true" /> : null}
      {label ?? status?.fa}
    </span>
  );
}
