import {
  formatJalali,
  formatRelative,
  gregorianToJalali,
  isJalaliLeapYear,
  isoDateToJalali,
  isValidJalaliDate,
  J_MONTHS,
  J_WEEKDAYS,
  jalaliToGregorian,
  jalaliToIsoDate,
  jalaliWeekday,
  jDaysInMonth,
  parsePeriod,
  periodKey,
  periodLabel,
  shiftPeriod,
  tehranParts,
  tehranPartsFixedOffset,
  toJalali,
} from "./jalali";

describe("gregorian ↔ jalali", () => {
  it("converts the known pairs", () => {
    expect(gregorianToJalali(2026, 10, 11)).toEqual({ jy: 1405, jm: 7, jd: 19 });
    expect(gregorianToJalali(2025, 3, 21)).toEqual({ jy: 1404, jm: 1, jd: 1 });
    expect(gregorianToJalali(2025, 3, 20)).toEqual({ jy: 1403, jm: 12, jd: 30 });
    expect(gregorianToJalali(2024, 3, 20)).toEqual({ jy: 1403, jm: 1, jd: 1 });
    expect(gregorianToJalali(2026, 1, 1)).toEqual({ jy: 1404, jm: 10, jd: 11 });
    expect(jalaliToGregorian(1405, 7, 19)).toEqual({ gy: 2026, gm: 10, gd: 11 });
    expect(jalaliToGregorian(1404, 1, 1)).toEqual({ gy: 2025, gm: 3, gd: 21 });
  });

  it("round-trips every day of 1380–1420", () => {
    for (let jy = 1380; jy <= 1420; jy++) {
      for (let jm = 1; jm <= 12; jm++) {
        for (let jd = 1; jd <= jDaysInMonth(jy, jm); jd++) {
          const g = jalaliToGregorian(jy, jm, jd);
          expect(gregorianToJalali(g.gy, g.gm, g.gd)).toEqual({ jy, jm, jd });
        }
      }
    }
  });

  it("agrees with the engine's ICU Persian calendar day by day (1995–2045)", () => {
    const icu = new Intl.DateTimeFormat("en-u-ca-persian-nu-latn", {
      timeZone: "UTC",
      year: "numeric",
      month: "numeric",
      day: "numeric",
    });
    const start = Date.UTC(1995, 0, 1);
    const end = Date.UTC(2045, 11, 31);
    for (let t = start; t <= end; t += 86_400_000) {
      const d = new Date(t);
      const parts: Record<string, number> = {};
      for (const p of icu.formatToParts(d)) if (p.type !== "literal") parts[p.type] = Number(p.value);
      const j = gregorianToJalali(d.getUTCFullYear(), d.getUTCMonth() + 1, d.getUTCDate());
      expect(j, d.toISOString()).toEqual({ jy: parts.year, jm: parts.month, jd: parts.day });
    }
  });

  it("is consecutive across every year boundary (no gaps, no duplicates)", () => {
    let prev = gregorianToJalali(2000, 1, 1);
    for (let t = Date.UTC(2000, 0, 2); t <= Date.UTC(2040, 0, 1); t += 86_400_000) {
      const d = new Date(t);
      const j = gregorianToJalali(d.getUTCFullYear(), d.getUTCMonth() + 1, d.getUTCDate());
      if (j.jd !== 1) expect(j).toEqual({ ...prev, jd: prev.jd + 1 });
      else expect(prev.jd).toBe(jDaysInMonth(prev.jy, prev.jm));
      prev = j;
    }
  });
});

describe("leap years and month lengths", () => {
  it("knows Esfand 1403 has 30 days and 1404 has 29", () => {
    expect(isJalaliLeapYear(1403)).toBe(true);
    expect(jDaysInMonth(1403, 12)).toBe(30);
    expect(isJalaliLeapYear(1404)).toBe(false);
    expect(jDaysInMonth(1404, 12)).toBe(29);
    expect(isJalaliLeapYear(1399)).toBe(true);
    expect(isJalaliLeapYear(1408)).toBe(true);
  });

  it("has 31-day first half and 30-day second half", () => {
    for (let m = 1; m <= 6; m++) expect(jDaysInMonth(1405, m)).toBe(31);
    for (let m = 7; m <= 11; m++) expect(jDaysInMonth(1405, m)).toBe(30);
  });

  it("validates Jalali dates", () => {
    expect(isValidJalaliDate(1403, 12, 30)).toBe(true);
    expect(isValidJalaliDate(1404, 12, 30)).toBe(false);
    expect(isValidJalaliDate(1405, 7, 31)).toBe(false);
    expect(isValidJalaliDate(1405, 13, 1)).toBe(false);
    expect(isValidJalaliDate(1405, 0, 1)).toBe(false);
    expect(isValidJalaliDate(1405.5, 1, 1)).toBe(false);
  });
});

describe("names and weekdays", () => {
  it("has 12 months starting at Farvardin and a Saturday-first week", () => {
    expect(J_MONTHS).toHaveLength(12);
    expect(J_MONTHS[0]).toBe("فروردین");
    expect(J_MONTHS[6]).toBe("مهر");
    expect(J_WEEKDAYS[0]).toBe("شنبه");
    expect(J_WEEKDAYS[6]).toBe("جمعه");
  });

  it("computes weekdays (0 = Saturday)", () => {
    expect(jalaliWeekday(1405, 7, 19)).toBe(1); // Sunday 2026-10-11
    expect(jalaliWeekday(1404, 1, 1)).toBe(6); // Friday 2025-03-21
    expect(jalaliWeekday(1405, 7, 18)).toBe(0); // Saturday
  });
});

describe("Tehran calendar day", () => {
  it("reads wall-clock time in Asia/Tehran", () => {
    expect(tehranParts(new Date("2026-10-11T11:05:00Z"))).toEqual({
      year: 2026,
      month: 10,
      day: 11,
      hour: 14,
      minute: 35,
      second: 0,
    });
  });

  it("matches the fixed +03:30 fallback for post-DST instants", () => {
    for (const iso of ["2026-10-11T20:29:59Z", "2026-10-11T20:30:00Z", "2025-03-20T20:30:00Z", "2026-06-01T00:00:00Z"]) {
      expect(tehranPartsFixedOffset(new Date(iso))).toEqual(tehranParts(new Date(iso)));
    }
  });

  it("treats YYYY-MM-DD as a calendar day, not an instant", () => {
    expect(toJalali("2026-10-11")).toEqual({ jy: 1405, jm: 7, jd: 19 });
    expect(toJalali("2026-10-11T22:00:00Z")).toEqual({ jy: 1405, jm: 7, jd: 20 });
  });

  it("throws on an invalid date", () => {
    expect(() => toJalali("not a date")).toThrow(RangeError);
  });

  it("converts to and from ISO dates", () => {
    expect(jalaliToIsoDate(1405, 7, 19)).toBe("2026-10-11");
    expect(jalaliToIsoDate(1403, 12, 30)).toBe("2025-03-20");
    expect(() => jalaliToIsoDate(1404, 12, 30)).toThrow(RangeError);
    expect(isoDateToJalali("2026-10-11")).toEqual({ jy: 1405, jm: 7, jd: 19 });
    expect(isoDateToJalali("2026-02-30")).toBeNull();
    expect(isoDateToJalali("2026/10/11")).toBeNull();
  });
});

describe("formatJalali", () => {
  it("formats every style with Persian digits", () => {
    expect(formatJalali("2026-10-11", "short")).toBe("۱۴۰۵/۰۷/۱۹");
    expect(formatJalali("2026-10-11", "long")).toBe("۱۹ مهر ۱۴۰۵");
    expect(formatJalali("2026-10-11", "full")).toBe("یکشنبه ۱۹ مهر ۱۴۰۵");
    expect(formatJalali("2026-10-11", "monthYear")).toBe("مهر ۱۴۰۵");
    expect(formatJalali("2026-10-11T11:05:00Z", "datetime")).toBe("۱۴۰۵/۰۷/۱۹، ۱۴:۳۵");
  });

  it("defaults to short, accepts Date and epoch millis", () => {
    const d = new Date("2025-03-21T08:00:00Z");
    expect(formatJalali(d)).toBe("۱۴۰۴/۰۱/۰۱");
    expect(formatJalali(d.getTime(), "long")).toBe("۱ فروردین ۱۴۰۴");
  });

  it("falls back to short for a date-only datetime, and to a dash on bad input", () => {
    expect(formatJalali("2026-10-11", "datetime")).toBe("۱۴۰۵/۰۷/۱۹");
    expect(formatJalali("garbage")).toBe("—");
    expect(formatJalali("2026-13-01")).toBe("—");
    expect(formatJalali(Number.NaN)).toBe("—");
  });
});

describe("periods", () => {
  it("keys an instant by its Tehran Jalali month", () => {
    expect(periodKey("2026-10-11")).toBe("1405-07");
    expect(periodKey(new Date("2026-10-11T08:00:00Z"))).toBe("1405-07");
  });

  it("switches period at Tehran midnight, not UTC midnight", () => {
    // 1405-08-01 begins 2026-10-23 00:00 Tehran = 2026-10-22 20:30 UTC.
    expect(periodKey("2026-10-22T20:29:59Z")).toBe("1405-07");
    expect(periodKey("2026-10-22T20:30:00Z")).toBe("1405-08");
    // Same UTC calendar day, two different periods:
    expect(periodKey("2026-10-22T23:59:59Z")).toBe("1405-08");
    // Nowruz: 1405-01-01 begins 2026-03-21 00:00 Tehran = 2026-03-20 20:30 UTC.
    expect(periodKey("2026-03-20T20:29:00Z")).toBe("1404-12");
    expect(periodKey("2026-03-20T20:31:00Z")).toBe("1405-01");
  });

  it("supports multi-month blocks keyed by their first month", () => {
    expect(periodKey("2026-10-11", 2)).toBe("1405-07");
    expect(periodKey("2026-11-01", 2)).toBe("1405-07"); // 1405-08-10
    expect(periodKey("2026-11-01", 3)).toBe("1405-07");
    expect(periodKey("2026-09-01", 3)).toBe("1405-04"); // 1405-06-10
  });

  it("labels, parses and shifts period keys", () => {
    expect(periodLabel("1405-07")).toBe("مهر ۱۴۰۵");
    expect(periodLabel("1404-12")).toBe("اسفند ۱۴۰۴");
    expect(periodLabel("1405-13")).toBe("—");
    expect(periodLabel("bad")).toBe("—");
    expect(parsePeriod("1405-07")).toEqual({ jy: 1405, jm: 7 });
    expect(() => parsePeriod("1405-7")).toThrow(RangeError);
    expect(shiftPeriod("1405-01", -1)).toBe("1404-12");
    expect(shiftPeriod("1405-12", 1)).toBe("1406-01");
    expect(shiftPeriod("1405-07", -36)).toBe("1402-07");
  });
});

describe("formatRelative", () => {
  const now = new Date("2026-10-11T12:00:00Z");
  const ago = (ms: number) => new Date(now.getTime() - ms);

  it("speaks Persian with Persian digits", () => {
    expect(formatRelative(ago(20_000), now)).toBe("لحظاتی پیش");
    expect(formatRelative(ago(3 * 60_000), now)).toBe("۳ دقیقه پیش");
    expect(formatRelative(ago(2 * 3_600_000), now)).toBe("۲ ساعت پیش");
    expect(formatRelative(ago(5 * 86_400_000), now)).toBe("۵ روز پیش");
    expect(formatRelative(ago(65 * 86_400_000), now)).toBe("۲ ماه پیش");
    expect(formatRelative(ago(400 * 86_400_000), now)).toBe("۱ سال پیش");
  });

  it("handles the future and bad input", () => {
    expect(formatRelative(new Date(now.getTime() + 10 * 60_000), now)).toBe("۱۰ دقیقه دیگر");
    expect(formatRelative("nope", now)).toBe("—");
  });
});
