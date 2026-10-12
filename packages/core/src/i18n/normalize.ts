/* Input normalisation — MUST stay byte-for-byte equivalent to
 * backend/app/core/normalize.py and backend/app/core/validators.py.
 *
 * The shared fixture packages/core/fixtures/normalize.json is the source of
 * truth and is tested on both sides. If the two drift, a subscriber typed on an
 * Arabic keyboard ("علي" with U+064A) matches on one side and not the other,
 * and nobody can see why: the strings look identical on screen. */

import { toEn } from "./digits";

/* Python's `\s` / str.isspace() set, spelled out. JS `\s` differs in both
 * directions: it includes U+FEFF (BOM) and misses U+001C–U+001F and U+0085.
 * Using JS `\s` here would make a BOM-prefixed Excel cell normalise
 * differently on the client than on the server. */
const WS = "\\t\\n\\v\\f\\r\\x1c-\\x1f \\x85\\xa0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000";
const WS_RUN = new RegExp(`[${WS}]+`, "g");
const MOBILE_JUNK = new RegExp(`[${WS}\\-()]`, "g");
const SUB_JUNK = new RegExp(`[${WS}\\-/.]`, "g");
const ID_JUNK = new RegExp(`[${WS}\\-]`, "g");

/** Arabic harakat U+064B–U+0652, superscript alef U+0670, tatweel U+0640.
 *  Hamza-above U+0654 ("خانهٔ") is deliberately NOT stripped. */
const DIACRITICS = /[ً-ْٰـ]/g;
const ZWNJ = /‌/g;

/**
 * Canonical form for search and matching (names, addresses, free text):
 * ASCII digits, Persian ی/ک/ه, no diacritics/tatweel, ZWNJ → space,
 * whitespace collapsed and trimmed, Latin A–Z lower-cased.
 */
export function normalizeText(s: string): string {
  const t = toEn(s)
    .replace(/[يى]/g, "ی")
    .replace(/ك/g, "ک")
    .replace(/ة/g, "ه")
    .replace(DIACRITICS, "")
    .replace(ZWNJ, " ")
    .replace(WS_RUN, " ")
    // After collapsing, the only whitespace left is a single " " at each end.
    // String.prototype.trim() would also eat a BOM, which Python keeps.
    .replace(/^ | $/g, "");
  // Only A–Z: toLowerCase() would also fold "Ä"/"İ", which the server does not.
  return t.replace(/[A-Z]/g, (c) => c.toLowerCase());
}

const MOBILE_PREFIXES = ["+98", "0098", "98", "0"] as const;

/**
 * Any way an Iranian mobile is typed → "09XXXXXXXXX", or null.
 * Accepts Persian/Arabic digits, spaces, dashes, parentheses and the prefixes
 * +98 / 0098 / 98 / 0 / none. A prefix is stripped only when exactly 10 digits
 * remain, so "9812345678" (no prefix, starts with 98) stays a valid number
 * instead of being cut to 8 digits.
 */
export function normalizeMobile(s: string | null | undefined): string | null {
  if (!s) return null;
  let t = toEn(s).replace(MOBILE_JUNK, "");
  for (const p of MOBILE_PREFIXES) {
    if (t.startsWith(p) && t.length - p.length === 10) {
      t = t.slice(p.length);
      break;
    }
  }
  return /^9[0-9]{9}$/.test(t) ? "0" + t : null;
}

/**
 * Subscription number → ASCII digits (4..20), leading zeros KEPT (they are
 * part of the number on the bill), or null. Spaces, dashes, slashes and dots
 * that people copy from the bill are removed.
 */
export function normalizeSubscription(s: string | number | null | undefined): string | null {
  if (s === null || s === undefined) return null;
  const t = toEn(String(s)).replace(SUB_JUNK, "");
  // [0-9], not \d: only ASCII digits may reach storage and comparisons.
  return /^[0-9]{4,20}$/.test(t) ? t : null;
}

/** Iranian national code (کد ملی): 10 digits, not all identical, mod-11 check digit. */
export function isValidNationalCode(s: string | null | undefined): boolean {
  if (!s) return false;
  const t = toEn(s).replace(ID_JUNK, "");
  if (!/^[0-9]{10}$/.test(t)) return false;
  // "1111111111" passes the checksum; the all-same codes are not issued.
  if (/^(.)\1{9}$/.test(t)) return false;
  let sum = 0;
  for (let i = 0; i < 9; i++) sum += Number(t[i]) * (10 - i);
  const r = sum % 11;
  const check = Number(t[9]);
  return r < 2 ? check === r : check === 11 - r;
}

/** IBAN (شبا) → "IR" + 24 digits, or null. Accepts with/without "IR", any case,
 *  Persian/Arabic digits, spaces and dashes. Shape only — see isValidIban. */
export function normalizeIban(s: string | null | undefined): string | null {
  if (!s) return null;
  let t = toEn(s).replace(ID_JUNK, "").toUpperCase();
  if (/^[0-9]{24}$/.test(t)) t = "IR" + t;
  return /^IR[0-9]{24}$/.test(t) ? t : null;
}

/** ISO 13616 mod-97 remainder of an alphanumeric IBAN string. Chunked so the
 *  ~30-digit number never exceeds 2^53 (Number) — no BigInt needed. */
function ibanMod97(iban: string): number {
  const moved = iban.slice(4) + iban.slice(0, 4);
  let digits = "";
  for (const ch of moved) {
    const c = ch.charCodeAt(0);
    digits += c >= 65 && c <= 90 ? String(c - 55) : ch; // A=10 … Z=35
  }
  let rem = 0;
  for (let i = 0; i < digits.length; i += 9) {
    rem = Number(String(rem) + digits.slice(i, i + 9)) % 97;
  }
  return rem;
}

/** Normalised shape AND the ISO 13616 checksum (remainder 1). */
export function isValidIban(s: string | null | undefined): boolean {
  const t = normalizeIban(s);
  return t !== null && ibanMod97(t) === 1;
}

/** "09121234567" → "0912***4567" (list views never show a full number, §4.4). */
export function maskMobile(m: string | null | undefined): string {
  if (!m || m.length < 8) return "—";
  return `${m.slice(0, 4)}***${m.slice(-4)}`;
}
