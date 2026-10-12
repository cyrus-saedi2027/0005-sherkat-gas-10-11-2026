/* ─────────────────────────────────────────────────────────────
 *  Persian digits — local until @gazyar/core's i18n lands.
 *
 *  Core is being written in parallel and does not export its digit
 *  helpers yet. These mirror the contract in ARCHITECTURE §0.7 / §4
 *  (normalize.py ↔ core/i18n): when core ships `toFa`/`toEn`, delete
 *  this file and re-export from "@gazyar/core" so there is exactly one
 *  implementation shared with the backend fixtures.
 *
 *  The rule that keeps the app coherent:
 *    • everything displayed goes through toFa / <Num>
 *    • everything compared, searched or stored goes through toEn first
 * ───────────────────────────────────────────────────────────── */

const FA = "۰۱۲۳۴۵۶۷۸۹";
/** Persian thousands separator (U+066C) — not a Latin comma. */
export const FA_GROUP = "٬";
/** Persian decimal separator (U+066B). */
export const FA_DECIMAL = "٫";
/** U+2212: a real minus sign; a hyphen-minus looks short beside Persian digits. */
export const FA_MINUS = "−";

export type ToFaOptions = {
  /** Thousands grouping with ٬ (default true). */
  group?: boolean;
  /** Fixed decimal places for numeric input. Strings keep their own. */
  decimals?: number;
};

/** Number → Persian-digit string: 1234.5 → "۱٬۲۳۴٫۵". Non-finite → "—". */
export function toFa(value: number | string, opts: ToFaOptions = {}): string {
  const { group = true, decimals } = opts;
  let s: string;
  if (typeof value === "number") {
    if (!Number.isFinite(value)) return "—";
    s = decimals === undefined ? String(value) : value.toFixed(decimals);
    // String(1e21) is exponential; fall back to a plain integer rendering.
    if (/e/i.test(s)) s = BigInt(Math.trunc(value)).toString();
  } else {
    s = toEn(value).trim();
  }

  const negative = s.startsWith("-");
  const body = negative ? s.slice(1) : s;
  const dot = body.indexOf(".");
  const int = dot >= 0 ? body.slice(0, dot) : body;
  const frac = dot >= 0 ? body.slice(dot + 1) : "";

  let out = int;
  if (group && /^\d+$/.test(int)) {
    out = int.replace(/\B(?=(\d{3})+(?!\d))/g, FA_GROUP);
  }
  if (frac) out += FA_DECIMAL + frac;
  return (negative ? FA_MINUS : "") + out.replace(/\d/g, (d) => FA[Number(d)]!);
}

/**
 * Persian (۰-۹) and Arabic-Indic (٠-٩) digits → ASCII. Arabic keyboards
 * emit the second set, which are different code points from Persian
 * ones and would silently break comparison.
 */
export function toEn(s: string): string {
  return s.replace(/[۰-۹٠-٩]/g, (d) => {
    const code = d.charCodeAt(0);
    return String(code >= 0x06f0 ? code - 0x06f0 : code - 0x0660);
  });
}
