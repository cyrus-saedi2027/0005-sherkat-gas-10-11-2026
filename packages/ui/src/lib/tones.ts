/* ─────────────────────────────────────────────────────────────
 *  Tones — the semantic colour vocabulary of badges, pills, banners.
 *
 *  Status labels (reading pending/approved/flagged…, case stages,
 *  ticket states) belong to @gazyar/core: its `labels.ts` maps a
 *  status code to `{ fa, tone }`, so admin and app always agree.
 *  Core's Tone is a subset of this one ("attn" and "reward" are
 *  presentation-only tones core never needs), so a core `Label` goes
 *  straight into <StatusPill status={…}> without a cast.
 * ───────────────────────────────────────────────────────────── */

import type { Label as CoreLabel } from "@gazyar/core";

export type Tone = "neutral" | "accent" | "ok" | "warn" | "crit" | "info" | "attn" | "reward";

export const TONES: readonly Tone[] = ["neutral", "accent", "ok", "warn", "crit", "info", "attn", "reward"];

/** A status rendered for people: Persian label + tone. Any core label is one. */
export type StatusLabel = CoreLabel | { fa: string; tone: Tone };
