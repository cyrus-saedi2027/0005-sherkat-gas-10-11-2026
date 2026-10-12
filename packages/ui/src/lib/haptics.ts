/* ─────────────────────────────────────────────────────────────
 *  Haptics — one named call per kind of feedback.
 *
 *  Patterns live here so firing is not scattered through the UI and
 *  the whole thing can be switched off (settings) or swapped (a
 *  Capacitor / React Native implementation) in one place.
 *    TAP     every press
 *    SELECT  a choice changed (segment, switch, tab)
 *    IMPACT  something committed (a refresh fired, a sheet snapped)
 *    SUCCESS a reward / approval landed
 *    WARN    an error the user must notice (paired with Shake)
 * ───────────────────────────────────────────────────────────── */

export type HapticKind = "tap" | "select" | "impact" | "success" | "warn";
export type HapticsImpl = (kind: HapticKind) => void;

const PATTERNS: Record<HapticKind, number | number[]> = {
  tap: 6,
  select: 10,
  impact: [0, 14],
  success: [0, 12, 60, 22],
  warn: [0, 24, 40, 24],
};

let enabled = true;
let impl: HapticsImpl | null = null;

/** Turn all haptic feedback on or off (user setting). */
export function setHapticsEnabled(on: boolean): void {
  enabled = on;
}

export function isHapticsEnabled(): boolean {
  return enabled;
}

/** Plug in a native implementation (Capacitor Haptics, RN). `null` restores the web default. */
export function setHapticsImpl(fn: HapticsImpl | null): void {
  impl = fn;
}

export function fireHaptic(kind: HapticKind): void {
  if (!enabled) return;
  try {
    if (impl) {
      impl(kind);
      return;
    }
    // iOS Safari has no vibrate; some WebViews throw on it before a user
    // gesture. Feedback is a nicety — never let it break a tap.
    if (typeof navigator !== "undefined" && typeof navigator.vibrate === "function") {
      navigator.vibrate(PATTERNS[kind]);
    }
  } catch {
    /* ignore */
  }
}

export const TAP = (): void => fireHaptic("tap");
export const SELECT = (): void => fireHaptic("select");
export const IMPACT = (): void => fireHaptic("impact");
export const SUCCESS = (): void => fireHaptic("success");
export const WARN = (): void => fireHaptic("warn");
