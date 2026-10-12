/* Persian labels + a semantic tone for every domain enum.
 * Tone is a meaning, not a colour: packages/ui maps it to the palette, so a
 * theme change never touches this file. Maps are Record<Union, Label>, so a
 * new enum member in types/enums.ts without a label fails to compile. */

import type {
  AnomalyCode,
  AssignmentMethod,
  BuildingType,
  CallOutcome,
  CaseOpenedReason,
  CaseStatus,
  ChimneyOption,
  Eligibility,
  EquipmentCondition,
  EstimateStatus,
  HeatingEquipmentType,
  ImportKind,
  ImportStatus,
  InsulationOption,
  LoginMethod,
  PhotoPhase,
  PointsEventType,
  PointsStatus,
  ReadingInputMethod,
  ReadingKind,
  ReadingStatus,
  RedemptionKind,
  RedemptionStatus,
  ReferralStatus,
  StaffRole,
  TicketPriority,
  TicketStatus,
  TicketSubject,
  TicketUnit,
  Tier,
  UserStatus,
  WindowSealOption,
} from "./types/enums";

export type Tone = "ok" | "warn" | "crit" | "info" | "neutral" | "accent";
export const TONES: readonly Tone[] = ["ok", "warn", "crit", "info", "neutral", "accent"];

export interface Label {
  fa: string;
  tone: Tone;
}

export type LabelMap<K extends string> = Readonly<Record<K, Label>>;

const L = (fa: string, tone: Tone = "neutral"): Label => ({ fa, tone });

/* ─── identity ───────────────────────────────────────────────────────────── */

export const STAFF_ROLE: LabelMap<StaffRole> = {
  super_admin: L("مدیر سامانه", "accent"),
  operator: L("اپراتور", "info"),
  technician: L("کارشناس فنی", "info"),
  ambassador: L("سفیر", "info"),
  finance: L("واحد مالی", "info"),
};

export const USER_STATUS: LabelMap<UserStatus> = {
  active: L("فعال", "ok"),
  suspended: L("تعلیق‌شده", "crit"),
};

export const ELIGIBILITY: LabelMap<Eligibility> = {
  eligible: L("واجد شرایط", "ok"),
  below_threshold: L("زیر آستانه", "warn"),
};

export const LOGIN_METHOD: LabelMap<LoginMethod> = {
  otp: L("کد یک‌بارمصرف"),
  password: L("رمز عبور"),
};

export const IMPORT_KIND: LabelMap<ImportKind> = {
  subscribers: L("فهرست مشترکان"),
  consumption: L("سابقهٔ مصرف"),
};

export const IMPORT_STATUS: LabelMap<ImportStatus> = {
  validated: L("اعتبارسنجی‌شده", "info"),
  committed: L("ثبت‌شده", "ok"),
  failed: L("ناموفق", "crit"),
};

/* ─── readings ───────────────────────────────────────────────────────────── */

export const READING_STATUS: LabelMap<ReadingStatus> = {
  pending: L("در انتظار بررسی", "info"),
  flagged: L("نیازمند بررسی دستی", "warn"),
  needs_correction: L("نیازمند اصلاح", "warn"),
  rejected: L("ردشده", "crit"),
  approved: L("تأییدشده", "ok"),
};

export const READING_KIND: LabelMap<ReadingKind> = {
  initial: L("قرائت دوره", "neutral"),
  correction: L("اصلاحیه", "info"),
  review_request: L("درخواست بررسی مجدد", "accent"),
};

export const READING_INPUT_METHOD: LabelMap<ReadingInputMethod> = {
  photo: L("با عکس کنتور"),
  manual: L("ثبت دستی"),
};

export const ANOMALY: LabelMap<AnomalyCode> = {
  meter_rollback: L("عقب‌رفتن کنتور", "crit"),
  sudden_drop: L("افت ناگهانی مصرف", "warn"),
  zero_consumption: L("مصرف صفر", "warn"),
  spike: L("جهش مصرف", "warn"),
  duplicate_photo: L("عکس تکراری", "crit"),
  exif_mismatch: L("ناهمخوانی تاریخ عکس", "warn"),
  future_date: L("تاریخ آینده", "crit"),
  stale_date: L("تاریخ قدیمی", "warn"),
};

/* ─── cases ──────────────────────────────────────────────────────────────── */

export const CASE_STATUS: LabelMap<CaseStatus> = {
  new: L("جدید", "info"),
  assigned: L("ارجاع‌شده به سفیر", "info"),
  contacted: L("تماس گرفته‌شده", "info"),
  evaluated: L("ارزیابی‌شده", "info"),
  visit_scheduled: L("بازدید زمان‌بندی‌شده", "accent"),
  visited: L("بازدیدشده", "info"),
  awaiting_consent: L("در انتظار تأیید مشترک", "warn"),
  consent_given: L("تأییدشده توسط مشترک", "ok"),
  consent_declined: L("عدم تأیید مشترک", "crit"),
  in_execution: L("در حال اجرا", "accent"),
  pending_final_approval: L("در انتظار تأیید نهایی", "warn"),
  completed: L("تکمیل‌شده", "ok"),
  cancelled: L("لغوشده", "neutral"),
  closed_no_action: L("بسته‌شده بدون اقدام", "neutral"),
};

export const TIER: LabelMap<Tier> = {
  no_cost: L("بدون‌هزینه", "ok"),
  low_cost: L("کم‌هزینه", "info"),
  high_cost: L("پرهزینه", "warn"),
};

export const CASE_OPENED_REASON: LabelMap<CaseOpenedReason> = {
  first_approved_reading: L("اولین قرائت تأییدشده", "info"),
  anomaly: L("ناهماهنگی در مصرف", "warn"),
  manual: L("ایجاد دستی", "neutral"),
};

export const ASSIGNMENT_METHOD: LabelMap<AssignmentMethod> = {
  auto: L("ارجاع خودکار", "info"),
  manual: L("ارجاع دستی", "neutral"),
};

export const CALL_OUTCOME: LabelMap<CallOutcome> = {
  reached: L("پاسخ داد", "ok"),
  no_answer: L("پاسخ نداد", "warn"),
  wrong_number: L("شمارهٔ اشتباه", "crit"),
  callback: L("تماس مجدد", "info"),
};

export const PHOTO_PHASE: LabelMap<PhotoPhase> = {
  before: L("قبل از اجرا"),
  after: L("بعد از اجرا", "ok"),
};

export const ESTIMATE_STATUS: LabelMap<EstimateStatus> = {
  draft: L("پیش‌نویس", "neutral"),
  sent: L("ارسال‌شده برای مشترک", "info"),
  accepted: L("پذیرفته‌شده", "ok"),
  declined: L("ردشده", "crit"),
};

export const HEATING_EQUIPMENT_TYPE: LabelMap<HeatingEquipmentType> = {
  heater: L("بخاری گازی"),
  package_boiler: L("پکیج"),
  water_heater: L("آبگرمکن"),
  central_boiler: L("موتورخانهٔ مرکزی"),
  fireplace: L("شومینه"),
  stove: L("اجاق گاز"),
  other: L("سایر"),
};

export const EQUIPMENT_CONDITION: LabelMap<EquipmentCondition> = {
  good: L("سالم", "ok"),
  needs_service: L("نیازمند سرویس", "warn"),
  worn_out: L("فرسوده", "crit"),
  not_working: L("از کار افتاده", "crit"),
};

export const INSULATION: LabelMap<InsulationOption> = {
  good: L("مناسب", "ok"),
  partial: L("ناقص", "warn"),
  none: L("ندارد", "crit"),
  unknown: L("نامشخص", "neutral"),
};

export const WINDOW_SEAL: LabelMap<WindowSealOption> = {
  good: L("درزگیری کامل", "ok"),
  partial: L("درزگیری ناقص", "warn"),
  none: L("بدون درزگیر", "crit"),
};

export const CHIMNEY: LabelMap<ChimneyOption> = {
  standard: L("استاندارد", "ok"),
  needs_repair: L("نیازمند اصلاح", "warn"),
  blocked: L("مسدود یا معیوب", "crit"),
  none: L("ندارد", "neutral"),
};

export const BUILDING_TYPE: LabelMap<BuildingType> = {
  apartment: L("آپارتمان"),
  house: L("ویلایی"),
  other: L("سایر"),
};

/* ─── points, referrals, store ───────────────────────────────────────────── */

export const POINTS_STATUS: LabelMap<PointsStatus> = {
  pending: L("در انتظار پایان ماه", "info"),
  available: L("قابل استفاده", "ok"),
  suspended: L("معلق", "warn"),
  reversed: L("برگشت‌خورده", "crit"),
};

export const POINTS_EVENT: LabelMap<PointsEventType> = {
  signup: L("ثبت‌نام", "accent"),
  profile_completed: L("تکمیل پروفایل", "accent"),
  valid_reading: L("قرائت معتبر ماهانه", "accent"),
  consumption_reduction: L("کاهش مصرف", "accent"),
  ambassador_cooperation: L("همکاری با سفیر", "accent"),
  referral_success: L("معرفی موفق", "accent"),
  survey_completed: L("شرکت در نظرسنجی", "accent"),
  optimization_executed: L("اجرای راهکار بهینه‌سازی", "accent"),
};

export const REFERRAL_STATUS: LabelMap<ReferralStatus> = {
  pending: L("در انتظار اولین قرائت", "info"),
  rewarded: L("پاداش داده‌شد", "ok"),
  capped: L("خارج از سقف ماهانه", "neutral"),
  suspicious: L("مشکوک", "warn"),
  rejected: L("ردشده", "crit"),
};

export const REDEMPTION_STATUS: LabelMap<RedemptionStatus> = {
  submitted: L("ثبت‌شده", "info"),
  approved: L("تأییدشده", "accent"),
  rejected: L("ردشده", "crit"),
  fulfilled: L("انجام‌شده", "ok"),
  cancelled: L("لغوشده", "neutral"),
};

export const REDEMPTION_KIND: LabelMap<RedemptionKind> = {
  product: L("کالا", "accent"),
  discount: L("تخفیف", "accent"),
  cash: L("برداشت نقدی", "accent"),
  donation: L("اهدا به خیریه", "accent"),
};

/* ─── tickets ────────────────────────────────────────────────────────────── */

export const TICKET_STATUS: LabelMap<TicketStatus> = {
  open: L("باز", "info"),
  in_progress: L("در حال بررسی", "accent"),
  awaiting_customer: L("در انتظار پاسخ مشترک", "warn"),
  answered: L("پاسخ داده‌شده", "ok"),
  resolved: L("حل‌شده", "ok"),
  closed: L("بسته‌شده", "neutral"),
};

export const TICKET_PRIORITY: LabelMap<TicketPriority> = {
  low: L("کم", "neutral"),
  normal: L("عادی", "info"),
  high: L("زیاد", "warn"),
  urgent: L("فوری", "crit"),
};

export const TICKET_UNIT: LabelMap<TicketUnit> = {
  support: L("پشتیبانی", "info"),
  technical: L("فنی", "info"),
  finance: L("مالی", "info"),
  ambassador: L("سفیران", "info"),
};

export const TICKET_SUBJECT: LabelMap<TicketSubject> = {
  reading: L("قرائت کنتور"),
  points: L("امتیاز و کیف پول"),
  store: L("فروشگاه و جوایز"),
  case: L("پرونده و بازدید"),
  technical: L("مشکل فنی برنامه"),
  account: L("حساب کاربری"),
  other: L("سایر"),
};

/* ─── lookup ─────────────────────────────────────────────────────────────── */

const UNKNOWN: Label = Object.freeze({ fa: "نامشخص", tone: "neutral" });

/**
 * Label for a value that came over the wire. The server can ship a new enum
 * member before the client updates; indexing the map directly would render
 * `undefined.fa` and blank the whole screen, so unknown values get "نامشخص".
 */
export function labelOf<K extends string>(map: LabelMap<K>, value: string | null | undefined): Label {
  if (value === null || value === undefined) return UNKNOWN;
  return Object.prototype.hasOwnProperty.call(map, value) ? map[value as K] : UNKNOWN;
}

/** Map → [{ value, fa, tone }] in declaration order, for selects and filter chips. */
export function labelOptions<K extends string>(map: LabelMap<K>): { value: K; fa: string; tone: Tone }[] {
  return (Object.keys(map) as K[]).map((value) => ({ value, ...map[value] }));
}
