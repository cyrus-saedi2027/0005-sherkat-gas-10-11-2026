import { expect, type Page, type APIRequestContext } from "@playwright/test";

export const API = "http://127.0.0.1:8000/api/v1";
export const STAFF_PASSWORD = "Gazyar1405";

/** Persian → ASCII digits, for asserting on rendered numbers. */
export const en = (s: string) => s.replace(/[۰-۹]/g, (d) => String("۰۱۲۳۴۵۶۷۸۹".indexOf(d)));

export async function staffToken(request: APIRequestContext, username = "admin"): Promise<string> {
  const r = await request.post(`${API}/admin/auth/login`, { data: { username, password: STAFF_PASSWORD } });
  expect(r.ok()).toBeTruthy();
  return (await r.json()).tokens.access_token as string;
}

/** Collect console errors so every spec can assert the page stayed clean. */
export function watchConsole(page: Page): string[] {
  const errors: string[] = [];
  page.on("console", (m) => {
    if (m.type() === "error") errors.push(m.text());
  });
  page.on("pageerror", (e) => errors.push(String(e)));
  return errors;
}
