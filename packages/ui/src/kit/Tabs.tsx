import * as React from "react";
import { MOTION } from "@gazyar/motion";
import { cx } from "../lib/cx";
import { toFa } from "../lib/digits";
import { SELECT } from "../lib/haptics";
import { isRtl } from "../lib/refs";
import { moveIndex, rovingKey } from "../lib/roving";
import { useControllable } from "../lib/useControllable";
import { useSpringBind, useSpringRef } from "../motion/hooks";
import { Pressable } from "../primitives/Pressable";
import styles from "./Tabs.module.css";

export type TabItem<V extends string = string> = {
  value: V;
  label: React.ReactNode;
  /** Count shown after the label (Persian digits). */
  badge?: number;
  disabled?: boolean;
};

export type TabsProps<V extends string = string> = Omit<React.HTMLAttributes<HTMLDivElement>, "onChange" | "defaultValue"> & {
  items: readonly TabItem<V>[];
  value?: V;
  defaultValue?: V;
  onValueChange?: (value: V) => void;
  /** Prefix for tab/panel ids — pair with <TabPanel idBase=…>. */
  idBase?: string;
  /** Tabs share the width equally (phone); default: natural width, scrolls (admin). */
  stretch?: boolean;
  ref?: React.Ref<HTMLDivElement>;
};

export const tabId = (base: string, value: string) => `${base}-tab-${value}`;
export const panelId = (base: string, value: string) => `${base}-panel-${value}`;

type Rect = { left: number; width: number };

/**
 * Underline tabs. One spring carries the *index* (0..n, fractional in
 * flight); the writer interpolates between the measured rects of the
 * two neighbouring tabs. Unequal tab widths animate correctly and a
 * resize only needs a re-measure, not a new animation.
 */
export function Tabs<V extends string = string>({
  items,
  value: valueProp,
  defaultValue,
  onValueChange,
  idBase: idBaseProp,
  stretch,
  className,
  ref,
  ...rest
}: TabsProps<V>) {
  const autoId = React.useId();
  const idBase = idBaseProp ?? autoId;
  const [value, setValue] = useControllable<V>(valueProp, defaultValue ?? (items[0]?.value as V), onValueChange);
  const index = Math.max(0, items.findIndex((it) => it.value === value));

  const tabs = React.useRef<Array<HTMLElement | null>>([]);
  const rects = React.useRef<Rect[]>([]);
  const spring = useSpringRef(index, MOTION.thumb);

  // Reads only refs, so it can be stable (and a dependency below).
  const write = React.useCallback((el: HTMLElement, x: number) => {
    const r = rects.current;
    if (!r.length) return;
    const i0 = Math.max(0, Math.min(r.length - 1, Math.floor(x)));
    const i1 = Math.min(r.length - 1, i0 + 1);
    const f = Math.max(0, Math.min(1, x - i0));
    const a = r[i0]!;
    const b = r[i1]!;
    const left = a.left + (b.left - a.left) * f;
    const width = a.width + (b.width - a.width) * f;
    el.style.transform = `translate3d(${left.toFixed(2)}px,0,0) scaleX(${width.toFixed(2)})`;
  }, []);
  const indicator = useSpringBind<HTMLSpanElement>(spring, write);
  const indicatorNode = React.useRef<HTMLSpanElement | null>(null);

  const measure = React.useCallback(() => {
    rects.current = tabs.current.map((t) => (t ? { left: t.offsetLeft, width: t.offsetWidth } : { left: 0, width: 0 }));
  }, []);

  // Measure before paint, then re-measure on resize (fonts loading,
  // rotation, a badge count changing width).
  React.useLayoutEffect(() => {
    tabs.current.length = items.length; // drop refs of removed tabs
    measure();
    if (indicatorNode.current) write(indicatorNode.current, spring.x);
    const list = tabs.current[0]?.parentElement;
    if (!list || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(() => {
      measure();
      if (indicatorNode.current) write(indicatorNode.current, spring.x);
    });
    ro.observe(list);
    for (const t of tabs.current) if (t) ro.observe(t);
    return () => ro.disconnect();
  }, [items, measure, spring, write]);

  React.useEffect(() => {
    spring.springTo(index, spring.v);
    // Keep the active tab visible in a scrolling tab bar.
    tabs.current[index]?.scrollIntoView?.({ block: "nearest", inline: "nearest" });
  }, [index, spring]);

  const select = (i: number, focus: boolean) => {
    const it = items[i];
    if (!it || it.disabled) return;
    if (it.value !== value) {
      SELECT();
      setValue(it.value);
    }
    if (focus) tabs.current[i]?.focus();
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

  const setIndicator = (el: HTMLSpanElement | null) => {
    indicatorNode.current = el;
    indicator(el);
  };

  return (
    <div
      {...rest}
      ref={ref}
      role="tablist"
      aria-orientation="horizontal"
      onKeyDown={onKeyDown}
      className={cx(styles.tabs, stretch && styles.stretch, className)}
    >
      {items.map((it, i) => (
        <Pressable
          key={it.value}
          ref={(el: HTMLElement | null) => {
            tabs.current[i] = el;
          }}
          id={tabId(idBase, it.value)}
          role="tab"
          aria-selected={i === index}
          aria-controls={panelId(idBase, it.value)}
          tabIndex={i === index ? 0 : -1}
          disabled={it.disabled}
          press="none"
          haptic={false}
          onPress={() => select(i, false)}
          className={styles.tab}
        >
          {it.label}
          {it.badge != null ? <span className={styles.badge}>{toFa(it.badge)}</span> : null}
        </Pressable>
      ))}
      <span ref={setIndicator} className={styles.indicator} aria-hidden="true" />
    </div>
  );
}

export type TabPanelProps = React.HTMLAttributes<HTMLDivElement> & {
  idBase: string;
  value: string;
  /** The currently selected tab value. */
  active: string;
  /** Keep inactive panels mounted (hidden) to preserve their state. Default false. */
  keepMounted?: boolean;
  ref?: React.Ref<HTMLDivElement>;
};

export function TabPanel({ idBase, value, active, keepMounted, className, children, ref, ...rest }: TabPanelProps) {
  const selected = value === active;
  if (!selected && !keepMounted) return null;
  return (
    <div
      {...rest}
      ref={ref}
      role="tabpanel"
      id={panelId(idBase, value)}
      aria-labelledby={tabId(idBase, value)}
      hidden={!selected}
      tabIndex={0}
      className={cx(styles.panel, className)}
    >
      {children}
    </div>
  );
}
