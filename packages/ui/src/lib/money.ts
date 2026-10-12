/* Money display. Amounts are stored and transported as integer rials
   (ARCHITECTURE §3); people read tomans. The conversion lives here so no
   screen ever divides by ten on its own — local until @gazyar/core
   exports its formatter, then re-export that instead. */

import { toFa } from "./digits";

/** Non-breaking space: a number must never wrap away from its unit. */
export const NBSP = " ";

export type MoneyUnit = "toman" | "rial";

export const MONEY_UNIT_FA: Record<MoneyUnit, string> = {
  toman: "تومان",
  rial: "ریال",
};

/** Integer rials → displayed amount in the chosen unit (rounded to whole tomans). */
export function rialTo(unit: MoneyUnit, rial: number): number {
  return unit === "toman" ? Math.round(rial / 10) : Math.round(rial);
}

/** 120000 → "۱۲٬۰۰۰ تومان" (NBSP between number and unit). */
export function formatMoney(rial: number, unit: MoneyUnit = "toman"): string {
  return `${toFa(rialTo(unit, rial))}${NBSP}${MONEY_UNIT_FA[unit]}`;
}

/** 1200 → "۱٬۲۰۰ امتیاز"; signed → "+۳۰ امتیاز" / "−۲۰ امتیاز". */
export function formatPoints(points: number, opts: { signed?: boolean; unit?: boolean } = {}): string {
  const { signed = false, unit = true } = opts;
  const sign = signed && points > 0 ? "+" : "";
  return `${sign}${toFa(points)}${unit ? `${NBSP}امتیاز` : ""}`;
}
