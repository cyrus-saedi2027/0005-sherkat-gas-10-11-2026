import { describe, expect, it } from "vitest";
import { MOTION, PRESET_ZETA, type MotionPreset } from "./presets";
import { dampingRatio } from "./spring";

describe("MOTION presets", () => {
  it("every preset's damping ratio matches the ζ its comment documents", () => {
    for (const key of Object.keys(MOTION) as MotionPreset[]) {
      const zeta = dampingRatio(MOTION[key]);
      // If this fails you retuned a preset: update the comment in
      // presets.ts *and* PRESET_ZETA together — that is the point.
      expect(Math.abs(zeta - PRESET_ZETA[key]), `${key}: ζ=${zeta.toFixed(3)}`).toBeLessThan(0.015);
    }
  });

  it("the sheet is tuned near ζ 0.8, between the signature cradle and the firmer swipe", () => {
    const sheet = dampingRatio(MOTION.sheet);
    expect(sheet).toBeGreaterThan(0.75);
    expect(sheet).toBeLessThan(0.85);
  });

  it("normalised springs use a fine precision; pixel springs a coarse one", () => {
    const unit: MotionPreset[] = ["swipe", "sheet", "flight", "thumb", "pop"];
    const px: MotionPreset[] = ["divider", "row", "bounce", "shake"];
    for (const k of unit) expect(MOTION[k].precision, k).toBeLessThanOrEqual(0.005);
    for (const k of px) expect(MOTION[k].precision, k).toBeGreaterThanOrEqual(0.1);
  });

  it("count never overshoots (ζ ≥ 1)", () => {
    expect(dampingRatio(MOTION.count)).toBeGreaterThanOrEqual(1);
  });
});
