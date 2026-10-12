import * as React from "react";
import { cx } from "../lib/cx";
import { SELECT } from "../lib/haptics";
import { useMergedRefs } from "../lib/refs";
import { useControllable } from "../lib/useControllable";
import styles from "./Choice.module.css";

type NativeInput = Omit<React.InputHTMLAttributes<HTMLInputElement>, "type" | "children">;

/* ── Checkbox ──────────────────────────────────────────────── */

export type CheckboxProps = NativeInput & {
  label?: React.ReactNode;
  description?: React.ReactNode;
  /** Shows a dash; announced as "mixed". Set on the "select all" box. */
  indeterminate?: boolean;
  onCheckedChange?: (checked: boolean) => void;
  ref?: React.Ref<HTMLInputElement>;
};

export function Checkbox({
  label,
  description,
  indeterminate = false,
  onCheckedChange,
  onChange,
  className,
  disabled,
  ref,
  ...rest
}: CheckboxProps) {
  const input = React.useRef<HTMLInputElement | null>(null);
  const setRef = useMergedRefs(input, ref);
  // `indeterminate` is a DOM property with no attribute: React cannot set it.
  React.useLayoutEffect(() => {
    if (input.current) input.current.indeterminate = indeterminate;
  }, [indeterminate]);

  return (
    <label className={cx(styles.choice, className)} data-disabled={disabled || undefined}>
      <input
        {...rest}
        ref={setRef}
        type="checkbox"
        disabled={disabled}
        className={cx(styles.control, styles.checkbox)}
        onChange={(e) => {
          onChange?.(e);
          SELECT();
          onCheckedChange?.(e.currentTarget.checked);
        }}
      />
      {label || description ? (
        <span className={styles.text}>
          {label ? <span className={styles.label}>{label}</span> : null}
          {description ? <span className={styles.description}>{description}</span> : null}
        </span>
      ) : null}
    </label>
  );
}

/* ── Radio / RadioGroup ────────────────────────────────────── */

type GroupCtx = {
  name: string;
  value: string;
  setValue: (v: string) => void;
  disabled?: boolean;
};

const RadioGroupContext = React.createContext<GroupCtx | null>(null);

export type RadioProps = Omit<NativeInput, "value" | "name"> & {
  value: string;
  label?: React.ReactNode;
  description?: React.ReactNode;
  ref?: React.Ref<HTMLInputElement>;
};

/** One option. Inside a RadioGroup it takes name/checked/onChange from the group. */
export function Radio({ value, label, description, className, disabled, onChange, ref, ...rest }: RadioProps) {
  const group = React.useContext(RadioGroupContext);
  const isDisabled = disabled ?? group?.disabled;
  return (
    <label className={cx(styles.choice, className)} data-disabled={isDisabled || undefined}>
      <input
        {...rest}
        ref={ref}
        type="radio"
        value={value}
        name={group?.name}
        checked={group ? group.value === value : rest.checked}
        disabled={isDisabled}
        className={cx(styles.control, styles.radio)}
        onChange={(e) => {
          onChange?.(e);
          if (e.currentTarget.checked) {
            SELECT();
            group?.setValue(value);
          }
        }}
      />
      {label || description ? (
        <span className={styles.text}>
          {label ? <span className={styles.label}>{label}</span> : null}
          {description ? <span className={styles.description}>{description}</span> : null}
        </span>
      ) : null}
    </label>
  );
}

export type RadioGroupProps = Omit<React.FieldsetHTMLAttributes<HTMLFieldSetElement>, "onChange" | "defaultValue"> & {
  legend?: React.ReactNode;
  value?: string;
  defaultValue?: string;
  onValueChange?: (value: string) => void;
  /** Shortcut for simple lists; or pass <Radio> children. */
  options?: readonly { value: string; label: React.ReactNode; description?: React.ReactNode; disabled?: boolean }[];
  orientation?: "vertical" | "horizontal";
  error?: React.ReactNode;
  name?: string;
  ref?: React.Ref<HTMLFieldSetElement>;
};

/**
 * Native radios in a fieldset: arrow keys, one tab stop and form
 * submission all come from the browser — and arrows follow `dir`, so
 * RTL needs no key handling here.
 */
export function RadioGroup({
  legend,
  value: valueProp,
  defaultValue = "",
  onValueChange,
  options,
  orientation = "vertical",
  error,
  name,
  disabled,
  className,
  children,
  ref,
  ...rest
}: RadioGroupProps) {
  const autoName = React.useId();
  const [value, setValue] = useControllable(valueProp, defaultValue, onValueChange);
  const errorId = `${autoName}-error`;
  const ctx = React.useMemo<GroupCtx>(
    () => ({ name: name ?? autoName, value, setValue, disabled }),
    [name, autoName, value, setValue, disabled],
  );
  return (
    <fieldset
      {...rest}
      ref={ref}
      disabled={disabled}
      role="radiogroup"
      aria-invalid={error ? true : undefined}
      aria-describedby={error ? errorId : undefined}
      className={cx(styles.group, className)}
    >
      {legend ? <legend className={styles.legend}>{legend}</legend> : null}
      <RadioGroupContext.Provider value={ctx}>
        <div className={styles.options} data-orientation={orientation}>
          {options?.map((o) => (
            <Radio key={o.value} value={o.value} label={o.label} description={o.description} disabled={o.disabled} />
          ))}
          {children}
        </div>
      </RadioGroupContext.Provider>
      {error && error !== true ? (
        <div className={styles.groupError} id={errorId} role="alert">
          {error}
        </div>
      ) : null}
    </fieldset>
  );
}
