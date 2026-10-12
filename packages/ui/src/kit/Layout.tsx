/* ─────────────────────────────────────────────────────────────
 *  Layout helpers — Stack (vertical), Inline (horizontal), Divider.
 *
 *  Spacing between siblings belongs to the parent, as `gap`, never to
 *  the children as margins: a margin on the last row of a card shows
 *  up as a lopsided bottom padding, and a margin-left written for LTR
 *  ends up on the wrong side in RTL. Gaps come from the SPACE scale
 *  (a step, not a pixel value) so screens cannot drift to 13px/15px.
 *
 *  The step is a data attribute matched by the CSS module, not an
 *  inline style: inline styles in this package are reserved for values
 *  a spring writes every frame.
 * ───────────────────────────────────────────────────────────── */

import * as React from "react";
import { cx } from "../lib/cx";
import type { SpaceStep } from "../tokens";
import styles from "./Layout.module.css";

type LayoutTag = "div" | "section" | "article" | "header" | "footer" | "main" | "nav" | "aside" | "ul" | "ol" | "li" | "form" | "fieldset" | "span";

type Align = "start" | "center" | "end" | "stretch" | "baseline";
type Justify = "start" | "center" | "end" | "between";

type LayoutProps = React.HTMLAttributes<HTMLElement> & {
  as?: LayoutTag;
  /** Gap as a SPACE step: 3 → 12px, 4 → 16px. */
  gap?: SpaceStep;
  align?: Align;
  justify?: Justify;
  ref?: React.Ref<HTMLElement>;
};

export type StackProps = LayoutProps;

/** Children top to bottom with a uniform gap. Default gap 3 (12px), children stretch. */
export function Stack({ as = "div", gap = 3, align, justify, className, ref, ...rest }: StackProps) {
  return React.createElement(as, {
    ...rest,
    ref,
    "data-gap": gap,
    "data-align": align,
    "data-justify": justify,
    className: cx(styles.stack, className),
  });
}

export type InlineProps = LayoutProps & {
  /** Wrap onto more lines when there is no room (default true): a row of chips on a phone. */
  wrap?: boolean;
};

/**
 * Children along the reading direction (right to left in RTL) with a
 * uniform gap. Default gap 2 (8px), vertically centred.
 */
export function Inline({ as = "div", gap = 2, align = "center", justify, wrap = true, className, ref, ...rest }: InlineProps) {
  return React.createElement(as, {
    ...rest,
    ref,
    "data-gap": gap,
    "data-align": align,
    "data-justify": justify,
    "data-nowrap": wrap ? undefined : "",
    className: cx(styles.inline, className),
  });
}

export type DividerProps = Omit<React.HTMLAttributes<HTMLElement>, "children"> & {
  orientation?: "horizontal" | "vertical";
  /** Text in the middle of a horizontal divider, e.g. «یا». */
  label?: React.ReactNode;
  /** Indent from the inline-start, px — lines up with text after a row's icon square. */
  inset?: 0 | 16 | 66;
  /** Space above and below (horizontal) as a SPACE step. Default 0. */
  spacing?: SpaceStep;
  ref?: React.Ref<HTMLElement>;
};

/**
 * A hairline separator. Plain dividers are exposed as role="separator";
 * a labelled one is a decorative pair of lines around readable text.
 */
export function Divider({ orientation = "horizontal", label, inset = 0, spacing = 0, className, ref, ...rest }: DividerProps) {
  if (label != null && orientation === "horizontal") {
    return (
      <div {...rest} ref={ref as React.Ref<HTMLDivElement>} data-spacing={spacing} className={cx(styles.labelled, className)}>
        <span className={styles.line} aria-hidden="true" />
        <span className={styles.label}>{label}</span>
        <span className={styles.line} aria-hidden="true" />
      </div>
    );
  }
  return (
    <div
      {...rest}
      ref={ref as React.Ref<HTMLDivElement>}
      role="separator"
      aria-orientation={orientation}
      data-inset={inset || undefined}
      data-spacing={spacing}
      className={cx(styles.divider, orientation === "vertical" && styles.vertical, className)}
    />
  );
}

export type SpacerProps = { ref?: React.Ref<HTMLSpanElement> };

/** Takes the free space in an Inline/Toolbar, pushing what follows to the inline-end. */
export function Spacer({ ref }: SpacerProps) {
  return <span ref={ref} className={styles.spacer} aria-hidden="true" />;
}
