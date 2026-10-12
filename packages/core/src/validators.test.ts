import {
  firstError,
  ibanError,
  isValidPassword,
  lengthBetween,
  maxLength,
  minLength,
  mobileError,
  nationalCodeError,
  passwordError,
  required,
  subscriptionError,
} from "./validators";

describe("isValidPassword", () => {
  it("accepts 8+ characters with a letter and a digit", () => {
    expect(isValidPassword("abcdefg1")).toEqual({ ok: true });
    expect(isValidPassword("رمزعبور۱۲")).toEqual({ ok: true }); // Persian letters + Persian digits
    expect(passwordError("Gazyar2026")).toBeNull();
  });

  it("explains the problem in Persian", () => {
    expect(isValidPassword("ab1")).toEqual({ ok: false, reason: "رمز عبور باید دست‌کم ۸ نویسه باشد." });
    expect(isValidPassword("abcdefgh")).toEqual({ ok: false, reason: "رمز عبور باید هم حرف و هم عدد داشته باشد." });
    expect(isValidPassword("12345678")).toEqual({ ok: false, reason: "رمز عبور باید هم حرف و هم عدد داشته باشد." });
    expect(isValidPassword("x".repeat(129) + "1").ok).toBe(false);
  });

  it("does not count Persian digits as letters", () => {
    expect(isValidPassword("1234567۱").ok).toBe(false);
  });
});

describe("required / length helpers", () => {
  it("required", () => {
    expect(required("")).toBe("این فیلد الزامی است.");
    expect(required("   ", "نام")).toBe("نام الزامی است.");
    expect(required(null)).not.toBeNull();
    expect(required([])).not.toBeNull();
    expect(required(0)).toBeNull();
    expect(required("x")).toBeNull();
  });

  it("min/max/between with Persian digits in messages", () => {
    expect(minLength("ab", 3, "نام")).toBe("نام باید دست‌کم ۳ نویسه باشد.");
    expect(minLength("abc", 3)).toBeNull();
    expect(maxLength("abcd", 3, "کد")).toBe("کد نباید بیشتر از ۳ نویسه باشد.");
    expect(maxLength("😀😀😀", 3)).toBeNull(); // code points, not UTF-16 units
    expect(lengthBetween("a", 2, 4)).toBe("مقدار باید دست‌کم ۲ نویسه باشد.");
    expect(lengthBetween("abcde", 2, 4)).toBe("مقدار نباید بیشتر از ۴ نویسه باشد.");
    expect(lengthBetween("abc", 2, 4)).toBeNull();
  });
});

describe("field validators", () => {
  it("mobile / subscription / national code / IBAN", () => {
    expect(mobileError("۰۹۱۲۱۲۳۴۵۶۷")).toBeNull();
    expect(mobileError("0912")).toMatch(/موبایل/);
    expect(subscriptionError("001234")).toBeNull();
    expect(subscriptionError("12")).toMatch(/اشتراک/);
    expect(nationalCodeError("0499370899")).toBeNull();
    expect(nationalCodeError("1111111111")).toBe("کد ملی معتبر نیست.");
    expect(ibanError("IR820540102680020817909002")).toBeNull();
    expect(ibanError("IR12")).toMatch(/۲۴ رقم/);
    expect(ibanError("IR830540102680020817909002")).toMatch(/معتبر نیست/);
  });

  it("firstError runs validators in order", () => {
    const req = (v: string) => required(v, "موبایل");
    expect(firstError("", req, mobileError)).toBe("موبایل الزامی است.");
    expect(firstError("123", req, mobileError)).toMatch(/موبایل معتبر نیست/);
    expect(firstError("09121234567", req, mobileError)).toBeNull();
  });
});
