/* The fixture is the contract shared with backend/app/core (normalize.py,
 * validators.py). These tests only iterate it; to add a case, add it to the
 * JSON so the backend suite checks it too. */

import fixture from "../../fixtures/normalize.json";
import { toEn } from "./digits";
import {
  isValidIban,
  isValidNationalCode,
  maskMobile,
  normalizeIban,
  normalizeMobile,
  normalizeSubscription,
  normalizeText,
} from "./normalize";

const show = (s: string) => JSON.stringify(s);

describe("normalize.json fixture shape", () => {
  it("has every section with at least 12 cases", () => {
    const sections = ["digits", "text", "mobile", "subscription", "national_code", "iban"] as const;
    expect(Object.keys(fixture).sort()).toEqual([...sections].sort());
    for (const s of sections) expect(fixture[s].length, s).toBeGreaterThanOrEqual(12);
  });

  it("outputs are ASCII where the contract says so", () => {
    for (const c of fixture.mobile) if (c.out !== null) expect(c.out).toMatch(/^09[0-9]{9}$/);
    for (const c of fixture.subscription) if (c.out !== null) expect(c.out).toMatch(/^[0-9]{4,20}$/);
    for (const c of fixture.iban) if (c.out !== null) expect(c.out).toMatch(/^IR[0-9]{24}$/);
  });
});

describe("toEn (fixture: digits)", () => {
  for (const c of fixture.digits) {
    it(`${show(c.in)} → ${show(c.out)}`, () => expect(toEn(c.in)).toBe(c.out));
  }
});

describe("normalizeText (fixture: text)", () => {
  for (const c of fixture.text) {
    it(`${show(c.in)} → ${show(c.out)}`, () => expect(normalizeText(c.in)).toBe(c.out));
  }

  it("is idempotent", () => {
    for (const c of fixture.text) expect(normalizeText(normalizeText(c.in))).toBe(c.out);
  });
});

describe("normalizeMobile (fixture: mobile)", () => {
  for (const c of fixture.mobile) {
    it(`${show(c.in)} → ${String(c.out)}`, () => expect(normalizeMobile(c.in)).toBe(c.out));
  }

  it("treats null/undefined as invalid", () => {
    expect(normalizeMobile(null)).toBeNull();
    expect(normalizeMobile(undefined)).toBeNull();
  });
});

describe("normalizeSubscription (fixture: subscription)", () => {
  for (const c of fixture.subscription) {
    it(`${show(c.in)} → ${String(c.out)}`, () => expect(normalizeSubscription(c.in)).toBe(c.out));
  }

  it("accepts a number but cannot recover leading zeros from it", () => {
    expect(normalizeSubscription(12345678)).toBe("12345678");
    expect(normalizeSubscription(null)).toBeNull();
  });
});

describe("isValidNationalCode (fixture: national_code)", () => {
  for (const c of fixture.national_code) {
    it(`${show(c.in)} → ${String(c.valid)}`, () => expect(isValidNationalCode(c.in)).toBe(c.valid));
  }
});

describe("normalizeIban / isValidIban (fixture: iban)", () => {
  for (const c of fixture.iban) {
    it(`${show(c.in)} → ${String(c.out)} (${c.valid ? "valid" : "invalid"})`, () => {
      expect(normalizeIban(c.in)).toBe(c.out);
      expect(isValidIban(c.in)).toBe(c.valid);
    });
  }

  it("never calls a checksum-invalid IBAN valid when only one digit changes", () => {
    const good = "IR820540102680020817909002";
    for (let i = 4; i < good.length; i++) {
      const d = Number(good[i]);
      const bad = good.slice(0, i) + String((d + 1) % 10) + good.slice(i + 1);
      expect(isValidIban(bad), bad).toBe(false);
    }
  });
});

describe("maskMobile", () => {
  it("keeps the operator prefix and the last four digits", () => {
    expect(maskMobile("09121234567")).toBe("0912***4567");
  });

  it("returns a dash for missing or too-short values", () => {
    expect(maskMobile(null)).toBe("—");
    expect(maskMobile("")).toBe("—");
    expect(maskMobile("0912")).toBe("—");
  });
});
