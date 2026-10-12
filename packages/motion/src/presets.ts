/* ─────────────────────────────────────────────────────────────
 *  Spring presets.
 *
 *  Think in damping ratio, not in raw numbers:
 *      ζ = c / (2·√(k·m))        (m = 1 everywhere here)
 *  ζ < 1 overshoots and settles; ≈0.7–0.8 reads "alive but not
 *  cartoonish"; ≥0.95 arrives and stops dead, which people describe as
 *  stiff or lifeless rather than fast.
 *
 *  `precision` is in the units of the value the spring carries:
 *  0.002 for a normalised 0..1 progress, ~0.25 for pixels. The
 *  reference once had its 0..1 sheet at 0.4 — the spring declared
 *  itself settled 40% short of the target and snapped the rest, which
 *  read as "flies up and stops hard" and was mis-diagnosed as a
 *  stiffness problem for a while. If a transition teleports near the
 *  end, check precision before touching stiffness.
 *
 *  Every ζ written in a comment below is asserted by presets.test.ts
 *  against the numbers (PRESET_ZETA). The reference shipped a sheet
 *  comment describing 185/21 (ζ 0.77) over values of 170/25 (ζ 0.96);
 *  the test exists so a retune cannot leave the reasoning stale again.
 * ───────────────────────────────────────────────────────────── */

import type { SpringConfig } from "./spring";

type Preset = Required<Pick<SpringConfig, "stiffness" | "damping" | "precision">>;

export const MOTION = {
  /** ζ≈0.72 — the floating nav pill. The softest preset and deliberately
   *  the app's signature: one gentle settle, no cartoon bounce. 0..n index. */
  cradle: { stiffness: 210, damping: 21, precision: 0.004 },

  /** ζ≈0.94 — interactive swipe-back of a screen. Near-critical so the
   *  page lands without wobbling under the user's thumb; a little softer
   *  than the reference's first 320/34 so the end of the move is not a slam. */
  swipe: { stiffness: 240, damping: 29, precision: 0.002 },

  /** ζ≈0.80 — bottom sheets (0 = open, 1 = closed, multiplied by the
   *  measured height). 200/26 (ζ 0.92) arrived fast and simply stopped,
   *  which the client called "dry"; 190/22 sits near `cradle` so sheets
   *  share the app's settle, while staying damped enough that the
   *  `Math.max(0, x)` clamp in the sheet writer rarely has to act.
   *  Settles in ≈0.36s. */
  sheet: { stiffness: 190, damping: 22, precision: 0.002 },

  /** ζ≈0.84 — shared-element flight (photo zoom, card → detail). A hint
   *  of overshoot sells the landing without the image visibly bouncing. */
  flight: { stiffness: 260, damping: 27, precision: 0.002 },

  /** ζ≈0.75 — switch knobs and segmented indicators: quick, with one
   *  small overshoot so the toggle feels physical. 0..1 / 0..n. */
  thumb: { stiffness: 300, damping: 26, precision: 0.002 },

  /** ζ≈0.84 — draggable split dividers, in pixels. */
  divider: { stiffness: 170, damping: 22, precision: 0.25 },

  /** ζ≈0.92 — list-row swipe-to-reveal, in pixels. Firm: a row that
   *  wobbles open makes its action buttons hard to hit. */
  row: { stiffness: 340, damping: 34, precision: 0.25 },

  /** ζ≈0.78 — elastic overscroll / pull-to-refresh return, in pixels. */
  bounce: { stiffness: 420, damping: 32, precision: 0.25 },

  /** ζ≈0.50 — success badges, reward check marks, "+30 points" chips.
   *  The one place a visible overshoot is the point: it is a celebration.
   *  Drives a 0..1 scale. */
  pop: { stiffness: 320, damping: 18, precision: 0.002 },

  /** ζ≈1.03 — number count-up. Critically damped on purpose: a counter
   *  that overshoots shows a wrong number (12,040 then 12,000) for a
   *  moment. Precision is half a displayed unit; CountUp overrides it
   *  for decimals. */
  count: { stiffness: 160, damping: 26, precision: 0.5 },

  /** ζ≈0.23 — error shake, in pixels, kicked with an initial velocity
   *  from rest at 0. Strongly underdamped so it oscillates 3–4 times and
   *  dies out in ≈0.6s; v0 ≈ 260px/s gives ≈10px of travel. */
  shake: { stiffness: 700, damping: 12, precision: 0.25 },
} as const satisfies Record<string, Preset>;

export type MotionPreset = keyof typeof MOTION;

/** The ζ each preset's comment promises — kept honest by presets.test.ts. */
export const PRESET_ZETA: Record<MotionPreset, number> = {
  cradle: 0.72,
  swipe: 0.94,
  sheet: 0.8,
  flight: 0.84,
  thumb: 0.75,
  divider: 0.84,
  row: 0.92,
  bounce: 0.78,
  pop: 0.5,
  count: 1.03,
  shake: 0.23,
};
