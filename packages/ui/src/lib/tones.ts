/* ─────────────────────────────────────────────────────────────
 *  Tones — the semantic colour vocabulary of badges, pills, banners.
 *
 *  Status labels (reading pending/approved/flagged…, case stages,
 *  ticket states) belong to @gazyar/core: it maps a status code to a
 *  Persian label and one of these tones, so admin and app always agree.
 *  Core does not export that table yet, so the tone union is declared
 *  here; core's labels must use exactly these names. When core lands,
 *  import its `StatusLabel` type and delete the local one.
 * ───────────────────────────────────────────────────────────── */

export type Tone = "neutral" | "accent" | "ok" | "warn" | "crit" | "info" | "attn" | "reward";

export const TONES: readonly Tone[] = ["neutral", "accent", "ok", "warn", "crit", "info", "attn", "reward"];

/** A status rendered for people: Persian label + tone. */
export type StatusLabel = { label: string; tone: Tone };
