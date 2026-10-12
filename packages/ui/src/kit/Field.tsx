/* ─────────────────────────────────────────────────────────────
 *  Text inputs: TextField, TextArea, Select — one shell, one look.
 *
 *  Values are strings in, strings out through `onValueChange`; the
 *  native `onChange` still passes through for form libraries.
 *
 *  `digits`: people type with whichever keyboard is up — Persian (۰-۹),
 *  Arabic-Indic (٠-٩) or ASCII. The value handed to the app is ASCII
 *  (what the backend compares and stores), while the field keeps
 *  showing exactly what was typed: replacing ۱۲ with 12 under the
 *  user's thumb reads as the app "changing my number".
 * ───────────────────────────────────────────────────────────── */

import * as React from "react";
import { cx } from "../lib/cx";
import { toEn } from "../lib/digits";
import { useMergedRefs } from "../lib/refs";
import { useControllable } from "../lib/useControllable";
import { Icon } from "../icons";
import { useShake } from "../motion/Shake";
import styles from "./Field.module.css";

type ShellProps = {
  id: string;
  label?: React.ReactNode;
  hint?: React.ReactNode;
  error?: React.ReactNode;
  required?: boolean;
  className?: string;
  children: React.ReactNode;
};

const hintId = (id: string) => `${id}-hint`;
const errorId = (id: string) => `${id}-error`;

/** Label above, hint/error below. The error replaces the hint (two lines of grey + red read as noise). */
function FieldShell({ id, label, hint, error, required, className, children }: ShellProps) {
  const hasError = error != null && error !== false && error !== true && error !== "";
  return (
    <div className={cx(styles.field, className)}>
      {label ? (
        <label className={styles.label} htmlFor={id}>
          {label}
          {required ? (
            <span className={styles.required} aria-hidden="true">
              *
            </span>
          ) : null}
        </label>
      ) : null}
      {children}
      {hasError ? (
        <div className={styles.error} id={errorId(id)} role="alert">
          <Icon.alert size={14} stroke={2.2} />
          <span>{error}</span>
        </div>
      ) : hint ? (
        <div className={styles.hint} id={hintId(id)}>
          {hint}
        </div>
      ) : null}
    </div>
  );
}

function describedBy(id: string, hint: unknown, error: unknown, extra?: string): string | undefined {
  const hasError = error != null && error !== false && error !== true && error !== "";
  const ids = [hasError ? errorId(id) : hint ? hintId(id) : null, extra].filter(Boolean);
  return ids.length ? ids.join(" ") : undefined;
}

/** Shake the box when an error appears or changes (not on every render). */
function useErrorShake(error: unknown) {
  const { ref, shake } = useShake<HTMLDivElement>();
  const prev = React.useRef(error);
  React.useEffect(() => {
    if (error && error !== prev.current) shake();
    prev.current = error;
  }, [error, shake]);
  return ref;
}

/* ── TextField ─────────────────────────────────────────────── */

type NativeInput = Omit<
  React.InputHTMLAttributes<HTMLInputElement>,
  "value" | "defaultValue" | "prefix" | "size" | "children"
>;

export type TextFieldProps = NativeInput & {
  label?: React.ReactNode;
  hint?: React.ReactNode;
  /** A message (shown, announced, shakes the field) or `true` for invalid styling only. */
  error?: React.ReactNode;
  value?: string;
  defaultValue?: string;
  /** Receives the normalised value (ASCII digits when `digits`). */
  onValueChange?: (value: string) => void;
  /** Content at the inline-start inside the box (e.g. an icon, "+98"). */
  prefix?: React.ReactNode;
  /** Content at the inline-end inside the box (e.g. a unit, "m³"). */
  suffix?: React.ReactNode;
  /** Latin / number field (mobile, IBAN, code): LTR caret and alignment. */
  ltr?: boolean;
  /** Normalise Persian/Arabic digits to ASCII in the value; display stays as typed. */
  digits?: boolean;
  /** Show a clear button when there is a value. */
  clearable?: boolean;
  /** Class for the outer wrapper (layout); the input itself is styled by the kit. */
  className?: string;
  inputClassName?: string;
  ref?: React.Ref<HTMLInputElement>;
};

export function TextField({
  label,
  hint,
  error,
  value: valueProp,
  defaultValue = "",
  onValueChange,
  onChange,
  prefix,
  suffix,
  ltr,
  digits,
  clearable,
  className,
  inputClassName,
  type = "text",
  inputMode,
  id: idProp,
  disabled,
  readOnly,
  required,
  ref,
  ...rest
}: TextFieldProps) {
  const autoId = React.useId();
  const id = idProp ?? autoId;
  const [value, setValue] = useControllable(valueProp, defaultValue, onValueChange);
  const normalise = React.useCallback((s: string) => (digits ? toEn(s) : s), [digits]);

  // What the user typed. Shown while it still normalises to the current
  // value; an external change (reset, prefill) wins otherwise.
  const [typed, setTyped] = React.useState(value);
  const shown = normalise(typed) === value ? typed : value;

  const [reveal, setReveal] = React.useState(false);
  const input = React.useRef<HTMLInputElement | null>(null);
  const setInputRef = useMergedRefs(input, ref);
  const shakeRef = useErrorShake(error);

  const invalid = !!error;
  const isPassword = type === "password";
  const canClear = clearable && shown !== "" && !disabled && !readOnly;

  return (
    <FieldShell id={id} label={label} hint={hint} error={error} required={required} className={className}>
      <div
        ref={shakeRef}
        className={styles.box}
        data-invalid={invalid || undefined}
        data-disabled={disabled || undefined}
      >
        {prefix ? <span className={styles.slot}>{prefix}</span> : null}
        <input
          {...rest}
          ref={setInputRef}
          id={id}
          type={isPassword && reveal ? "text" : type}
          inputMode={inputMode ?? (digits ? "numeric" : undefined)}
          dir={ltr ? "ltr" : undefined}
          value={shown}
          disabled={disabled}
          readOnly={readOnly}
          required={required}
          aria-invalid={invalid || undefined}
          aria-describedby={describedBy(id, hint, error, rest["aria-describedby"])}
          className={cx(styles.input, inputClassName)}
          onChange={(e) => {
            onChange?.(e);
            const raw = e.currentTarget.value;
            setTyped(raw);
            setValue(normalise(raw));
          }}
        />
        {canClear ? (
          <button
            type="button"
            className={styles.action}
            aria-label="پاک کردن"
            onClick={() => {
              setTyped("");
              setValue("");
              input.current?.focus();
            }}
          >
            <Icon.close size={16} stroke={2.2} />
          </button>
        ) : null}
        {isPassword ? (
          <button
            type="button"
            className={styles.action}
            aria-label={reveal ? "پنهان کردن رمز" : "نمایش رمز"}
            aria-pressed={reveal}
            aria-controls={id}
            onClick={() => setReveal((r) => !r)}
          >
            {reveal ? <Icon.eyeOff size={18} /> : <Icon.eye size={18} />}
          </button>
        ) : null}
        {suffix ? <span className={styles.slot}>{suffix}</span> : null}
      </div>
    </FieldShell>
  );
}

/* ── TextArea ──────────────────────────────────────────────── */

type NativeTextArea = Omit<React.TextareaHTMLAttributes<HTMLTextAreaElement>, "value" | "defaultValue" | "children">;

export type TextAreaProps = NativeTextArea & {
  label?: React.ReactNode;
  hint?: React.ReactNode;
  error?: React.ReactNode;
  value?: string;
  defaultValue?: string;
  onValueChange?: (value: string) => void;
  /** Grow with the content (default true). */
  autoGrow?: boolean;
  className?: string;
  ref?: React.Ref<HTMLTextAreaElement>;
};

function supportsFieldSizing(): boolean {
  return typeof CSS !== "undefined" && typeof CSS.supports === "function" && CSS.supports("field-sizing", "content");
}

export function TextArea({
  label,
  hint,
  error,
  value: valueProp,
  defaultValue = "",
  onValueChange,
  onChange,
  autoGrow = true,
  className,
  id: idProp,
  disabled,
  required,
  rows = 3,
  ref,
  ...rest
}: TextAreaProps) {
  const autoId = React.useId();
  const id = idProp ?? autoId;
  const [value, setValue] = useControllable(valueProp, defaultValue, onValueChange);
  const area = React.useRef<HTMLTextAreaElement | null>(null);
  const setAreaRef = useMergedRefs(area, ref);
  const shakeRef = useErrorShake(error);

  // Fallback auto-grow where `field-sizing: content` is missing:
  // measure after every value change (typing, paste, programmatic set).
  React.useLayoutEffect(() => {
    const el = area.current;
    if (!autoGrow || !el || supportsFieldSizing()) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }, [value, autoGrow]);

  return (
    <FieldShell id={id} label={label} hint={hint} error={error} required={required} className={className}>
      <div
        ref={shakeRef}
        className={cx(styles.box, styles.areaBox)}
        data-invalid={error ? true : undefined}
        data-disabled={disabled || undefined}
      >
        <textarea
          {...rest}
          ref={setAreaRef}
          id={id}
          rows={rows}
          value={value}
          disabled={disabled}
          required={required}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy(id, hint, error, rest["aria-describedby"])}
          className={cx(styles.input, styles.area, autoGrow && styles.autoGrow)}
          onChange={(e) => {
            onChange?.(e);
            setValue(e.currentTarget.value);
          }}
        />
      </div>
    </FieldShell>
  );
}

/* ── Select ────────────────────────────────────────────────── */

export type SelectOption = { value: string; label: string; disabled?: boolean };

type NativeSelect = Omit<React.SelectHTMLAttributes<HTMLSelectElement>, "value" | "defaultValue" | "multiple">;

export type SelectProps = NativeSelect & {
  label?: React.ReactNode;
  hint?: React.ReactNode;
  error?: React.ReactNode;
  value?: string;
  defaultValue?: string;
  onValueChange?: (value: string) => void;
  options?: readonly SelectOption[];
  /** Shown while nothing is chosen (value ""). */
  placeholder?: string;
  className?: string;
  ref?: React.Ref<HTMLSelectElement>;
};

/**
 * A styled native <select>. Native on purpose: on phones it opens the
 * OS picker (big targets, accessible, scrolls well), which a custom
 * dropdown in a PWA cannot match.
 */
export function Select({
  label,
  hint,
  error,
  value: valueProp,
  defaultValue = "",
  onValueChange,
  onChange,
  options,
  placeholder,
  children,
  className,
  id: idProp,
  disabled,
  required,
  ref,
  ...rest
}: SelectProps) {
  const autoId = React.useId();
  const id = idProp ?? autoId;
  const [value, setValue] = useControllable(valueProp, defaultValue, onValueChange);
  const shakeRef = useErrorShake(error);

  return (
    <FieldShell id={id} label={label} hint={hint} error={error} required={required} className={className}>
      <div
        ref={shakeRef}
        className={cx(styles.box, styles.selectBox)}
        data-invalid={error ? true : undefined}
        data-disabled={disabled || undefined}
      >
        <select
          {...rest}
          ref={ref}
          id={id}
          value={value}
          disabled={disabled}
          required={required}
          data-placeholder={placeholder && value === "" ? "" : undefined}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy(id, hint, error, rest["aria-describedby"])}
          className={cx(styles.input, styles.select)}
          onChange={(e) => {
            onChange?.(e);
            setValue(e.currentTarget.value);
          }}
        >
          {placeholder ? (
            <option value="" disabled={required}>
              {placeholder}
            </option>
          ) : null}
          {options?.map((o) => (
            <option key={o.value} value={o.value} disabled={o.disabled}>
              {o.label}
            </option>
          ))}
          {children}
        </select>
        <Icon.chevronDown className={styles.chevron} size={18} />
      </div>
    </FieldShell>
  );
}
