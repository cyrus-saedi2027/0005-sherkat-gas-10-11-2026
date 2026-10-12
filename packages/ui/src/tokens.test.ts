import { describe, expect, it } from "vitest";
import css from "./styles/global.css?raw";
import { BREAKPOINTS, FONT, GESTURE, R, Z, mq, tokenCssVars } from "./tokens";

/** Custom properties declared in the first `:root { … }` block of global.css. */
function rootVars(source: string): Record<string, string> {
  const block = /:root\s*\{([\s\S]*?)\n\}/.exec(source)?.[1] ?? "";
  const out: Record<string, string> = {};
  for (const m of block.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) out[m[1]!] = m[2]!.trim();
  return out;
}

describe("tokens", () => {
  it("global.css declares exactly the custom properties tokens.ts defines", () => {
    expect(rootVars(css)).toEqual(tokenCssVars());
  });

  it("every font url in global.css points at a file the vazirmatn package ships", () => {
    const shipped = Object.keys(
      import.meta.glob("../node_modules/vazirmatn/fonts/webfonts/*.woff2", { query: "?url", eager: true }),
    ).map((p) => p.replace("../node_modules/", ""));
    const urls = Array.from(css.matchAll(/url\("\.\.\/\.\.\/node_modules\/([^"]+)"\)/g), (m) => m[1]!);
    expect(urls).toHaveLength(4);
    for (const u of urls) expect(shipped, u).toContain(u);
  });

  it("Persian type sits in the 1.45–1.75 line-height band", () => {
    for (const [k, f] of Object.entries(FONT)) {
      expect(f.lineHeight, k).toBeGreaterThanOrEqual(1.45);
      expect(f.lineHeight, k).toBeLessThanOrEqual(1.75);
    }
  });

  it("radii are named by what they wrap and pill is fully round", () => {
    expect(R.pill).toBeGreaterThanOrEqual(999);
    expect(R.card).toBeGreaterThan(R.row);
    expect(R.sheet).toBeGreaterThan(R.card);
  });

  it("rows lock before tabs so a row swipe wins without a state machine", () => {
    expect(GESTURE.rowLock).toBeLessThan(GESTURE.tabLock);
  });

  it("z-order is strictly increasing in the documented order", () => {
    const order = [Z.tab, Z.sticky, Z.push, Z.nav, Z.dropdown, Z.sheet, Z.dialog, Z.toast, Z.flight];
    for (let i = 1; i < order.length; i++) expect(order[i]!).toBeGreaterThan(order[i - 1]!);
  });

  it("breakpoints and media queries", () => {
    expect(BREAKPOINTS).toEqual({ sm: 480, md: 768, lg: 1024, xl: 1280 });
    expect(mq("md")).toBe("(min-width: 768px)");
  });
});
