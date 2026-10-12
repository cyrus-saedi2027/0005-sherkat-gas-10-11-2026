/* Domain enums from docs/ARCHITECTURE.md §3/§4.3, as runtime arrays + unions.
 * The arrays exist so tests (and pickers/filters) can iterate every member;
 * the label maps in labels.ts are typed Record<Union, …>, so adding a member
 * here without a label is a compile error. Values are the exact wire strings. */

/* §3.1 identity & access */
export const STAFF_ROLES = ["super_admin", "operator", "technician", "ambassador", "finance"] as const;
export type StaffRole = (typeof STAFF_ROLES)[number];

export const USER_STATUSES = ["active", "suspended"] as const;
export type UserStatus = (typeof USER_STATUSES)[number];

export const ELIGIBILITIES = ["eligible", "below_threshold"] as const;
export type Eligibility = (typeof ELIGIBILITIES)[number];

export const LOGIN_METHODS = ["otp", "password"] as const;
export type LoginMethod = (typeof LOGIN_METHODS)[number];

/* §3.2 reference data */
export const IMPORT_KINDS = ["subscribers", "consumption"] as const;
export type ImportKind = (typeof IMPORT_KINDS)[number];

export const IMPORT_STATUSES = ["validated", "committed", "failed"] as const;
export type ImportStatus = (typeof IMPORT_STATUSES)[number];

/* §3.4 readings */
export const READING_STATUSES = ["pending", "flagged", "needs_correction", "rejected", "approved"] as const;
export type ReadingStatus = (typeof READING_STATUSES)[number];

export const READING_KINDS = ["initial", "correction", "review_request"] as const;
export type ReadingKind = (typeof READING_KINDS)[number];

export const READING_INPUT_METHODS = ["photo", "manual"] as const;
export type ReadingInputMethod = (typeof READING_INPUT_METHODS)[number];

export const ANOMALY_CODES = [
  "meter_rollback",
  "sudden_drop",
  "zero_consumption",
  "spike",
  "duplicate_photo",
  "exif_mismatch",
  "future_date",
  "stale_date",
] as const;
export type AnomalyCode = (typeof ANOMALY_CODES)[number];

/* §3.5 cases */
export const CASE_STATUSES = [
  "new",
  "assigned",
  "contacted",
  "evaluated",
  "visit_scheduled",
  "visited",
  "awaiting_consent",
  "consent_given",
  "consent_declined",
  "in_execution",
  "pending_final_approval",
  "completed",
  "cancelled",
  "closed_no_action",
] as const;
export type CaseStatus = (typeof CASE_STATUSES)[number];

export const TIERS = ["no_cost", "low_cost", "high_cost"] as const;
export type Tier = (typeof TIERS)[number];

export const CASE_OPENED_REASONS = ["first_approved_reading", "anomaly", "manual"] as const;
export type CaseOpenedReason = (typeof CASE_OPENED_REASONS)[number];

export const ASSIGNMENT_METHODS = ["auto", "manual"] as const;
export type AssignmentMethod = (typeof ASSIGNMENT_METHODS)[number];

export const CALL_OUTCOMES = ["reached", "no_answer", "wrong_number", "callback"] as const;
export type CallOutcome = (typeof CALL_OUTCOMES)[number];

export const PHOTO_PHASES = ["before", "after"] as const;
export type PhotoPhase = (typeof PHOTO_PHASES)[number];

export const ESTIMATE_STATUSES = ["draft", "sent", "accepted", "declined"] as const;
export type EstimateStatus = (typeof ESTIMATE_STATUSES)[number];

/* §3.5 checklist (case_checklists). The contract names the fields, not their
 * options; these keys are the proposed wire values for both sides. */
export const HEATING_EQUIPMENT_TYPES = [
  "heater",
  "package_boiler",
  "water_heater",
  "central_boiler",
  "fireplace",
  "stove",
  "other",
] as const;
export type HeatingEquipmentType = (typeof HEATING_EQUIPMENT_TYPES)[number];

export const EQUIPMENT_CONDITIONS = ["good", "needs_service", "worn_out", "not_working"] as const;
export type EquipmentCondition = (typeof EQUIPMENT_CONDITIONS)[number];

export const INSULATION_OPTIONS = ["good", "partial", "none", "unknown"] as const;
export type InsulationOption = (typeof INSULATION_OPTIONS)[number];

export const WINDOW_SEAL_OPTIONS = ["good", "partial", "none"] as const;
export type WindowSealOption = (typeof WINDOW_SEAL_OPTIONS)[number];

export const CHIMNEY_OPTIONS = ["standard", "needs_repair", "blocked", "none"] as const;
export type ChimneyOption = (typeof CHIMNEY_OPTIONS)[number];

export const BUILDING_TYPES = ["apartment", "house", "other"] as const;
export type BuildingType = (typeof BUILDING_TYPES)[number];

/* §3.6 points */
export const POINTS_STATUSES = ["pending", "available", "suspended", "reversed"] as const;
export type PointsStatus = (typeof POINTS_STATUSES)[number];

export const POINTS_EVENT_TYPES = [
  "signup",
  "profile_completed",
  "valid_reading",
  "consumption_reduction",
  "ambassador_cooperation",
  "referral_success",
  "survey_completed",
  "optimization_executed",
] as const;
export type PointsEventType = (typeof POINTS_EVENT_TYPES)[number];

/* §3.7 referrals */
export const REFERRAL_STATUSES = ["pending", "rewarded", "capped", "suspicious", "rejected"] as const;
export type ReferralStatus = (typeof REFERRAL_STATUSES)[number];

/* §3.9 store */
export const REDEMPTION_STATUSES = ["submitted", "approved", "rejected", "fulfilled", "cancelled"] as const;
export type RedemptionStatus = (typeof REDEMPTION_STATUSES)[number];

export const REDEMPTION_KINDS = ["product", "discount", "cash", "donation"] as const;
export type RedemptionKind = (typeof REDEMPTION_KINDS)[number];

/* §3.10 tickets */
export const TICKET_STATUSES = ["open", "in_progress", "awaiting_customer", "answered", "resolved", "closed"] as const;
export type TicketStatus = (typeof TICKET_STATUSES)[number];

export const TICKET_PRIORITIES = ["low", "normal", "high", "urgent"] as const;
export type TicketPriority = (typeof TICKET_PRIORITIES)[number];

export const TICKET_UNITS = ["support", "technical", "finance", "ambassador"] as const;
export type TicketUnit = (typeof TICKET_UNITS)[number];

export const TICKET_SUBJECTS = ["reading", "points", "store", "case", "technical", "account", "other"] as const;
export type TicketSubject = (typeof TICKET_SUBJECTS)[number];

/* §4.3 RBAC — the server decides; clients only hide what would be refused. */
export const PERMISSIONS = [
  "dashboard.view",
  "subscribers.view",
  "subscribers.import",
  "subscribers.edit",
  "users.view",
  "users.suspend",
  "readings.view",
  "readings.review",
  "readings.correct_value",
  "cases.view_all",
  "cases.view_own",
  "cases.assign",
  "cases.work",
  "cases.final_approve",
  "points.view",
  "points.rules_edit",
  "points.adjust",
  "points.suspend",
  "referrals.view",
  "referrals.review",
  "rewards.view",
  "rewards.manage",
  "redemptions.view",
  "redemptions.review",
  "redemptions.fulfill",
  "tickets.view",
  "tickets.handle",
  "content.view",
  "content.manage",
  "notifications.broadcast",
  "surveys.view",
  "surveys.manage",
  "reports.view",
  "reports.export",
  "settings.view",
  "settings.edit",
  "settings.finance_edit",
  "staff.view",
  "staff.manage",
  "access_review.perform",
  "audit.view",
  "data.delete",
] as const;
export type Permission = (typeof PERMISSIONS)[number];

/** Narrowing guard for values arriving over the wire. */
export function isOneOf<const T extends readonly string[]>(values: T, v: unknown): v is T[number] {
  return typeof v === "string" && (values as readonly string[]).includes(v);
}
