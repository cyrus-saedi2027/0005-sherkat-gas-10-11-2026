/* ─────────────────────────────────────────────────────────────
 *  FocusTrap — keeps Tab inside a dialog or sheet while it is open
 *  and hands focus back to whatever opened it when it closes.
 *
 *  Without the restore, closing a sheet with the keyboard (or a
 *  screen reader) drops focus on <body>: the user is thrown back to
 *  the top of the page and has to find their place again.
 * ───────────────────────────────────────────────────────────── */

import * as React from "react";
import { cx } from "../lib/cx";
import { useMergedRefs } from "../lib/refs";
import styles from "./primitives.module.css";

const FOCUSABLE = [
  "a[href]",
  "area[href]",
  "button:not([disabled])",
  "input:not([disabled]):not([type='hidden'])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "iframe",
  "audio[controls]",
  "video[controls]",
  "[contenteditable]:not([contenteditable='false'])",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

/** Tabbable descendants in DOM order, skipping inert/hidden subtrees. */
export function getTabbables(root: HTMLElement): HTMLElement[] {
  return Array.from(root.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
    (el) => !el.closest("[inert]") && !el.closest("[hidden]") && el.getAttribute("aria-hidden") !== "true",
  );
}

export type FocusTrapProps = React.HTMLAttributes<HTMLDivElement> & {
  /** Trap only while true (e.g. while the sheet is open). Default true. */
  active?: boolean;
  /** Element to focus on activation; default: first tabbable, else the container. */
  initialFocus?: React.RefObject<HTMLElement | null>;
  /** Return focus to the previously focused element on deactivation. Default true. */
  restoreFocus?: boolean;
  ref?: React.Ref<HTMLDivElement>;
};

export function FocusTrap({
  active = true,
  initialFocus,
  restoreFocus = true,
  children,
  onKeyDown,
  className,
  ref,
  ...rest
}: FocusTrapProps) {
  const box = React.useRef<HTMLDivElement | null>(null);
  const setRef = useMergedRefs(box, ref);

  React.useEffect(() => {
    if (!active) return;
    const root = box.current;
    if (!root) return;
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;

    if (!root.contains(document.activeElement)) {
      const target = initialFocus?.current ?? getTabbables(root)[0] ?? root;
      target.focus({ preventScroll: true });
    }

    return () => {
      // Only restore if focus is still inside (or was lost to <body>):
      // if the user already moved on, yanking focus back is worse.
      const now = document.activeElement;
      const lost = !now || now === document.body || root.contains(now);
      if (restoreFocus && lost && previous && previous.isConnected) previous.focus({ preventScroll: true });
    };
  }, [active, initialFocus, restoreFocus]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    onKeyDown?.(e);
    if (!active || e.defaultPrevented || e.key !== "Tab") return;
    const root = box.current;
    if (!root) return;
    const items = getTabbables(root);
    if (items.length === 0) {
      e.preventDefault();
      root.focus();
      return;
    }
    const first = items[0]!;
    const last = items[items.length - 1]!;
    const current = document.activeElement;
    if (e.shiftKey && (current === first || current === root)) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && current === last) {
      e.preventDefault();
      first.focus();
    }
  };

  return (
    <div {...rest} ref={setRef} tabIndex={-1} className={cx(styles.trap, className)} onKeyDown={handleKeyDown}>
      {children}
    </div>
  );
}
