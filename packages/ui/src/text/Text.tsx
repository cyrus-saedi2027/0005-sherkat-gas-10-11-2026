import * as React from "react";
import { cx } from "../lib/cx";
import { toFa } from "../lib/digits";
import { formatMoney, formatPoints, type MoneyUnit } from "../lib/money";
import type { Tone } from "../lib/tones";
import styles from "./text.module.css";

type BlockTag = "h1" | "h2" | "h3" | "h4" | "p" | "div" | "span" | "label" | "strong" | "legend";

type TextProps = React.HTMLAttributes<HTMLElement> & {
  as?: BlockTag;
  ref?: React.Ref<HTMLElement>;
};

function make(base: string | undefined, defaultTag: BlockTag, displayName: string) {
  function C({ as = defaultTag, className, ref, ...rest }: TextProps) {
    return React.createElement(as, { ...rest, ref, className: cx(base, className) });
  }
  C.displayName = displayName;
  return C;
}

/** Screen title — 22/800. Defaults to <h1>; one per screen. */
export const Title = make(styles.title, "h1", "Title");

/** Section heading — 16/800. Defaults to <h2>. */
export const Head = make(styles.head, "h2", "Head");

export type BodyProps = TextProps & {
  /** muted (default) for running text, ink for emphasis, faint for footnotes. */
  tone?: "muted" | "ink" | "faint";
};

/** Running text — 14/500, inkMuted. Defaults to <p>. */
export function Body({ as = "p", tone = "muted", className, ref, ...rest }: BodyProps) {
  return React.createElement(as, { ...rest, ref, "data-tone": tone, className: cx(styles.body, className) });
}

export type CapProps = TextProps & {
  /** A small coloured dot before the label — the Persian replacement for a tracked uppercase eyebrow. */
  dot?: Tone | boolean;
};

/** Small label — 11/700, inkFaint. */
export function Cap({ as = "span", dot, className, children, ref, ...rest }: CapProps) {
  return React.createElement(
    as,
    { ...rest, ref, className: cx(styles.cap, className) },
    dot ? <i className={styles.dot} data-tone={dot === true ? undefined : dot} aria-hidden="true" /> : null,
    children,
  );
}

export type NumProps = Omit<React.HTMLAttributes<HTMLElement>, "children"> & {
  value: number | string;
  /** ٬ grouping. Default true. */
  group?: boolean;
  decimals?: number;
  /** Prefix positives with "+" (deltas). */
  signed?: boolean;
  bold?: boolean;
  ref?: React.Ref<HTMLElement>;
};

/**
 * A number for people: Persian digits, ٬ grouping, tabular, inside <bdi>.
 * Without the isolate, "+۱۰" in a Persian sentence renders as "۱۰+".
 */
export function Num({ value, group = true, decimals, signed, bold, className, ref, ...rest }: NumProps) {
  let text = toFa(value, { group, decimals });
  if (signed && typeof value === "number" && value > 0) text = `+${text}`;
  return (
    <bdi {...rest} ref={ref} className={cx(styles.num, className)} data-weight={bold ? "bold" : undefined}>
      {text}
    </bdi>
  );
}

export type LatProps = React.HTMLAttributes<HTMLElement> & { ref?: React.Ref<HTMLElement> };

/** An inline Latin run (brand names, usernames, IBAN) — forced LTR and isolated so bidi cannot reorder it. */
export function Lat({ className, ref, ...rest }: LatProps) {
  return <bdi {...rest} ref={ref} dir="ltr" className={cx(styles.lat, className)} />;
}

export type CodeProps = Omit<React.HTMLAttributes<HTMLElement>, "children"> & {
  /** Identifier shown as is: tracking codes, subscription numbers. Digits stay ASCII — it is an id, not a quantity. */
  code: string | number;
  ref?: React.Ref<HTMLElement>;
};

/**
 * A code people read out or type back (ticket "GZ-140507-00012", a
 * subscription number). ASCII digits on purpose: it is matched against
 * what is printed on the bill, and isolated so a Persian sentence
 * cannot flip its dashes around.
 */
export function Code({ code, className, ref, ...rest }: CodeProps) {
  return (
    <bdi {...rest} ref={ref} dir="ltr">
      <code className={cx(styles.code, className)}>{String(code)}</code>
    </bdi>
  );
}

export type MoneyProps = Omit<React.HTMLAttributes<HTMLElement>, "children"> & {
  /** Integer rials, as stored and transported. */
  rial: number;
  /** Display unit; default toman (what people say), rial for finance screens. */
  unit?: MoneyUnit;
  ref?: React.Ref<HTMLElement>;
};

/** 120000 rial → "۱۲٬۰۰۰ تومان". The conversion lives in one place so no screen divides by ten itself. */
export function Money({ rial, unit = "toman", className, ref, ...rest }: MoneyProps) {
  return (
    <bdi {...rest} ref={ref} className={cx(styles.money, className)}>
      {formatMoney(rial, unit)}
    </bdi>
  );
}

export type PointsProps = Omit<React.HTMLAttributes<HTMLElement>, "children"> & {
  value: number;
  signed?: boolean;
  /** Append «امتیاز». Default true. */
  unit?: boolean;
  ref?: React.Ref<HTMLElement>;
};

/** Points in the reward colour: "۱٬۲۰۰ امتیاز", or "+۳۰ امتیاز" when signed. */
export function Points({ value, signed, unit = true, className, ref, ...rest }: PointsProps) {
  return (
    <bdi {...rest} ref={ref} className={cx(styles.points, className)}>
      {formatPoints(value, { signed, unit })}
    </bdi>
  );
}
