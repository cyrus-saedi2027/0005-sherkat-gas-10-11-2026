import * as React from "react";
import { cx } from "../lib/cx";
import type { Tone } from "../lib/tones";
import { Icon } from "../icons";
import { Pressable, type PressableProps } from "../primitives/Pressable";
import styles from "./ListRow.module.css";

export type ListRowProps = Omit<PressableProps, "as" | "title"> & {
  /** Icon in a rounded square at the inline-start. */
  icon?: React.ReactNode;
  iconTone?: Tone;
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  /** Inline-end content: a value, a StatusPill, a Switch. */
  trailing?: React.ReactNode;
  /** Forward chevron (points inline-end, mirrored in RTL). Default: shown when the row navigates. */
  chevron?: boolean;
  /** Borderless row for use inside a Card. */
  flat?: boolean;
  /** Let title/subtitle wrap instead of ellipsizing. */
  wrap?: boolean;
  as?: "div" | "li" | "button" | "a";
};

export function ListRow({
  icon,
  iconTone,
  title,
  subtitle,
  trailing,
  chevron,
  flat,
  wrap,
  as,
  onPress,
  className,
  ...rest
}: ListRowProps) {
  const tag = as ?? (rest.href ? "a" : onPress ? "button" : "div");
  const navigates = !!onPress || !!rest.href;
  return (
    <Pressable
      {...rest}
      as={tag}
      onPress={onPress}
      press={navigates ? "subtle" : "none"}
      className={cx(styles.row, flat && styles.flat, wrap && styles.wrap, className)}
    >
      {icon ? (
        <span className={styles.icon} data-gz-tone={iconTone} aria-hidden="true">
          {icon}
        </span>
      ) : null}
      <span className={styles.text}>
        <span className={styles.title}>{title}</span>
        {subtitle ? <span className={styles.subtitle}>{subtitle}</span> : null}
      </span>
      {trailing ? <span className={styles.trailing}>{trailing}</span> : null}
      {(chevron ?? navigates) ? <Icon.chevronEnd className={styles.chevron} size={18} /> : null}
    </Pressable>
  );
}
