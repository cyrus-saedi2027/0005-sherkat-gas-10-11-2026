/* ─────────────────────────────────────────────────────────────
 *  Pressable — press feedback for everything tappable.
 *
 *  The load-bearing detail: the release listener is on `window`, not
 *  on the element. When a parent grabs the pointer — a tab pan, a row
 *  swipe, a sheet drag — the child never receives its own pointerup
 *  and stays visually pressed forever. Listening on window is the fix.
 *
 *  Pressed state is a `data-pressed` attribute written straight to the
 *  node, not React state: pressing a row in a 20-row list costs zero
 *  renders, and the CSS transition does the scale.
 * ───────────────────────────────────────────────────────────── */

import * as React from "react";
import { cx } from "../lib/cx";
import { fireHaptic, type HapticKind } from "../lib/haptics";
import styles from "./primitives.module.css";

/** How far it sinks on press: subtle 0.985 (rows, cards), normal 0.955, firm 0.94 (chips, small icons). */
export type PressDepth = "none" | "subtle" | "normal" | "firm";

type Tag = "button" | "a" | "div" | "span" | "li" | "label";

export type PressableProps = Omit<React.HTMLAttributes<HTMLElement>, "onClick"> & {
  as?: Tag;
  /** Native button type; default "button" so a Pressable never submits a form by accident. */
  type?: "button" | "submit" | "reset";
  href?: string;
  target?: string;
  rel?: string;
  disabled?: boolean;
  onPress?: (e: React.MouseEvent<HTMLElement>) => void;
  onClick?: (e: React.MouseEvent<HTMLElement>) => void;
  press?: PressDepth;
  /** Haptic on press-down. Default "tap" when there is an onPress, otherwise none. */
  haptic?: HapticKind | false;
  ref?: React.Ref<HTMLElement>;
};

export function Pressable({
  as = "button",
  type = "button",
  disabled = false,
  onPress,
  onClick,
  onPointerDown,
  onKeyDown,
  onKeyUp,
  press = "normal",
  haptic,
  className,
  role,
  tabIndex,
  ref,
  children,
  ...rest
}: PressableProps) {
  const interactive = !!onPress || as === "button" || (as === "a" && !!rest.href);
  const hapticKind: HapticKind | false = haptic ?? (onPress ? "tap" : false);

  const handlePointerDown = (e: React.PointerEvent<HTMLElement>) => {
    onPointerDown?.(e);
    if (disabled || e.defaultPrevented || !interactive) return;
    if (e.pointerType === "mouse" && e.button !== 0) return;
    const el = e.currentTarget;
    if (press !== "none") el.setAttribute("data-pressed", "");
    const release = () => {
      el.removeAttribute("data-pressed");
      window.removeEventListener("pointerup", release);
      window.removeEventListener("pointercancel", release);
    };
    window.addEventListener("pointerup", release);
    window.addEventListener("pointercancel", release);
    if (hapticKind) fireHaptic(hapticKind);
  };

  const handleClick = (e: React.MouseEvent<HTMLElement>) => {
    onClick?.(e);
    if (disabled) {
      e.preventDefault();
      return;
    }
    if (!e.defaultPrevented) onPress?.(e);
  };

  // Non-button hosts with an onPress get button semantics and keys,
  // otherwise keyboard and screen-reader users cannot activate them.
  const fakeButton = !!onPress && as !== "button" && !(as === "a" && rest.href);
  const handleKeyDown = (e: React.KeyboardEvent<HTMLElement>) => {
    onKeyDown?.(e);
    if (!fakeButton || disabled || e.defaultPrevented) return;
    if (e.key === "Enter") {
      e.preventDefault();
      e.currentTarget.click();
    } else if (e.key === " ") {
      e.preventDefault(); // stop the page from scrolling; activate on keyup like a button
    }
  };
  const handleKeyUp = (e: React.KeyboardEvent<HTMLElement>) => {
    onKeyUp?.(e);
    if (fakeButton && !disabled && !e.defaultPrevented && e.key === " ") e.currentTarget.click();
  };

  const props: Record<string, unknown> = {
    ...rest,
    ref,
    className: cx(styles.pressable, !interactive && styles.static, className),
    "data-press": press,
    role: role ?? (fakeButton ? "button" : undefined),
    tabIndex: tabIndex ?? (fakeButton ? (disabled ? -1 : 0) : undefined),
    onPointerDown: handlePointerDown,
    onClick: handleClick,
    onKeyDown: handleKeyDown,
    onKeyUp: handleKeyUp,
  };
  if (as === "button") {
    props.type = type;
    props.disabled = disabled;
  } else if (disabled) {
    props["aria-disabled"] = true;
  }

  return React.createElement(as, props, children);
}
