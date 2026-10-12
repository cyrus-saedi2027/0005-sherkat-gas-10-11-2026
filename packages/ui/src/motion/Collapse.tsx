/* ─────────────────────────────────────────────────────────────
 *  Collapse — animate height to and from `auto`.
 *
 *  CSS cannot transition to `height: auto`, so a spring carries a 0..1
 *  progress and the writer multiplies it by the content height measured
 *  at the start of each transition. At rest open the height goes back
 *  to `auto`, so content that grows later (an error line, a loaded
 *  list) is not clipped to a stale number.
 *
 *  MOTION.swipe (ζ≈0.94): a height that overshoots shows a blank strip
 *  under the content, so this wants near-critical damping; the
 *  Math.max(0, …) clamp covers the tiny undershoot when closing.
 * ───────────────────────────────────────────────────────────── */

import * as React from "react";
import { MOTION, type MotionPreset } from "@gazyar/motion";
import { cx } from "../lib/cx";
import { useMergedRefs } from "../lib/refs";
import { useSpringBind, useSpringRef } from "./hooks";
import styles from "./motion.module.css";

export type CollapseProps = React.HTMLAttributes<HTMLDivElement> & {
  open: boolean;
  preset?: MotionPreset;
  /** Fires after the open/close animation settles. */
  onRest?: (open: boolean) => void;
  ref?: React.Ref<HTMLDivElement>;
};

export function Collapse({ open, preset = "swipe", onRest, className, children, ref, ...rest }: CollapseProps) {
  const spring = useSpringRef(open ? 1 : 0, MOTION[preset]);
  const inner = React.useRef<HTMLDivElement | null>(null);
  const height = React.useRef(0);
  const onRestRef = React.useRef(onRest);
  React.useLayoutEffect(() => {
    onRestRef.current = onRest;
  });

  const bind = useSpringBind<HTMLDivElement>(spring, (el, x) => {
    const resting = !spring.isMoving;
    if (resting && x >= 1) el.style.height = "";
    else el.style.height = `${(Math.max(0, x) * height.current).toFixed(2)}px`;
    // Closed content leaves the tab order and the accessibility tree.
    el.toggleAttribute("inert", resting && x <= 0);
  });
  const setRef = useMergedRefs(bind, ref);

  const first = React.useRef(true);
  React.useLayoutEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    height.current = inner.current?.offsetHeight ?? 0;
    spring.springTo(open ? 1 : 0, spring.v, () => onRestRef.current?.(open));
  }, [open, spring]);

  return (
    <div {...rest} ref={setRef} className={cx(styles.collapse, className)} data-open={open || undefined}>
      <div ref={inner} className={styles.collapseInner}>
        {children}
      </div>
    </div>
  );
}
