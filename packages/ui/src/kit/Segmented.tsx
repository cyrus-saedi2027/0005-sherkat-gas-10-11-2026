import * as React from "react";
import { MOTION } from "@gazyar/motion";
import { cx } from "../lib/cx";
import { SELECT } from "../lib/haptics";
import { isRtl } from "../lib/refs";
import { moveIndex, rovingKey } from "../lib/roving";
import { useControllable } from "../lib/useControllable";
import { useSpringBind, useSpringRef } from "../motion/hooks";
import { Pressable } from "../primitives/Pressable";
import styles from "./Segmented.module.css";

export type SegmentedItem<V extends string = string> = {
  value: V;
  label: React.ReactNode;
  /** Accessible name when the label is an icon. */
  ariaLabel?: string;
  disabled?: boolean;
};

export type SegmentedProps<V extends string = string> = Omit<React.HTMLAttributes<HTMLDivElement>, "onChange" | "defaultValue"> & {
  items: readonly SegmentedItem<V>[];
  value?: V;
  defaultValue?: V;
  onValueChange?: (value: V) => void;
  size?: "sm" | "md";
  fullWidth?: boolean;
  ref?: React.Ref<HTMLDivElement>;
};

/**
 * Segmented control — a radio group (one tab stop, arrows move and
 * select, following reading direction). The indicator slides on the
 * `thumb` spring between columns, written to the DOM; retapping
 * mid-slide redirects it with its velocity.
 */
export function Segmented<V extends string = string>({
  items,
  value: valueProp,
  defaultValue,
  onValueChange,
  size = "md",
  fullWidth,
  className,
  style,
  ref,
  ...rest
}: SegmentedProps<V>) {
  const first = items[0]?.value as V;
  const [value, setValue] = useControllable<V>(valueProp, defaultValue ?? first, onValueChange);
  const index = Math.max(0, items.findIndex((it) => it.value === value));

  const spring = useSpringRef(index, MOTION.thumb);
  const sign = React.useRef<number | null>(null);
  const indicator = useSpringBind<HTMLSpanElement>(spring, (el, x) => {
    sign.current ??= isRtl(el) ? -1 : 1;
    el.style.transform = `translate3d(${(sign.current * x * 100).toFixed(3)}%,0,0)`;
  });
  React.useEffect(() => {
    spring.springTo(index, spring.v);
  }, [index, spring]);

  const buttons = React.useRef<Array<HTMLElement | null>>([]);

  const select = (i: number, focus: boolean) => {
    const it = items[i];
    if (!it || it.disabled) return;
    if (it.value !== value) {
      SELECT();
      setValue(it.value);
    }
    if (focus) buttons.current[i]?.focus();
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    const dir = rovingKey(e, isRtl(e.currentTarget));
    if (!dir) return;
    e.preventDefault();
    const next = moveIndex(
      index,
      dir,
      items.map((it) => !!it.disabled),
    );
    if (next >= 0) select(next, true);
  };

  // --n (item count) is data for the indicator's width rule, not styling.
  const vars = { "--n": items.length } as React.CSSProperties;
  return (
    <div
      {...rest}
      ref={ref}
      role="radiogroup"
      onKeyDown={onKeyDown}
      className={cx(styles.segmented, fullWidth && styles.full, size === "sm" && styles.sm, className)}
      style={{ ...vars, ...style }}
    >
      <span ref={indicator} className={styles.indicator} aria-hidden="true" />
      {items.map((it, i) => (
        <Pressable
          key={it.value}
          ref={(el: HTMLElement | null) => {
            buttons.current[i] = el;
          }}
          role="radio"
          aria-checked={i === index}
          aria-label={it.ariaLabel}
          tabIndex={i === index ? 0 : -1}
          disabled={it.disabled}
          press="subtle"
          haptic={false}
          onPress={() => select(i, false)}
          className={styles.item}
        >
          {it.label}
        </Pressable>
      ))}
    </div>
  );
}
