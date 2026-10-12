import * as React from "react";
import { MOTION } from "@gazyar/motion";
import { cx } from "../lib/cx";
import { SELECT } from "../lib/haptics";
import { isRtl } from "../lib/refs";
import { useControllable } from "../lib/useControllable";
import { useSpringBind, useSpringRef } from "../motion/hooks";
import { Pressable } from "../primitives/Pressable";
import styles from "./Switch.module.css";

export type SwitchProps = Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "onChange" | "value" | "onClick"> & {
  checked?: boolean;
  defaultChecked?: boolean;
  onCheckedChange?: (checked: boolean) => void;
  /** Visible label to the inline-start of the switch; becomes its accessible name. */
  label?: React.ReactNode;
  description?: React.ReactNode;
  size?: "sm" | "md";
  ref?: React.Ref<HTMLButtonElement>;
};

/** Knob travel, px: track − knob − 2×padding. */
const TRAVEL = { md: 44 - 20 - 6, sm: 36 - 16 - 6 } as const;

/**
 * On/off switch (role="switch", aria-checked). The knob rides the
 * `thumb` spring (ζ≈0.75: one small overshoot so it feels physical),
 * written straight to the DOM. Tapping again mid-travel reverses from
 * where the knob is, with its velocity — no restart from the end.
 */
export function Switch({
  checked: checkedProp,
  defaultChecked = false,
  onCheckedChange,
  label,
  description,
  size = "md",
  disabled,
  className,
  id: idProp,
  ref,
  ...rest
}: SwitchProps) {
  const [checked, setChecked] = useControllable(checkedProp, defaultChecked, onCheckedChange);
  const autoId = React.useId();
  const id = idProp ?? autoId;
  const spring = useSpringRef(checked ? 1 : 0, MOTION.thumb);
  // Direction is read once per node: transforms do not mirror with `dir`.
  const sign = React.useRef<number | null>(null);
  const knob = useSpringBind<HTMLSpanElement>(spring, (el, x) => {
    sign.current ??= isRtl(el) ? -1 : 1;
    el.style.transform = `translate3d(${(sign.current * x * TRAVEL[size]).toFixed(2)}px,0,0)`;
  });

  React.useEffect(() => {
    spring.springTo(checked ? 1 : 0, spring.v);
  }, [checked, spring]);

  const labelId = `${id}-label`;
  const descId = `${id}-desc`;

  const control = (
    <Pressable
      {...(rest as Omit<React.HTMLAttributes<HTMLElement>, "onClick">)}
      as="button"
      ref={ref as React.Ref<HTMLElement>}
      id={id}
      role="switch"
      aria-checked={checked}
      aria-labelledby={label ? labelId : rest["aria-labelledby"]}
      aria-describedby={description ? descId : rest["aria-describedby"]}
      disabled={disabled}
      press="firm"
      haptic={false}
      onPress={() => {
        SELECT();
        setChecked(!checked);
      }}
      className={cx(styles.switch, size === "sm" && styles.sm, !label && className)}
    >
      <span className={styles.track} aria-hidden="true">
        <span ref={knob} className={styles.knob} />
      </span>
    </Pressable>
  );

  if (!label && !description) return control;
  return (
    <div className={cx(styles.row, className)}>
      <span className={styles.text} onClick={() => !disabled && setChecked(!checked)}>
        {label ? (
          <span id={labelId} className={styles.label}>
            {label}
          </span>
        ) : null}
        {description ? (
          <span id={descId} className={styles.description}>
            {description}
          </span>
        ) : null}
      </span>
      {control}
    </div>
  );
}
