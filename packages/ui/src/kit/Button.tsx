import * as React from "react";
import { cx } from "../lib/cx";
import { Pressable } from "../primitives/Pressable";
import { Spinner } from "./Spinner";
import styles from "./Button.module.css";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "subtle";
export type ButtonSize = "sm" | "md" | "lg";

type NativeButton = Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "onClick">;

export type ButtonProps = NativeButton & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  /** Shows a spinner, keeps the width, blocks presses and sets aria-busy. */
  loading?: boolean;
  /** Icon before the label (inline-start: right in RTL). */
  iconStart?: React.ReactNode;
  iconEnd?: React.ReactNode;
  fullWidth?: boolean;
  onPress?: (e: React.MouseEvent<HTMLElement>) => void;
  onClick?: (e: React.MouseEvent<HTMLElement>) => void;
  ref?: React.Ref<HTMLButtonElement>;
};

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  iconStart,
  iconEnd,
  fullWidth,
  disabled,
  className,
  children,
  type = "button",
  ref,
  ...rest
}: ButtonProps) {
  return (
    <Pressable
      {...rest}
      as="button"
      type={type}
      ref={ref as React.Ref<HTMLElement>}
      // A loading button stays focusable (not `disabled`) so focus is not
      // thrown to <body> mid-submit; presses are swallowed instead.
      disabled={disabled}
      aria-disabled={loading || undefined}
      aria-busy={loading || undefined}
      onClick={(e) => {
        if (loading) {
          e.preventDefault();
          return;
        }
        rest.onClick?.(e);
      }}
      onPress={loading ? undefined : rest.onPress}
      press={size === "sm" ? "firm" : "normal"}
      className={cx(
        styles.button,
        styles[variant],
        size !== "md" && styles[size],
        fullWidth && styles.full,
        loading && styles.loading,
        className,
      )}
    >
      {iconStart ? <span className={styles.slot}>{iconStart}</span> : null}
      {children != null ? <span className={styles.label}>{children}</span> : null}
      {iconEnd ? <span className={styles.slot}>{iconEnd}</span> : null}
      {loading ? <Spinner className={styles.spinner} size={size === "sm" ? 16 : 20} label="" /> : null}
    </Pressable>
  );
}

export type IconButtonProps = Omit<ButtonProps, "iconStart" | "iconEnd" | "fullWidth" | "children"> & {
  /** Accessible name — required: an icon alone says nothing to a screen reader. */
  label: string;
  icon: React.ReactNode;
  round?: boolean;
};

export function IconButton({
  label,
  icon,
  variant = "subtle",
  size = "md",
  round,
  loading = false,
  className,
  type = "button",
  ref,
  ...rest
}: IconButtonProps) {
  return (
    <Pressable
      {...rest}
      as="button"
      type={type}
      ref={ref as React.Ref<HTMLElement>}
      aria-label={label}
      title={rest.title ?? label}
      aria-disabled={loading || undefined}
      aria-busy={loading || undefined}
      onClick={(e) => {
        if (loading) {
          e.preventDefault();
          return;
        }
        rest.onClick?.(e);
      }}
      onPress={loading ? undefined : rest.onPress}
      press="firm"
      className={cx(
        styles.button,
        styles.iconButton,
        styles[variant],
        size !== "md" && styles[size],
        round && styles.round,
        loading && styles.loading,
        className,
      )}
    >
      <span className={styles.slot}>{icon}</span>
      {loading ? <Spinner className={styles.spinner} size={size === "sm" ? 16 : 20} label="" /> : null}
    </Pressable>
  );
}
