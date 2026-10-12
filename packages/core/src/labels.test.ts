import * as E from "./types/enums";
import * as L from "./labels";
import type { LabelMap } from "./labels";

/* Every enum array paired with its label map. The Record types already make a
 * missing key a compile error; this also catches empty strings, bad tones and
 * stale keys left in a map after a member is removed. */
const PAIRS: [string, readonly string[], LabelMap<string>][] = [
  ["STAFF_ROLE", E.STAFF_ROLES, L.STAFF_ROLE],
  ["USER_STATUS", E.USER_STATUSES, L.USER_STATUS],
  ["ELIGIBILITY", E.ELIGIBILITIES, L.ELIGIBILITY],
  ["LOGIN_METHOD", E.LOGIN_METHODS, L.LOGIN_METHOD],
  ["IMPORT_KIND", E.IMPORT_KINDS, L.IMPORT_KIND],
  ["IMPORT_STATUS", E.IMPORT_STATUSES, L.IMPORT_STATUS],
  ["READING_STATUS", E.READING_STATUSES, L.READING_STATUS],
  ["READING_KIND", E.READING_KINDS, L.READING_KIND],
  ["READING_INPUT_METHOD", E.READING_INPUT_METHODS, L.READING_INPUT_METHOD],
  ["ANOMALY", E.ANOMALY_CODES, L.ANOMALY],
  ["CASE_STATUS", E.CASE_STATUSES, L.CASE_STATUS],
  ["TIER", E.TIERS, L.TIER],
  ["CASE_OPENED_REASON", E.CASE_OPENED_REASONS, L.CASE_OPENED_REASON],
  ["ASSIGNMENT_METHOD", E.ASSIGNMENT_METHODS, L.ASSIGNMENT_METHOD],
  ["CALL_OUTCOME", E.CALL_OUTCOMES, L.CALL_OUTCOME],
  ["PHOTO_PHASE", E.PHOTO_PHASES, L.PHOTO_PHASE],
  ["ESTIMATE_STATUS", E.ESTIMATE_STATUSES, L.ESTIMATE_STATUS],
  ["HEATING_EQUIPMENT_TYPE", E.HEATING_EQUIPMENT_TYPES, L.HEATING_EQUIPMENT_TYPE],
  ["EQUIPMENT_CONDITION", E.EQUIPMENT_CONDITIONS, L.EQUIPMENT_CONDITION],
  ["INSULATION", E.INSULATION_OPTIONS, L.INSULATION],
  ["WINDOW_SEAL", E.WINDOW_SEAL_OPTIONS, L.WINDOW_SEAL],
  ["CHIMNEY", E.CHIMNEY_OPTIONS, L.CHIMNEY],
  ["BUILDING_TYPE", E.BUILDING_TYPES, L.BUILDING_TYPE],
  ["POINTS_STATUS", E.POINTS_STATUSES, L.POINTS_STATUS],
  ["POINTS_EVENT", E.POINTS_EVENT_TYPES, L.POINTS_EVENT],
  ["REFERRAL_STATUS", E.REFERRAL_STATUSES, L.REFERRAL_STATUS],
  ["REDEMPTION_STATUS", E.REDEMPTION_STATUSES, L.REDEMPTION_STATUS],
  ["REDEMPTION_KIND", E.REDEMPTION_KINDS, L.REDEMPTION_KIND],
  ["TICKET_STATUS", E.TICKET_STATUSES, L.TICKET_STATUS],
  ["TICKET_PRIORITY", E.TICKET_PRIORITIES, L.TICKET_PRIORITY],
  ["TICKET_UNIT", E.TICKET_UNITS, L.TICKET_UNIT],
  ["TICKET_SUBJECT", E.TICKET_SUBJECTS, L.TICKET_SUBJECT],
];

describe("label maps", () => {
  it.each(PAIRS)("%s labels exactly every enum member", (_name, members, map) => {
    expect(Object.keys(map).sort()).toEqual([...members].sort());
    for (const m of members) {
      const label = map[m]!;
      expect(label.fa.trim(), m).not.toBe("");
      expect(L.TONES, m).toContain(label.tone);
      // Labels are Persian: Latin letters would break RTL runs, and any ASCII
      // digit would skip the Persian-digit rule.
      expect(label.fa, m).not.toMatch(/[A-Za-z0-9]/);
    }
  });

  it("covers the architecture's case states and roles", () => {
    expect(E.CASE_STATUSES).toHaveLength(14);
    expect(L.STAFF_ROLE.super_admin.fa).toBe("مدیر سامانه");
    expect(L.STAFF_ROLE.operator.fa).toBe("اپراتور");
    expect(L.STAFF_ROLE.technician.fa).toBe("کارشناس فنی");
    expect(L.STAFF_ROLE.ambassador.fa).toBe("سفیر");
    expect(L.STAFF_ROLE.finance.fa).toBe("واحد مالی");
    expect(L.TIER.no_cost.fa).toBe("بدون‌هزینه");
    expect(L.TIER.low_cost.fa).toBe("کم‌هزینه");
    expect(L.TIER.high_cost.fa).toBe("پرهزینه");
    expect(L.READING_STATUS.pending.fa).toBe("در انتظار بررسی");
  });

  it("has unique labels within a map so filter chips are distinguishable", () => {
    for (const [name, members, map] of PAIRS) {
      const fas = members.map((m) => map[m]!.fa);
      expect(new Set(fas).size, name).toBe(fas.length);
    }
  });
});

describe("labelOf / labelOptions", () => {
  it("returns the label, or نامشخص for unknown wire values", () => {
    expect(L.labelOf(L.READING_STATUS, "approved")).toEqual({ fa: "تأییدشده", tone: "ok" });
    expect(L.labelOf(L.READING_STATUS, "brand_new_state")).toEqual({ fa: "نامشخص", tone: "neutral" });
    expect(L.labelOf(L.READING_STATUS, null).fa).toBe("نامشخص");
    expect(L.labelOf(L.READING_STATUS, undefined).fa).toBe("نامشخص");
    // Prototype keys must not leak through as labels.
    expect(L.labelOf(L.READING_STATUS, "toString").fa).toBe("نامشخص");
  });

  it("lists options in declaration order", () => {
    expect(L.labelOptions(L.TIER)).toEqual([
      { value: "no_cost", fa: "بدون‌هزینه", tone: "ok" },
      { value: "low_cost", fa: "کم‌هزینه", tone: "info" },
      { value: "high_cost", fa: "پرهزینه", tone: "warn" },
    ]);
  });
});

describe("isOneOf", () => {
  it("narrows wire values", () => {
    expect(E.isOneOf(E.TIERS, "low_cost")).toBe(true);
    expect(E.isOneOf(E.TIERS, "LOW_COST")).toBe(false);
    expect(E.isOneOf(E.TIERS, 3)).toBe(false);
    expect(E.PERMISSIONS).toContain("settings.finance_edit");
    expect(new Set(E.PERMISSIONS).size).toBe(E.PERMISSIONS.length);
  });
});
