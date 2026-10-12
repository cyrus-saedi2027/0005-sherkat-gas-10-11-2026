import { parseFaNumber, toEn, toFa } from "./digits";

describe("toFa", () => {
  it("maps digits and groups thousands with ٬", () => {
    expect(toFa(0)).toBe("۰");
    expect(toFa(7)).toBe("۷");
    expect(toFa(999)).toBe("۹۹۹");
    expect(toFa(1000)).toBe("۱٬۰۰۰");
    expect(toFa(1250)).toBe("۱٬۲۵۰");
    expect(toFa(1234567)).toBe("۱٬۲۳۴٬۵۶۷");
  });

  it("can skip grouping (years, codes)", () => {
    expect(toFa(1405, false)).toBe("۱۴۰۵");
    expect(toFa(1234567, false)).toBe("۱۲۳۴۵۶۷");
  });

  it("uses ٫ for the decimal point and − for minus", () => {
    expect(toFa(1.5)).toBe("۱٫۵");
    expect(toFa(-1234.25)).toBe("−۱٬۲۳۴٫۲۵");
    expect(toFa("-12")).toBe("−۱۲");
  });

  it("never renders a negative zero", () => {
    expect(toFa(-0)).toBe("۰");
    expect(toFa("-0.00")).toBe("۰٫۰۰");
  });

  it("does not print exponent notation", () => {
    expect(toFa(1e21)).toBe("۱٬۰۰۰٬۰۰۰٬۰۰۰٬۰۰۰٬۰۰۰٬۰۰۰٬۰۰۰");
    expect(toFa(1e-7)).toBe("۰٫۰۰۰۰۰۰۱");
  });

  it("renders non-finite numbers as a dash", () => {
    expect(toFa(Number.NaN)).toBe("—");
    expect(toFa(Number.POSITIVE_INFINITY)).toBe("—");
  });

  it("treats leading-zero strings as identifiers (no grouping)", () => {
    expect(toFa("09121234567")).toBe("۰۹۱۲۱۲۳۴۵۶۷");
    expect(toFa("0012")).toBe("۰۰۱۲");
  });

  it("only swaps digits in non-numeric strings", () => {
    expect(toFa("1405/07/19")).toBe("۱۴۰۵/۰۷/۱۹");
    expect(toFa("GZ-261011-00042")).toBe("GZ-۲۶۱۰۱۱-۰۰۰۴۲");
    expect(toFa("12-34")).toBe("۱۲-۳۴");
  });

  it("accepts strings that already contain Persian/Arabic digits", () => {
    expect(toFa("۱۲۳۴")).toBe("۱٬۲۳۴");
    expect(toFa("١٢٣٤")).toBe("۱٬۲۳۴");
  });
});

describe("toEn", () => {
  it("maps Persian and Arabic-Indic digits to ASCII", () => {
    expect(toEn("۰۱۲۳۴۵۶۷۸۹")).toBe("0123456789");
    expect(toEn("٠١٢٣٤٥٦٧٨٩")).toBe("0123456789");
    expect(toEn("۴٤")).toBe("44");
  });

  it("leaves everything else untouched", () => {
    expect(toEn("abc-۱٫۵")).toBe("abc-1٫5");
    expect(toEn("")).toBe("");
    expect(toEn("１２３")).toBe("１２３"); // full-width digits are not in scope
  });

  it("round-trips with toFa for plain integers", () => {
    for (const n of [0, 5, 42, 1405, 99999]) expect(toEn(toFa(n, false))).toBe(String(n));
  });
});

describe("parseFaNumber", () => {
  it("parses any digit set, grouping and decimal separator", () => {
    expect(parseFaNumber("۱٬۲۵۰")).toBe(1250);
    expect(parseFaNumber("1,250")).toBe(1250);
    expect(parseFaNumber("۳٫۵")).toBe(3.5);
    expect(parseFaNumber("٣.٥")).toBe(3.5);
    expect(parseFaNumber("−۵")).toBe(-5);
    expect(parseFaNumber(" 12 ")).toBe(12);
    expect(parseFaNumber(".5")).toBe(0.5);
  });

  it("returns null (never NaN) for non-numbers", () => {
    expect(parseFaNumber("")).toBeNull();
    expect(parseFaNumber("abc")).toBeNull();
    expect(parseFaNumber("1.2.3")).toBeNull();
    expect(parseFaNumber("-")).toBeNull();
  });
});
