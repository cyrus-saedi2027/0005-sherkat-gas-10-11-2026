import * as React from "react";
import { cx } from "../lib/cx";
import type { Tone } from "../lib/tones";
import { Icon } from "../icons";
import styles from "./Feedback.module.css";

/* ── Empty ─────────────────────────────────────────────────── */

export type EmptyProps = Omit<React.HTMLAttributes<HTMLDivElement>, "title"> & {
  icon?: React.ReactNode;
  title: React.ReactNode;
  text?: React.ReactNode;
  /** Usually a Button: the one thing to do next. */
  action?: React.ReactNode;
  ref?: React.Ref<HTMLDivElement>;
};

/** Empty state: say what is missing and what to do, in the user's words. */
export function Empty({ icon, title, text, action, className, ref, ...rest }: EmptyProps) {
  return (
    <div {...rest} ref={ref} className={cx(styles.empty, className)}>
      <span className={styles.emptyIcon} aria-hidden="true">
        {icon ?? <Icon.inbox size={24} stroke={1.7} />}
      </span>
      <div className={styles.emptyTitle}>{title}</div>
      {text ? <div className={styles.emptyText}>{text}</div> : null}
      {action ? <div className={styles.emptyAction}>{action}</div> : null}
    </div>
  );
}

/* ── Banner ────────────────────────────────────────────────── */

export type BannerTone = Extract<Tone, "info" | "warn" | "crit" | "ok" | "accent" | "reward" | "neutral">;

export type BannerProps = Omit<React.HTMLAttributes<HTMLDivElement>, "title"> & {
  tone?: BannerTone;
  title?: React.ReactNode;
  icon?: React.ReactNode | false;
  action?: React.ReactNode;
  onDismiss?: () => void;
  dismissLabel?: string;
  ref?: React.Ref<HTMLDivElement>;
};

const BANNER_ICON: Record<BannerTone, React.ReactNode> = {
  info: <Icon.info size={18} />,
  warn: <Icon.alert size={18} />,
  crit: <Icon.alert size={18} />,
  ok: <Icon.checkCircle size={18} />,
  accent: <Icon.sparkle size={18} />,
  reward: <Icon.gift size={18} />,
  neutral: <Icon.info size={18} />,
};

/**
 * Inline message. `crit` is announced immediately (role="alert");
 * everything else politely (role="status") so it does not interrupt.
 */
export function Banner({
  tone = "info",
  title,
  icon,
  action,
  onDismiss,
  dismissLabel = "بستن",
  className,
  children,
  ref,
  ...rest
}: BannerProps) {
  return (
    <div
      role={tone === "crit" ? "alert" : "status"}
      {...rest}
      ref={ref}
      data-gz-tone={tone}
      className={cx(styles.banner, className)}
    >
      {icon !== false ? (
        <span className={styles.bannerIcon} aria-hidden="true">
          {icon ?? BANNER_ICON[tone]}
        </span>
      ) : null}
      <div className={styles.bannerBody}>
        {title ? <div className={styles.bannerTitle}>{title}</div> : null}
        {children ? <div>{children}</div> : null}
      </div>
      {action ? <div className={styles.bannerAction}>{action}</div> : null}
      {onDismiss ? (
        <button type="button" className={styles.bannerClose} aria-label={dismissLabel} onClick={onDismiss}>
          <Icon.close size={16} stroke={2.2} />
        </button>
      ) : null}
    </div>
  );
}

/* ── Avatar ────────────────────────────────────────────────── */

const AVATAR_TONES: Tone[] = ["accent", "ok", "info", "reward", "attn", "warn"];

/** Stable tone per name, so the same person keeps the same colour across screens. */
export function avatarTone(name: string): Tone {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0;
  return AVATAR_TONES[h % AVATAR_TONES.length]!;
}

/**
 * Initials: first letter of the first two words. A ZWNJ separates them
 * — Persian letters side by side would otherwise join into one glyph
 * cluster ("ع" + "ر" → "عر") and read as a word, not initials.
 */
export function initials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  const letters = words.slice(0, 2).map((w) => Array.from(w)[0] ?? "");
  return letters.join("‌");
}

export type AvatarProps = Omit<React.HTMLAttributes<HTMLSpanElement>, "children"> & {
  name: string;
  src?: string;
  size?: "sm" | "md" | "lg";
  tone?: Tone;
  ref?: React.Ref<HTMLSpanElement>;
};

export function Avatar({ name, src, size = "md", tone, className, ref, ...rest }: AvatarProps) {
  const [failed, setFailed] = React.useState(false);
  const showImg = src && !failed;
  return (
    <span
      role="img"
      aria-label={name}
      {...rest}
      ref={ref}
      data-gz-tone={tone ?? avatarTone(name)}
      className={cx(styles.avatar, size !== "md" && styles[`avatar-${size}`], className)}
    >
      {showImg ? (
        <img src={src} alt="" onError={() => setFailed(true)} />
      ) : (
        <span aria-hidden="true">{initials(name)}</span>
      )}
    </span>
  );
}
