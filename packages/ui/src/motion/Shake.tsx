/* ─────────────────────────────────────────────────────────────
 *  Shake — horizontal error shake, spring-driven.
 *
 *  A spring at rest at 0 is kicked with an initial velocity; MOTION.
 *  shake is strongly underdamped (ζ≈0.23), so it swings 3–4 times and
 *  dies out in ≈0.6s. Kicking again mid-shake adds to the motion
 *  instead of snapping back to zero the way a restarted CSS keyframe
 *  does on a double submit. Symmetric, so RTL needs no
 *  mirroring. Under reduced motion it does nothing visible — the error
 *  text and the haptic still carry the message.
 * ───────────────────────────────────────────────────────────── */

import * as React from "react";
import { MOTION } from "@gazyar/motion";
import { cx } from "../lib/cx";
import { WARN } from "../lib/haptics";
import { useSpringBind, useSpringRef } from "./hooks";
import styles from "./motion.module.css";

/** Initial velocity, px/s — ≈10px of travel with MOTION.shake. */
export const SHAKE_V0 = 260;

export type ShakeHandle = { shake: () => void };

/** Imperative shake for any element: `const s = useShake(); <div ref={s.ref}/>; s.shake()`. */
export function useShake<T extends HTMLElement = HTMLDivElement>(opts: { haptic?: boolean } = {}) {
  const { haptic = true } = opts;
  const spring = useSpringRef(0, MOTION.shake);
  const ref = useSpringBind<T>(spring, (el, x) => {
    el.style.transform = x === 0 ? "" : `translate3d(${x.toFixed(2)}px,0,0)`;
  });
  const shake = React.useCallback(() => {
    if (haptic) WARN();
    spring.springTo(0, spring.v + SHAKE_V0);
  }, [spring, haptic]);
  return { ref, shake };
}

export type ShakeProps = React.HTMLAttributes<HTMLDivElement> & {
  /** Shakes whenever this value changes to something truthy (e.g. an error message or a submit count). */
  trigger?: unknown;
  haptic?: boolean;
  ref?: React.Ref<ShakeHandle>;
};

export function Shake({ trigger, haptic = true, className, ref, ...rest }: ShakeProps) {
  const { ref: bind, shake } = useShake<HTMLDivElement>({ haptic });
  React.useImperativeHandle(ref, () => ({ shake }), [shake]);

  const prev = React.useRef(trigger);
  React.useEffect(() => {
    if (trigger !== prev.current && trigger) shake();
    prev.current = trigger;
  }, [trigger, shake]);

  return <div {...rest} ref={bind} className={cx(styles.shake, className)} />;
}
