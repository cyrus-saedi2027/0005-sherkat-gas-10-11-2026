/* ─────────────────────────────────────────────────────────────
 *  Persian digits for the UI — a thin layer over @gazyar/core.
 *
 *  The digit rules live in core (i18n/digits.ts), tested against the
 *  same normalisation fixtures as the backend. This file only adds the
 *  option shape the components want (`decimals` for fixed places) and
 *  must never grow its own digit mapping: a second implementation is
 *  how a mobile number once rendered grouped ("۰۹٬۱۲۱…") on one screen
 *  and plain on the next.
 *
 *  The rule that keeps the app coherent:
 *    • everything displayed goes through toFa / <Num>
 *    • everything compared, searched or stored goes through toEn first
 * ───────────────────────────────────────────────────────────── */

import { toEn as coreToEn, toFa as coreToFa, parseFaNumber as coreParse } from "@gazyar/core";

/** Persian thousands separator (U+066C) — not a Latin comma. */
export const FA_GROUP = "٬";
/** Persian decimal separator (U+066B). */
export const FA_DECIMAL = "٫";
/** U+2212: a real minus sign; a hyphen-minus looks short beside Persian digits. */
export const FA_MINUS = "−";

export type ToFaOptions = {
  /** Thousands grouping with ٬ (default true). Identifiers with a leading zero are never grouped. */
  group?: boolean;
  /** Fixed decimal places for numeric input. Strings keep their own. */
  decimals?: number;
};

/** Number → Persian-digit string: 1234.5 → "۱٬۲۳۴٫۵". Non-finite → "—". */
export function toFa(value: number | string, opts: ToFaOptions = {}): string {
  const { group = true, decimals } = opts;
  if (typeof value === "number" && decimals !== undefined && Number.isFinite(value)) {
    // toFixed caps at 100 places and throws beyond; clamp like core's formatters.
    return coreToFa(value.toFixed(Math.max(0, Math.min(20, decimals))), group);
  }
  return coreToFa(value, group);
}

/**
 * Persian (۰-۹) and Arabic-Indic (٠-٩) digits → ASCII. Arabic keyboards
 * emit the second set, which are different code points from Persian
 * ones and would silently break comparison.
 */
export const toEn: (s: string) => string = coreToEn;

/** Parse a typed number in any digit set ("۱٬۲۰۰٫۵") → 1200.5, or null. */
export const parseFaNumber: (s: string) => number | null = coreParse;
