/* ─────────────────────────────────────────────────────────────
 *  Geometry, depth, timing and gesture tokens.
 *
 *  Names say what a value is FOR, not how big it is: `R.card`, not
 *  `R.lg`. When every card uses R.card, the app's roundness is one
 *  number and nobody has to decide whether a card is "lg" or "xl".
 *
 *  These are mirrored as CSS custom properties in styles/global.css
 *  (--r-*, --sh-*, --ease-*, --z-*, --sp-*, --fs-*) so CSS Modules can
 *  use them; tokens.test.ts fails if the two drift apart.
 * ───────────────────────────────────────────────────────────── */

import { MOTION, RUBBER_K, VELOCITY_WINDOW_MS } from "@gazyar/motion";

export { MOTION };

/** Corner radii, px — named by what they wrap. */
export const R = {
  /** count badges, tiny status dots with text */
  badge: 7,
  /** tags and chips that are not pills */
  tag: 9,
  /** the rounded square behind an icon */
  icon: 14,
  /** text inputs, selects */
  field: 14,
  /** list rows */
  row: 18,
  /** stat tiles, quick-action tiles */
  tile: 18,
  /** cards */
  card: 22,
  /** bottom sheets (top corners) */
  sheet: 30,
  /** large hero panels */
  panel: 42,
  /** fully rounded: buttons, nav, segmented, switches */
  pill: 999,
} as const;

/**
 * Shadows by placement. Blur radii are deliberately small: ~20 rows sit
 * on screen at once and in the reference a larger row blur took p95 frame
 * time from 33ms to 50ms on a mid-range Android — measured. Separation
 * comes from the 1px `hair` border (free to paint), not from bigger
 * shadows. Colours come from the theme (`--c-shadow*`) so night mode can
 * deepen them without a second token set.
 */
export const SHADOW = {
  /** cards resting on the page */
  card: "0 14px 28px -20px var(--c-shadow)",
  /** rows and tiles — the cheapest, used ~20× per screen */
  soft: "0 6px 14px -10px var(--c-shadow)",
  /** something picked up: a dragged row, a floating action */
  lifted: "0 22px 40px -18px var(--c-shadowStrong)",
  /** bottom sheet edge, cast upward */
  sheet: "0 -14px 36px -18px var(--c-shadowStrong)",
  /** the floating pill nav */
  nav: "0 14px 30px -12px var(--c-shadowStrong)",
  /** primary buttons, active segment, chips */
  pill: "0 6px 14px -8px var(--c-shadow)",
  /** keyboard focus where an outline would be clipped (inside overflow:hidden) */
  focus: "0 0 0 2px var(--c-canvas), 0 0 0 4px var(--c-focus)",
} as const;

/**
 * CSS easings — for simple, non-interruptible state changes (press
 * scale, colour, opacity). Anything gesture-driven or interruptible uses
 * a spring from MOTION instead.
 */
export const EASE = {
  /** default for CSS transitions */
  out: "cubic-bezier(.22,1,.36,1)",
  /** sheet-like, matches the iOS feel */
  ios: "cubic-bezier(.32,.72,0,1)",
  inOut: "cubic-bezier(.65,0,.35,1)",
  /** small overshoot for expanding nav labels and pops done in CSS */
  spring: "cubic-bezier(.34,1.56,.64,1)",
} as const;

/** CSS durations, ms. */
export const DURATION = {
  /** press feedback — a press is not interruptible, so no spring */
  press: 280,
  fast: 160,
  base: 240,
  slow: 420,
} as const;

/**
 * Every gesture threshold in one table. When a gesture feels wrong the
 * fix is a number, and the numbers should be next to each other. Each
 * was changed at least once in the reference because of a real
 * complaint; the comments say which, so nobody "tidies" one back.
 */
export const GESTURE = {
  /** Swipe-back may start mid-screen too, not only from the edge strip. */
  edgeOnly: false,
  /** Edge strip width: a swipe starting here begins immediately.
   *  Was 38px — together with a 34% commit that read as "barely works". */
  edgeInset: 56,
  /** Horizontal travel needed before a mid-screen swipe-back starts. */
  anywhereLock: 16,
  /** Vertical drift an edge swipe tolerates. A thumb starting at the edge
   *  always arcs; the old 12px tolerance silently cancelled natural swipes
   *  ("sometimes it works, sometimes it doesn't"). */
  edgeBail: 30,
  /** Stricter mid-screen, where vertical scrolling is a real competitor. */
  anywhereBail: 22,
  /** Horizontal must beat vertical by this ratio to count as a swipe. */
  axisRatio: 1.5,
  /** Fraction of width that commits a back-swipe… */
  backCommit: 0.26,
  /** …or a flick of this many widths per second, whichever comes first.
   *  Requiring both felt heavy; distance only made flicks feel broken. */
  backFlick: 0.65,
  /** A flick back toward the start at this speed cancels regardless. */
  backCancelFlick: -1.0,
  /** Velocity window, ms — two samples were too noisy (see motion/gesture). */
  velWindow: VELOCITY_WINDOW_MS,
  /** Tab pan commit fraction and lock distance. */
  tabCommit: 0.3,
  tabLock: 8,
  /** Rows lock before tabs (6 < 8), so a row swipe wins over a tab pan —
   *  a conflict resolved by ordering two numbers, not a state machine. */
  rowLock: 6,
  /** Width a swiped row opens to, px. */
  rowOpen: 76,
  /** Resistance past a limit (rubber-band), shared with motion. */
  rubber: RUBBER_K,
  /** Sheet: closes past this fraction of its height… */
  sheetCommit: 0.36,
  /** …or on a downward flick faster than this many heights per second. */
  sheetFlick: 1.1,
  /** Pull distance (px, after rubber-banding) that triggers refresh. */
  pullRefresh: 66,
  /** Axis lock for scroll vs. pull, px — below this, finger tremor decides. */
  axisLock: 8,
  /** Long press: slightly above the usual 300–400ms because the app is
   *  used in a hurry and a faster one fired on ordinary taps. */
  longPressMs: 420,
  /** Movement allowed during a long press before it is cancelled. */
  longPressSlop: 8,
} as const;

/** Stacking order — the whole app uses these and nothing else. */
export const Z = {
  tab: 1,
  sticky: 5,
  push: 10,
  nav: 40,
  dropdown: 50,
  sheet: 55,
  dialog: 60,
  toast: 64,
  /** shared-element flight briefly passes over everything */
  flight: 70,
} as const;

/** Spacing scale, px. Index by step: SPACE[4] = 16. */
export const SPACE = {
  0: 0,
  1: 4,
  2: 8,
  3: 12,
  4: 16,
  5: 20,
  6: 24,
  7: 32,
  8: 40,
  9: 48,
} as const;

export type SpaceStep = keyof typeof SPACE;

/** Standard horizontal page gutter, px. */
export const GUTTER = 18;

/**
 * Type scale. Persian has tall ascenders and deep descenders, so line
 * heights stay within 1.45–1.75 — Latin-normal leading makes lines
 * collide. There is no letter-spacing anywhere: it breaks the joined
 * Persian script, and Persian has no capitals to track out.
 */
export const FONT = {
  title: { size: 22, weight: 800, lineHeight: 1.45 },
  head: { size: 16, weight: 800, lineHeight: 1.5 },
  body: { size: 14, weight: 500, lineHeight: 1.75 },
  /** small label — replaces the Latin all-caps "eyebrow" */
  cap: { size: 11, weight: 700, lineHeight: 1.6 },
  /** numbers in tiles and KPIs */
  num: { size: 24, weight: 800, lineHeight: 1.45 },
} as const;

export const FONT_FAMILY =
  "'Vazirmatn', system-ui, -apple-system, 'Segoe UI', Tahoma, 'Noto Sans Arabic', sans-serif";

/** Min-width breakpoints, px — admin is responsive, the user app phone-first. */
export const BREAKPOINTS = {
  sm: 480,
  md: 768,
  lg: 1024,
  xl: 1280,
} as const;

export type Breakpoint = keyof typeof BREAKPOINTS;

/** `(min-width: 768px)` for matchMedia. */
export function mq(bp: Breakpoint): string {
  return `(min-width: ${BREAKPOINTS[bp]}px)`;
}

/** Backdrop blur is expensive on mid-range Android; speed wins over
 *  effect. The flag exists to enable it on a capable device, not to be
 *  forgotten in the on position. */
export const FROST = { enabled: false };

/** Minimum touch target, px (WCAG 2.5.8 asks 24; phones want 44). */
export const TOUCH = 44;

/** Every token as the CSS custom property global.css must declare. */
export function tokenCssVars(): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [k, val] of Object.entries(R)) out[`--r-${k}`] = `${val}px`;
  for (const [k, val] of Object.entries(SHADOW)) out[`--sh-${k}`] = val;
  for (const [k, val] of Object.entries(EASE)) out[`--ease-${k}`] = val;
  for (const [k, val] of Object.entries(DURATION)) out[`--dur-${k}`] = `${val}ms`;
  for (const [k, val] of Object.entries(Z)) out[`--z-${k}`] = String(val);
  for (const [k, val] of Object.entries(SPACE)) out[`--sp-${k}`] = `${val}px`;
  out["--gutter"] = `${GUTTER}px`;
  out["--touch"] = `${TOUCH}px`;
  for (const [k, f] of Object.entries(FONT)) {
    out[`--fs-${k}`] = `${f.size}px`;
    out[`--fw-${k}`] = String(f.weight);
    out[`--lh-${k}`] = String(f.lineHeight);
  }
  out["--font"] = FONT_FAMILY;
  return out;
}
