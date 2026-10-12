/* ─────────────────────────────────────────────────────────────
 *  Tones — the semantic colour vocabulary of badges, pills, banners.
 *
 *  Status labels (reading pending/approved/flagged…, case stages,
 *  ticket states) belong to @gazyar/core: `labels.ts` maps a status
 *  code to `{ fa, tone }`, so admin and app always agree. Core's
 *  barrel does not export that table yet (it is being written in
 *  parallel), so the shape is mirrored here structurally. Core's Tone
 *  is a subset of this one ("attn" and "reward" are presentation-only
 *  tones core never needs), so a core `Label` is assignable to
 *  `StatusLabel` without a cast. When core's index exports `Label`,
 *  replace `StatusLabel` with a re-export.
 * ───────────────────────────────────────────────────────────── */

export type Tone = "neutral" | "accent" | "ok" | "warn" | "crit" | "info" | "attn" | "reward";

export const TONES: readonly Tone[] = ["neutral", "accent", "ok", "warn", "crit", "info", "attn", "reward"];

/** A status rendered for people: Persian label + tone (same shape as core's `Label`). */
export type StatusLabel = { fa: string; tone: Tone };
