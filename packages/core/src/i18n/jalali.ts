/* Gregorian ↔ Jalali (Solar Hijri), dependency-free.
 *
 * Arithmetic is the Borkowski/jalaali-js algorithm (33-year cycles anchored on
 * a table of break years). Calendar *days* for instants are always taken in
 * Asia/Tehran, matching backend/app/core/jalali.py: a reading submitted at
 * 23:30 UTC on the last day of a month already belongs to the next Tehran day,
 * and therefore possibly to the next period. */

import { toFa } from "./digits";

export interface JalaliDate {
  jy: number;
  jm: number; // 1..12
  jd: number; // 1..31
}

export interface GregorianDate {
  gy: number;
  gm: number; // 1..12
  gd: number;
}

/* Truncating division, not Math.floor: the algorithm relies on it.
 * With floor, div(3 - 8, 6) is −1 instead of 0 and every date in Jan/Feb lands
 * one year off with jm overflowing past 12. */
const div = (a: number, b: number) => Math.trunc(a / b);
const mod = (a: number, b: number) => a - Math.trunc(a / b) * b;

/* Break years of the 2820-year grand cycle model (jalaali-js). Valid for
 * jy ∈ [-61, 3177] — far beyond anything this app will see. */
const BREAKS = [
  -61, 9, 38, 199, 426, 686, 756, 818, 1111, 1181, 1210, 1635, 2060, 2097, 2192, 2262, 2324, 2394,
  2456, 3178,
] as const;

interface JalCal {
  /** 0 ⇒ jy is a leap year. Non-zero values are positions within the 4/5-year sub-cycle. */
  leap: number;
  /** Gregorian year in which jy begins. */
  gy: number;
  /** Day of March (Gregorian) on which Farvardin 1 of jy falls. */
  march: number;
}

function jalCal(jy: number): JalCal {
  const gy = jy + 621;
  let leapJ = -14;
  let jp: number = BREAKS[0];
  let jump = 0;
  if (jy < jp || jy >= BREAKS[BREAKS.length - 1]!) throw new RangeError(`Jalali year out of range: ${jy}`);
  for (let i = 1; i < BREAKS.length; i++) {
    const jm = BREAKS[i]!;
    jump = jm - jp;
    if (jy < jm) break;
    leapJ = leapJ + div(jump, 33) * 8 + div(mod(jump, 33), 4);
    jp = jm;
  }
  let n = jy - jp;
  leapJ = leapJ + div(n, 33) * 8 + div(mod(n, 33) + 3, 4);
  if (mod(jump, 33) === 4 && jump - n === 4) leapJ += 1;
  const leapG = div(gy, 4) - div((div(gy, 100) + 1) * 3, 4) - 150;
  const march = 20 + leapJ - leapG;
  if (jump - n < 6) n = n - jump + div(jump + 4, 33) * 33;
  let leap = mod(mod(n + 1, 33) - 1, 4);
  if (leap === -1) leap = 4;
  return { leap, gy, march };
}

/** Gregorian → Julian Day Number. */
function g2d(gy: number, gm: number, gd: number): number {
  let d =
    div((gy + div(gm - 8, 6) + 100100) * 1461, 4) + div(153 * mod(gm + 9, 12) + 2, 5) + gd - 34840408;
  d = d - div(div(gy + 100100 + div(gm - 8, 6), 100) * 3, 4) + 752;
  return d;
}

/** Julian Day Number → Gregorian. */
function d2g(jdn: number): GregorianDate {
  let j = 4 * jdn + 139361631;
  j = j + div(div(4 * jdn + 183187720, 146097) * 3, 4) * 4 - 3908;
  const i = div(mod(j, 1461), 4) * 5 + 308;
  const gd = div(mod(i, 153), 5) + 1;
  const gm = mod(div(i, 153), 12) + 1;
  const gy = div(j, 1461) - 100100 + div(8 - gm, 6);
  return { gy, gm, gd };
}

function j2d(jy: number, jm: number, jd: number): number {
  const r = jalCal(jy);
  return g2d(r.gy, 3, r.march) + (jm - 1) * 31 - div(jm, 7) * (jm - 7) + jd - 1;
}

function d2j(jdn: number): JalaliDate {
  const gy = d2g(jdn).gy;
  let jy = gy - 621;
  const r = jalCal(jy);
  let k = jdn - g2d(gy, 3, r.march);
  if (k >= 0) {
    if (k <= 185) return { jy, jm: 1 + div(k, 31), jd: mod(k, 31) + 1 };
    k -= 186;
  } else {
    // Before Farvardin 1 of gy-621 ⇒ still in the previous Jalali year.
    // r.leap === 1 here means that *previous* year was leap (Esfand has 30 days).
    jy -= 1;
    k += 179;
    if (r.leap === 1) k += 1;
  }
  return { jy, jm: 7 + div(k, 30), jd: mod(k, 30) + 1 };
}

export function gregorianToJalali(gy: number, gm: number, gd: number): JalaliDate {
  return d2j(g2d(gy, gm, gd));
}

export function jalaliToGregorian(jy: number, jm: number, jd: number): GregorianDate {
  return d2g(j2d(jy, jm, jd));
}

/* Note: leap is tested with `=== 0`. MediStock's port tested `=== 1`, which is
 * the flag for "the year *before* was leap" — Esfand 1403 came out as 29 days. */
export function isJalaliLeapYear(jy: number): boolean {
  return jalCal(jy).leap === 0;
}

export function jDaysInMonth(jy: number, jm: number): number {
  if (jm <= 6) return 31;
  if (jm <= 11) return 30;
  return isJalaliLeapYear(jy) ? 30 : 29;
}

export function isValidJalaliDate(jy: number, jm: number, jd: number): boolean {
  return (
    Number.isInteger(jy) &&
    Number.isInteger(jm) &&
    Number.isInteger(jd) &&
    jy >= BREAKS[0] &&
    jy < BREAKS[BREAKS.length - 1]! &&
    jm >= 1 &&
    jm <= 12 &&
    jd >= 1 &&
    jd <= jDaysInMonth(jy, jm)
  );
}

export const J_MONTHS = [
  "فروردین",
  "اردیبهشت",
  "خرداد",
  "تیر",
  "مرداد",
  "شهریور",
  "مهر",
  "آبان",
  "آذر",
  "دی",
  "بهمن",
  "اسفند",
] as const;

/** Saturday first — the Iranian week. Index with jalaliWeekday(). */
export const J_WEEKDAYS = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه"] as const;
export const J_WEEKDAYS_SHORT = ["ش", "ی", "د", "س", "چ", "پ", "ج"] as const;

/** 0 = Saturday … 6 = Friday. (JDN 0 was a Monday, so Saturday ≡ 5 mod 7.) */
export function jalaliWeekday(jy: number, jm: number, jd: number): number {
  return mod(j2d(jy, jm, jd) + 2, 7);
}

/* ─── instants → Tehran calendar ─────────────────────────────────────────── */

export const TEHRAN_TZ = "Asia/Tehran";

/** Wall-clock fields of an instant in Tehran (Gregorian). */
export interface TehranParts {
  year: number;
  month: number;
  day: number;
  hour: number;
  minute: number;
  second: number;
}

/* Built once: constructing an Intl formatter costs tens of µs, and a 100-row
 * table formats several dates per row. undefined = not tried yet, null = this
 * engine has no tz data (some Hermes builds ship without full ICU). */
let tehranFormatter: Intl.DateTimeFormat | null | undefined;

function getTehranFormatter(): Intl.DateTimeFormat | null {
  if (tehranFormatter === undefined) {
    try {
      const f = new Intl.DateTimeFormat("en-US-u-ca-gregory-nu-latn", {
        timeZone: TEHRAN_TZ,
        year: "numeric",
        month: "numeric",
        day: "numeric",
        hour: "numeric",
        minute: "numeric",
        second: "numeric",
        hourCycle: "h23",
      });
      tehranFormatter = typeof f.formatToParts === "function" ? f : null;
    } catch {
      tehranFormatter = null;
    }
  }
  return tehranFormatter;
}

/** Fixed UTC+03:30. Exact for every instant since Iran abolished DST
 *  (Sept 2022); older summer instants can be an hour off. Only used when the
 *  engine lacks tz data. */
export function tehranPartsFixedOffset(instant: Date): TehranParts {
  const t = new Date(instant.getTime() + 210 * 60_000);
  return {
    year: t.getUTCFullYear(),
    month: t.getUTCMonth() + 1,
    day: t.getUTCDate(),
    hour: t.getUTCHours(),
    minute: t.getUTCMinutes(),
    second: t.getUTCSeconds(),
  };
}

export function tehranParts(instant: Date): TehranParts {
  const f = getTehranFormatter();
  if (!f) return tehranPartsFixedOffset(instant);
  const out: Record<string, number> = {};
  for (const p of f.formatToParts(instant)) {
    if (p.type !== "literal") out[p.type] = Number(p.value);
  }
  return {
    year: out.year ?? 0,
    month: out.month ?? 0,
    day: out.day ?? 0,
    // Some engines still print midnight as "24" even with h23.
    hour: (out.hour ?? 0) % 24,
    minute: out.minute ?? 0,
    second: out.second ?? 0,
  };
}

/** Date, epoch millis, ISO datetime string ("2026-10-11T08:00:00Z"), or a
 *  calendar date "YYYY-MM-DD". */
export type DateInput = Date | number | string;

const DATE_ONLY = /^(\d{4})-(\d{2})-(\d{2})$/;

interface CalendarDay {
  g: GregorianDate;
  /** Tehran wall-clock time, absent for date-only input. */
  time: { hour: number; minute: number } | null;
}

/* A "YYYY-MM-DD" (reading_date, a date picker value) is a calendar day, not an
 * instant: pushing it through `new Date()` makes it UTC midnight, and on a
 * device east of Tehran the local-midnight variant would land on the previous
 * day. So it is converted as-is. */
function calendarDay(input: DateInput): CalendarDay | null {
  if (typeof input === "string") {
    const m = DATE_ONLY.exec(input);
    if (m) {
      const g = { gy: Number(m[1]), gm: Number(m[2]), gd: Number(m[3]) };
      return g.gm >= 1 && g.gm <= 12 && g.gd >= 1 && g.gd <= 31 ? { g, time: null } : null;
    }
  }
  const d = input instanceof Date ? input : new Date(input);
  if (Number.isNaN(d.getTime())) return null;
  const p = tehranParts(d);
  return { g: { gy: p.year, gm: p.month, gd: p.day }, time: { hour: p.hour, minute: p.minute } };
}

/** Jalali calendar day (Tehran) of the input. Throws RangeError on an invalid date. */
export function toJalali(input: DateInput): JalaliDate {
  const c = calendarDay(input);
  if (!c) throw new RangeError(`Invalid date: ${String(input)}`);
  return gregorianToJalali(c.g.gy, c.g.gm, c.g.gd);
}

export function todayJalali(now: DateInput = new Date()): JalaliDate {
  return toJalali(now);
}

const p2 = (n: number) => String(n).padStart(2, "0");

/** "1405-07-19" Jalali → "YYYY-MM-DD" Gregorian (what the API takes for dates). */
export function jalaliToIsoDate(jy: number, jm: number, jd: number): string {
  if (!isValidJalaliDate(jy, jm, jd)) throw new RangeError(`Invalid Jalali date: ${jy}-${jm}-${jd}`);
  const g = jalaliToGregorian(jy, jm, jd);
  return `${String(g.gy).padStart(4, "0")}-${p2(g.gm)}-${p2(g.gd)}`;
}

/** "YYYY-MM-DD" Gregorian → Jalali, or null when it is not a valid date. */
export function isoDateToJalali(s: string): JalaliDate | null {
  const m = DATE_ONLY.exec(s);
  if (!m) return null;
  const gy = Number(m[1]);
  const gm = Number(m[2]);
  const gd = Number(m[3]);
  const j = gregorianToJalali(gy, gm, gd);
  const back = jalaliToGregorian(j.jy, j.jm, j.jd);
  // Round-trip rejects 2026-02-30 and friends, which the arithmetic would roll over.
  return back.gy === gy && back.gm === gm && back.gd === gd ? j : null;
}

/* ─── formatting ─────────────────────────────────────────────────────────── */

export type JalaliFormat = "short" | "long" | "full" | "monthYear" | "datetime";

const monthName = (jm: number) => J_MONTHS[jm - 1] ?? "";

/**
 * short     ۱۴۰۵/۰۷/۱۹
 * long      ۱۹ مهر ۱۴۰۵
 * full      یکشنبه ۱۹ مهر ۱۴۰۵
 * monthYear مهر ۱۴۰۵
 * datetime  ۱۴۰۵/۰۷/۱۹، ۱۴:۳۵   (date-only input falls back to short)
 * Invalid input → "—" so a bad row never crashes a screen.
 */
export function formatJalali(input: DateInput, style: JalaliFormat = "short"): string {
  const c = calendarDay(input);
  if (!c) return "—";
  const j = gregorianToJalali(c.g.gy, c.g.gm, c.g.gd);
  const short = toFa(`${j.jy}/${p2(j.jm)}/${p2(j.jd)}`);
  switch (style) {
    case "short":
      return short;
    case "long":
      return `${toFa(j.jd)} ${monthName(j.jm)} ${toFa(j.jy, false)}`;
    case "full":
      return `${J_WEEKDAYS[jalaliWeekday(j.jy, j.jm, j.jd)]} ${toFa(j.jd)} ${monthName(j.jm)} ${toFa(j.jy, false)}`;
    case "monthYear":
      return `${monthName(j.jm)} ${toFa(j.jy, false)}`;
    case "datetime":
      return c.time ? `${short}، ${toFa(`${p2(c.time.hour)}:${p2(c.time.minute)}`)}` : short;
  }
}

/* ─── periods ("1405-07") ────────────────────────────────────────────────── */

/**
 * "YYYY-MM" of the Jalali month containing the input, in Tehran — identical to
 * backend jalali.period_key. With multi-month periods the key is the first
 * month of the block (01, 03, 05… for 2), so keys stay string-comparable.
 */
export function periodKey(input: DateInput, monthsPerPeriod = 1): string {
  const j = toJalali(input);
  let m = j.jm;
  if (monthsPerPeriod > 1) m = div(m - 1, monthsPerPeriod) * monthsPerPeriod + 1;
  return `${String(j.jy).padStart(4, "0")}-${p2(m)}`;
}

const PERIOD = /^(\d{4})-(\d{2})$/;

/** Throws RangeError like the backend's parse_period (year ≥ 1300, month 1..12). */
export function parsePeriod(key: string): { jy: number; jm: number } {
  const m = PERIOD.exec(key);
  const jy = m ? Number(m[1]) : NaN;
  const jm = m ? Number(m[2]) : NaN;
  if (!m || jm < 1 || jm > 12 || jy < 1300) throw new RangeError(`Bad period key: ${key}`);
  return { jy, jm };
}

export function shiftPeriod(key: string, months: number): string {
  const { jy, jm } = parsePeriod(key);
  const idx = jy * 12 + (jm - 1) + months;
  return `${String(Math.floor(idx / 12)).padStart(4, "0")}-${p2((((idx % 12) + 12) % 12) + 1)}`;
}

/** "1405-07" → "مهر ۱۴۰۵". Invalid key → "—". */
export function periodLabel(key: string): string {
  try {
    const { jy, jm } = parsePeriod(key);
    return `${monthName(jm)} ${toFa(jy, false)}`;
  } catch {
    return "—";
  }
}

/* ─── relative time ──────────────────────────────────────────────────────── */

const MINUTE = 60_000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

function toMillis(input: DateInput): number {
  if (typeof input === "number") return input;
  if (input instanceof Date) return input.getTime();
  return new Date(input).getTime();
}

/**
 * "لحظاتی پیش", "۳ دقیقه پیش", "۲ ساعت پیش", "۵ روز پیش", "۲ ماه پیش",
 * "۱ سال پیش"; future instants use "دیگر" ("۱۰ دقیقه دیگر").
 * Elapsed-time based (a month = 30 days) — for exact dates use formatJalali.
 */
export function formatRelative(input: DateInput, now: DateInput = Date.now()): string {
  const t = toMillis(input);
  const n = toMillis(now);
  if (!Number.isFinite(t) || !Number.isFinite(n)) return "—";
  const diff = n - t;
  const abs = Math.abs(diff);
  const suffix = diff >= 0 ? "پیش" : "دیگر";
  if (abs < MINUTE) return `لحظاتی ${suffix}`;
  const unit = (count: number, word: string) => `${toFa(count)} ${word} ${suffix}`;
  if (abs < HOUR) return unit(Math.floor(abs / MINUTE), "دقیقه");
  if (abs < DAY) return unit(Math.floor(abs / HOUR), "ساعت");
  if (abs < 30 * DAY) return unit(Math.floor(abs / DAY), "روز");
  if (abs < 365 * DAY) return unit(Math.floor(abs / (30 * DAY)), "ماه");
  return unit(Math.floor(abs / (365 * DAY)), "سال");
}
