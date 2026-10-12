import { describe, expect, it } from "vitest";
import { contrastRatio } from "../lib/contrast";
import { GRAPHIC_PAIRS, NON_HEX_KEYS, TEXT_PAIRS, THEMES, type Palette, type ThemeId } from "./palettes";

const ids = Object.keys(THEMES) as ThemeId[];
const nonHex = new Set<string>(NON_HEX_KEYS);

describe("palettes", () => {
  it.each(ids)("%s: every opaque key is a valid hex colour", (id) => {
    const p = THEMES[id].p;
    for (const [k, val] of Object.entries(p)) {
      if (nonHex.has(k)) continue;
      expect(val, k).toMatch(/^#[0-9A-F]{6}$/i);
    }
  });

  it.each(ids)("%s: every text colour is ≥ 4.5:1 on each surface it is used on", (id) => {
    const p: Palette = THEMES[id].p;
    const failures: string[] = [];
    for (const [fg, bg] of TEXT_PAIRS) {
      const r = contrastRatio(p[fg], p[bg]);
      if (r < 4.5) failures.push(`${fg} ${p[fg]} on ${bg} ${p[bg]} = ${r.toFixed(2)}`);
    }
    expect(failures).toEqual([]);
  });

  it.each(ids)("%s: chart series, focus ring and controls are ≥ 3:1 (non-text contrast)", (id) => {
    const p: Palette = THEMES[id].p;
    const failures: string[] = [];
    for (const [fg, bg] of GRAPHIC_PAIRS) {
      const r = contrastRatio(p[fg], p[bg]);
      if (r < 3) failures.push(`${fg} ${p[fg]} on ${bg} ${p[bg]} = ${r.toFixed(2)}`);
    }
    expect(failures).toEqual([]);
  });

  it("day and night define exactly the same keys", () => {
    expect(Object.keys(THEMES.night.p).sort()).toEqual(Object.keys(THEMES.day.p).sort());
  });
});
