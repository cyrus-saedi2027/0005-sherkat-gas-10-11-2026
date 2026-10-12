/* Display formatting for the business units: points, rials/tomans, m³, %.
 * All output uses Persian digits (toFa). Inputs are plain numbers as the API
 * sends them: money in integer rials, points as integers, consumption as m³. */

import { toFa } from "./i18n/digits";

/** toFixed(`digits`) rounding, rendered with toFa (which also drops a "-0" sign). */
function fixed(n: number, digits: number): string {
  if (!Number.isFinite(n)) return "—";
  return toFa(n.toFixed(Math.max(0, Math.min(20, digits))));
}

/** "۱٬۲۵۰ امتیاز" */
export function formatPoints(n: number): string {
  return `${fixed(n, 0)} امتیاز`;
}

/** "۵٬۰۰۰٬۰۰۰ ریال" */
export function formatRial(n: number): string {
  return `${fixed(n, 0)} ریال`;
}

/** Rials in, tomans out: "۵۰۰٬۰۰۰ تومان". Rounded to whole tomans —
 *  a 5-rial remainder is below anything a person can pay. */
export function formatToman(rial: number): string {
  return `${fixed(rial / 10, 0)} تومان`;
}

/** "۳٬۵۰۰ مترمکعب" (digits = decimals shown). */
export function formatM3(n: number, digits = 0): string {
  return `${fixed(n, digits)} مترمکعب`;
}

/**
 * "۱۲٪", or with `signed` "+۱۲٪" / "−۱۲٪" (zero never gets a sign).
 * Used for reduction vs baseline, where the sign is the whole message.
 */
export function formatPercent(n: number, signed = false, digits = 0): string {
  if (!Number.isFinite(n)) return "—";
  const d = Math.max(0, Math.min(20, digits));
  // Decide the sign on the *rounded* value: −0.3 shown as "۰٪" must not read "−۰٪".
  const isZero = Number(Math.abs(n).toFixed(d)) === 0;
  const sign = isZero ? "" : n < 0 ? "−" : signed ? "+" : "";
  return `${sign}${fixed(Math.abs(n), d)}٪`;
}

const UNITS = [
  { at: 1e9, word: "میلیارد" },
  { at: 1e6, word: "میلیون" },
  { at: 1e3, word: "هزار" },
] as const;

/**
 * Short form for tiles and chart axes: "۹۵۰", "۱٫۲ هزار", "۳ میلیون",
 * "۲٫۵ میلیارد". One decimal at most, trailing "٫۰" dropped.
 */
export function compactFa(n: number): string {
  if (!Number.isFinite(n)) return "—";
  const abs = Math.abs(n);
  const sign = n < 0 ? "−" : "";
  for (let i = 0; i < UNITS.length; i++) {
    const u = UNITS[i]!;
    if (abs < u.at) continue;
    const v = Math.round((abs / u.at) * 10) / 10;
    // 999_950 rounds to "1000 هزار" — promote to the next unit instead.
    const bigger = UNITS[i - 1];
    if (v >= 1000 && bigger) return sign + compactOne(abs / bigger.at, bigger.word);
    return sign + compactOne(abs / u.at, u.word);
  }
  const r = Math.round(abs);
  return (r === 0 ? "" : sign) + toFa(r);
}

function compactOne(v: number, word: string): string {
  const rounded = Math.round(v * 10) / 10;
  const s = Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
  return `${toFa(s)} ${word}`;
}
