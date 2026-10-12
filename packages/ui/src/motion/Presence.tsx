/* ─────────────────────────────────────────────────────────────
 *  Presence — mount/unmount with an exit animation.
 *
 *  React removes a node the instant its condition turns false, so an
 *  exit animation needs something that keeps it mounted until the
 *  animation finishes. Here a 0..1 spring carries the transition and
 *  its onRest unmounts. Because the engine still fires onRest under
 *  reduced motion (after jumping to the target), the unmount happens
 *  either way — nothing leaks when animations are off.
 * ───────────────────────────────────────────────────────────── */

import * as React from "react";
import { MOTION, type MotionPreset } from "@gazyar/motion";
import { cx } from "../lib/cx";
import { useMergedRefs } from "../lib/refs";
import { useSpringBind, useSpringRef } from "./hooks";
import styles from "./motion.module.css";

export type PresenceVariant = "fade" | "up" | "down" | "scale";

export type PresenceProps = Omit<React.HTMLAttributes<HTMLDivElement>, "children"> & {
  show: boolean;
  children?: React.ReactNode;
  variant?: PresenceVariant;
  /** Spring preset. Default "flight" (ζ≈0.84). */
  preset?: MotionPreset;
  /** Animate the first mount too. Default true. */
  appear?: boolean;
  /** Called once the exit animation has finished and children are gone. */
  onExited?: () => void;
  ref?: React.Ref<HTMLDivElement>;
};

/** Travel for the slide variants, px. */
const TRAVEL = 12;

function writer(variant: PresenceVariant) {
  return (el: HTMLElement, x: number) => {
    const p = Math.min(1, Math.max(0, x));
    el.style.opacity = p >= 1 ? "" : p.toFixed(3);
    let t = "";
    if (variant === "up") t = `translate3d(0,${((1 - x) * TRAVEL).toFixed(2)}px,0)`;
    else if (variant === "down") t = `translate3d(0,${((x - 1) * TRAVEL).toFixed(2)}px,0)`;
    else if (variant === "scale") t = `scale(${(0.94 + 0.06 * x).toFixed(4)})`;
    // At rest drop the transform: a lingering identity transform still
    // creates a stacking context and traps fixed-position children.
    el.style.transform = x === 1 ? "" : t;
  };
}

export function Presence({
  show,
  children,
  variant = "up",
  preset = "flight",
  appear = true,
  onExited,
  className,
  ref,
  ...rest
}: PresenceProps) {
  const [mounted, setMounted] = React.useState(show);
  // "Adjust state while rendering": mount in the same pass `show` turns
  // true, so the effect below already has a node to animate.
  if (show && !mounted) setMounted(true);

  const spring = useSpringRef(show && !appear ? 1 : 0, MOTION[preset]);
  const onExitedRef = React.useRef(onExited);
  React.useLayoutEffect(() => {
    onExitedRef.current = onExited;
  });

  const bind = useSpringBind<HTMLDivElement>(spring, writer(variant));
  const setRef = useMergedRefs(bind, ref);

  React.useLayoutEffect(() => {
    if (show) {
      spring.springTo(1, spring.v);
      return;
    }
    // Hidden and already at rest at 0 (e.g. first mount with show=false):
    // nothing is exiting, so no onExited either.
    if (spring.x === 0 && !spring.isMoving) return;
    spring.springTo(0, spring.v, () => {
      setMounted(false);
      onExitedRef.current?.();
    });
  }, [show, spring]);

  if (!mounted) return null;
  return (
    <div
      {...rest}
      ref={setRef}
      className={cx(styles.presence, className)}
      data-state={show ? "entered" : "exiting"}
      aria-hidden={show ? rest["aria-hidden"] : true}
    >
      {children}
    </div>
  );
}
