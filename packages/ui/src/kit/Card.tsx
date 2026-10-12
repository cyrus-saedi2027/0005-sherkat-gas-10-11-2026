import * as React from "react";
import { cx } from "../lib/cx";
import { Pressable, type PressableProps } from "../primitives/Pressable";
import styles from "./Card.module.css";

export type CardVariant = "plain" | "elevated" | "accent" | "deep";

export type CardProps = Omit<PressableProps, "as"> & {
  variant?: CardVariant;
  padding?: "none" | "sm" | "md" | "lg";
  as?: "div" | "section" | "article" | "li" | "button" | "a";
};

/**
 * Surface for grouped content. With `onPress` (or `href`) it becomes a
 * button (or link) with a subtle press; otherwise a plain container.
 */
export function Card({ variant = "elevated", padding = "md", as, onPress, className, ...rest }: CardProps) {
  const tag = as ?? (rest.href ? "a" : onPress ? "button" : "div");
  return (
    <Pressable
      {...rest}
      as={tag}
      onPress={onPress}
      press={onPress || rest.href ? "subtle" : "none"}
      className={cx(styles.card, styles[variant], styles[`pad-${padding}`], className)}
    />
  );
}
