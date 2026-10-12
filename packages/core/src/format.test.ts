import { compactFa, formatM3, formatPercent, formatPoints, formatRial, formatToman } from "./format";

describe("unit formatters", () => {
  it("formats points", () => {
    expect(formatPoints(1250)).toBe("۱٬۲۵۰ امتیاز");
    expect(formatPoints(0)).toBe("۰ امتیاز");
    expect(formatPoints(-30)).toBe("−۳۰ امتیاز");
  });

  it("formats rials and converts rials to tomans", () => {
    expect(formatRial(5_000_000)).toBe("۵٬۰۰۰٬۰۰۰ ریال");
    expect(formatToman(5_000_000)).toBe("۵۰۰٬۰۰۰ تومان");
    expect(formatToman(1_000)).toBe("۱۰۰ تومان");
    expect(formatToman(4)).toBe("۰ تومان");
  });

  it("formats cubic metres with optional decimals", () => {
    expect(formatM3(3500)).toBe("۳٬۵۰۰ مترمکعب");
    expect(formatM3(12.345, 1)).toBe("۱۲٫۳ مترمکعب");
    expect(formatM3(0.4)).toBe("۰ مترمکعب");
  });

  it("renders non-finite input as a dash instead of NaN", () => {
    expect(formatPoints(Number.NaN)).toBe("— امتیاز");
    expect(formatPercent(Number.NaN)).toBe("—");
    expect(compactFa(Number.POSITIVE_INFINITY)).toBe("—");
  });
});

describe("formatPercent", () => {
  it("formats plain and signed percentages", () => {
    expect(formatPercent(12)).toBe("۱۲٪");
    expect(formatPercent(12, true)).toBe("+۱۲٪");
    expect(formatPercent(-12)).toBe("−۱۲٪");
    expect(formatPercent(-12, true)).toBe("−۱۲٪");
    expect(formatPercent(12.345, false, 1)).toBe("۱۲٫۳٪");
  });

  it("never signs a zero, including values that round to zero", () => {
    expect(formatPercent(0, true)).toBe("۰٪");
    expect(formatPercent(-0.3)).toBe("۰٪");
    expect(formatPercent(0.3, true)).toBe("۰٪");
    expect(formatPercent(-0.04, true, 1)).toBe("۰٫۰٪");
  });
});

describe("compactFa", () => {
  it("keeps small numbers whole", () => {
    expect(compactFa(0)).toBe("۰");
    expect(compactFa(950)).toBe("۹۵۰");
    expect(compactFa(-0.4)).toBe("۰");
  });

  it("uses هزار / میلیون / میلیارد with at most one decimal", () => {
    expect(compactFa(1200)).toBe("۱٫۲ هزار");
    expect(compactFa(1000)).toBe("۱ هزار");
    expect(compactFa(3_000_000)).toBe("۳ میلیون");
    expect(compactFa(1_250_000)).toBe("۱٫۳ میلیون");
    expect(compactFa(2_500_000_000)).toBe("۲٫۵ میلیارد");
    expect(compactFa(-1200)).toBe("−۱٫۲ هزار");
  });

  it("promotes instead of printing 1000 of a unit", () => {
    expect(compactFa(999_950)).toBe("۱ میلیون");
    expect(compactFa(999_960_000)).toBe("۱ میلیارد");
  });
});
