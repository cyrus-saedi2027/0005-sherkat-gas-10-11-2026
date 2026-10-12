/* ─────────────────────────────────────────────────────────────
 *  Toolbar — a row of controls above a list or table: a title at the
 *  inline-start, filters/search in the middle, actions at the
 *  inline-end. Wraps onto more lines on a phone instead of scrolling
 *  sideways (a sideways-scrolling toolbar hides its primary action).
 *
 *  Keyboard: every control stays in the Tab order, and ←/→ (in
 *  reading direction) plus Home/End also move between them. The
 *  WAI-ARIA pattern's single tab stop is deliberately not used: admin
 *  toolbars mix a search field with buttons, and a search field only
 *  reachable by arrow keys is invisible to most keyboard users. Arrows
 *  are left alone inside text fields and selects, where they edit.
 * ───────────────────────────────────────────────────────────── */

import * as React from "react";
import { cx } from "../lib/cx";
import { isRtl, useMergedRefs } from "../lib/refs";
import { getTabbables } from "../primitives/FocusTrap";
import styles from "./Toolbar.module.css";

export type ToolbarProps = Omit<React.HTMLAttributes<HTMLDivElement>, "title"> & {
  /** Accessible name — required: a page often has more than one toolbar. */
  label: string;
  /** Heading at the inline-start (an admin page title, a section name). */
  title?: React.ReactNode;
  /** Controls at the inline-end — the primary action goes last. */
  actions?: React.ReactNode;
  /** "bar": a surface with a hairline (page headers); "plain": layout only. Default "plain". */
  variant?: "plain" | "bar";
  /** Stick to the top of the scroll container while the list scrolls under it. */
  sticky?: boolean;
  ref?: React.Ref<HTMLDivElement>;
};

/** Controls where ←/→/Home/End edit text or pick an option, so the toolbar must not steal them. */
function ownsArrowKeys(el: Element | null): boolean {
  if (!el) return false;
  if (el instanceof HTMLTextAreaElement || el instanceof HTMLSelectElement) return true;
  if (el instanceof HTMLInputElement) {
    return !["button", "submit", "reset", "checkbox", "radio", "file", "image", "color"].includes(el.type);
  }
  return el instanceof HTMLElement && el.isContentEditable;
}

export function Toolbar({
  label,
  title,
  actions,
  variant = "plain",
  sticky,
  className,
  children,
  onKeyDown,
  ref,
  ...rest
}: ToolbarProps) {
  const box = React.useRef<HTMLDivElement | null>(null);
  const setRef = useMergedRefs(box, ref);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    onKeyDown?.(e);
    if (e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey) return;
    const root = box.current;
    if (!root || ownsArrowKeys(e.target as Element)) return;

    const rtl = isRtl(root);
    let dir: "next" | "prev" | "first" | "last" | null = null;
    if (e.key === "ArrowRight") dir = rtl ? "prev" : "next";
    else if (e.key === "ArrowLeft") dir = rtl ? "next" : "prev";
    else if (e.key === "Home") dir = "first";
    else if (e.key === "End") dir = "last";
    if (!dir) return;

    const items = getTabbables(root);
    if (items.length === 0) return;
    const at = items.indexOf(document.activeElement as HTMLElement);
    let next: number;
    if (dir === "first") next = 0;
    else if (dir === "last") next = items.length - 1;
    else if (at < 0) next = 0;
    // No wrap-around: hitting the end and stopping tells the user where
    // the toolbar ends; wrapping silently looks like nothing happened.
    else next = Math.min(items.length - 1, Math.max(0, at + (dir === "next" ? 1 : -1)));
    e.preventDefault();
    items[next]?.focus();
  };

  return (
    <div
      {...rest}
      ref={setRef}
      role="toolbar"
      aria-label={label}
      aria-orientation="horizontal"
      data-variant={variant}
      data-sticky={sticky || undefined}
      onKeyDown={handleKeyDown}
      className={cx(styles.toolbar, className)}
    >
      {title != null ? <div className={styles.title}>{title}</div> : null}
      {children != null ? <div className={styles.main}>{children}</div> : null}
      {actions != null ? <div className={styles.actions}>{actions}</div> : null}
    </div>
  );
}
