/* Form validators. Every helper that can fail returns a Persian message
 * (string) or null for "fine", so a form shows `error ?? hint` directly.
 * The server re-validates everything; these exist for instant feedback. */

import { toEn, toFa } from "./i18n/digits";
import { isValidIban, isValidNationalCode, normalizeIban, normalizeMobile, normalizeSubscription } from "./i18n/normalize";

export { isValidIban, isValidNationalCode, maskMobile, normalizeIban, normalizeMobile, normalizeSubscription } from "./i18n/normalize";

/** A Persian error message, or null when the value is acceptable. */
export type FieldError = string | null;
export type Validator<T = string> = (value: T) => FieldError;

export const PASSWORD_MIN = 8;
export const PASSWORD_MAX = 128;

/* Letters only: Latin A–Z/a–z plus the Arabic-script *letter* ranges. A plain
 * U+0600–U+06FF range would count Persian digits (U+06F0–U+06F9) and "،" as
 * letters, so "1234567۱" would pass as "has a letter". */
const LETTER = /[A-Za-zؠ-يٮ-ۓەۮۯۺ-ۼۿ]/;

export type PasswordCheck = { ok: true } | { ok: false; reason: string };

/** Same rules and messages as backend validators.password_problem, except the
 *  letter class: the backend's [A-Za-z\u0600-\u06FF] also counts Persian
 *  digits as letters, so "1234567۱" passes there and fails here (the backend
 *  should adopt LETTER above). */
export function isValidPassword(pw: string): PasswordCheck {
  if (pw.length < PASSWORD_MIN) return { ok: false, reason: "رمز عبور باید دست‌کم ۸ نویسه باشد." };
  if (pw.length > PASSWORD_MAX) return { ok: false, reason: "رمز عبور بیش از حد طولانی است." };
  if (!LETTER.test(pw) || !/[0-9]/.test(toEn(pw))) {
    return { ok: false, reason: "رمز عبور باید هم حرف و هم عدد داشته باشد." };
  }
  return { ok: true };
}

export function passwordError(pw: string): FieldError {
  const r = isValidPassword(pw);
  return r.ok ? null : r.reason;
}

const isBlank = (v: unknown) =>
  v === null || v === undefined || (typeof v === "string" && v.trim() === "") || (Array.isArray(v) && v.length === 0);

/** "نام الزامی است." / "این فیلد الزامی است." */
export function required(value: unknown, label?: string): FieldError {
  if (!isBlank(value)) return null;
  return label ? `${label} الزامی است.` : "این فیلد الزامی است.";
}

/* Length counts code points, not UTF-16 units — an emoji is one character to
 * the person typing it. */
const charCount = (s: string) => Array.from(s).length;

export function minLength(value: string, min: number, label = "مقدار"): FieldError {
  return charCount(value.trim()) < min ? `${label} باید دست‌کم ${toFa(min)} نویسه باشد.` : null;
}

export function maxLength(value: string, max: number, label = "مقدار"): FieldError {
  return charCount(value) > max ? `${label} نباید بیشتر از ${toFa(max)} نویسه باشد.` : null;
}

export function lengthBetween(value: string, min: number, max: number, label = "مقدار"): FieldError {
  return minLength(value, min, label) ?? maxLength(value, max, label);
}

export function mobileError(value: string): FieldError {
  return normalizeMobile(value) ? null : "شمارهٔ موبایل معتبر نیست؛ مثال: ۰۹۱۲۱۲۳۴۵۶۷";
}

export function subscriptionError(value: string): FieldError {
  return normalizeSubscription(value) ? null : "شمارهٔ اشتراک معتبر نیست؛ فقط رقم وارد کنید (۴ تا ۲۰ رقم).";
}

export function nationalCodeError(value: string): FieldError {
  return isValidNationalCode(value) ? null : "کد ملی معتبر نیست.";
}

export function ibanError(value: string): FieldError {
  if (!normalizeIban(value)) return "شمارهٔ شبا باید ۲۴ رقم بعد از IR باشد.";
  return isValidIban(value) ? null : "شمارهٔ شبا معتبر نیست؛ ارقام را دوباره بررسی کنید.";
}

/** First error wins — run cheap checks (required) before expensive ones. */
export function firstError<T>(value: T, ...validators: Validator<T>[]): FieldError {
  for (const v of validators) {
    const e = v(value);
    if (e) return e;
  }
  return null;
}
