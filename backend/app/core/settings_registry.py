"""Every business number from the requirement document, as an editable setting (R06).

The document says explicitly: "3500 m³ is a configurable parameter and the x
values are only initial settings, not contract numbers". So nothing here may
be read as a literal elsewhere — services call `get(db, key)`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.rbac import P

Kind = Literal["int", "float", "bool", "str", "choice"]


@dataclass(frozen=True)
class Spec:
    key: str
    default: Any
    kind: Kind
    category: str
    title_fa: str
    help_fa: str = ""
    min: float | None = None
    max: float | None = None
    choices: tuple[tuple[str, str], ...] = ()
    permission: P = P.SETTINGS_EDIT
    unit_fa: str = ""


SPECS: tuple[Spec, ...] = (
    # ── eligibility (R06, R09, R14) ──
    Spec("eligibility.threshold_m3", 3500, "int", "eligibility", "آستانهٔ مصرف برای ورود به طرح",
         "مشترکانی که مصرفِ مبنایشان کمتر از این عدد است صلاحیتِ ورود ندارند.", 0, 1_000_000, unit_fa="مترمکعب"),
    Spec("eligibility.threshold_basis", "annual", "choice", "eligibility", "مبنای مقایسه با آستانه",
         "مصرفِ مبنا از میانگینِ دورهٔ مشابهِ سه سالِ قبل محاسبه می‌شود.",
         choices=(("annual", "مجموع سالانه"), ("monthly_avg", "میانگین ماهانه"), ("period", "دورهٔ همان قرائت"))),
    Spec("eligibility.baseline_years", 3, "int", "eligibility", "تعداد سال‌های مبنا", "", 1, 5, unit_fa="سال"),
    # ── readings (R12, R13, R15) ──
    Spec("reading.period_months", 1, "choice", "reading", "طول دورهٔ قرائت",
         choices=(("1", "ماهانه"), ("2", "دوماهه"))),
    Spec("reading.photo_required", True, "bool", "reading", "تصویر کنتور الزامی است"),
    Spec("reading.max_back_days", 45, "int", "reading", "حداکثر قدمتِ تاریخ قرائت", "", 1, 365, unit_fa="روز"),
    Spec("reading.max_value_m3", 9_999_999, "int", "reading", "بیشینهٔ عدد کنتور", "", 1, 99_999_999),
    Spec("anomaly.sudden_drop_pct", 60, "int", "reading", "افت ناگهانی نسبت به مبنا",
         "اگر مصرفِ دوره بیش از این درصد از مبنا کمتر باشد، قرائت برای بررسیِ دستی علامت می‌خورد.", 1, 100, unit_fa="٪"),
    Spec("anomaly.spike_pct", 250, "int", "reading", "جهش غیرعادی نسبت به مبنا", "", 100, 10_000, unit_fa="٪"),
    Spec("anomaly.exif_max_days", 10, "int", "reading", "اختلاف مجاز تاریخ عکس و تاریخ قرائت", "", 1, 90, unit_fa="روز"),
    # ── points (R22, R23) ──
    Spec("points.reduction_required_pct", 10, "int", "points", "درصد کاهش لازم نسبت به مبنا", "", 0, 100, unit_fa="٪"),
    Spec("points.reduction_monthly_cap", 200, "int", "points", "سقف امتیاز کاهش مصرف در ماه", "", 0, 100_000, unit_fa="امتیاز"),
    # ── finance (R06, R19, R21) — operators can never edit these (R34) ──
    Spec("finance.point_rial_rate", 1000, "int", "finance", "ارزش ریالی هر امتیاز", "", 0, 10_000_000,
         permission=P.SETTINGS_FINANCE_EDIT, unit_fa="ریال"),
    Spec("finance.free_cap_rial", 5_000_000, "int", "finance", "سقف ریالی خدمات رایگان", "", 0, 10_000_000_000,
         permission=P.SETTINGS_FINANCE_EDIT, unit_fa="ریال"),
    Spec("finance.copay_subscriber_pct", 30, "int", "finance", "سهم مشارکت مشترک در گروه پرهزینه",
         "سهم طرح برابر با باقی‌مانده است (پیش‌فرض ۳۰/۷۰).", 0, 100, permission=P.SETTINGS_FINANCE_EDIT, unit_fa="٪"),
    Spec("finance.min_cash_withdraw_points", 500, "int", "finance", "حداقل امتیاز برای برداشت نقدی", "", 0, 10_000_000,
         permission=P.SETTINGS_FINANCE_EDIT, unit_fa="امتیاز"),
    Spec("finance.redeem_window_days", 0, "int", "finance", "مهلت استفاده از امتیاز پس از پایان ماه",
         "صفر یعنی امتیازِ آزادشده هر زمان قابل استفاده است.", 0, 31, permission=P.SETTINGS_FINANCE_EDIT, unit_fa="روز"),
    # ── fraud (R24, R40) ──
    Spec("fraud.referral_monthly_cap", 5, "int", "fraud", "سقف معرفی موفق در ماه", "", 0, 1000,
         permission=P.SETTINGS_FINANCE_EDIT),
    Spec("fraud.max_accounts_per_device", 2, "int", "fraud", "حداکثر حساب روی یک دستگاه", "", 1, 50,
         permission=P.SETTINGS_FINANCE_EDIT),
    # ── uploads & otp & security (R36) ──
    Spec("uploads.max_mb", 8, "int", "uploads", "حداکثر حجم هر تصویر", "", 1, 20, unit_fa="مگابایت"),
    Spec("uploads.daily_per_user", 30, "int", "uploads", "سقف آپلود روزانهٔ هر کاربر", "", 1, 500),
    Spec("otp.ttl_seconds", 120, "int", "otp", "اعتبار کد یک‌بارمصرف", "", 30, 600, unit_fa="ثانیه"),
    Spec("otp.resend_seconds", 60, "int", "otp", "فاصلهٔ ارسال مجدد کد", "", 15, 600, unit_fa="ثانیه"),
    Spec("otp.max_attempts", 5, "int", "otp", "تعداد تلاش مجاز برای هر کد", "", 1, 10),
    Spec("otp.per_mobile_10min", 3, "int", "otp", "سقف ارسال کد به هر موبایل در ۱۰ دقیقه", "", 1, 20),
    Spec("otp.per_mobile_day", 10, "int", "otp", "سقف ارسال کد به هر موبایل در روز", "", 1, 100),
    Spec("otp.per_ip_10min", 20, "int", "otp", "سقف درخواست کد از هر IP در ۱۰ دقیقه", "", 1, 1000),
    Spec("security.staff_max_failed_logins", 5, "int", "security", "تعداد ورود ناموفق تا قفل حساب کارکنان", "", 3, 20),
    Spec("security.staff_lock_minutes", 15, "int", "security", "مدت قفل حساب", "", 1, 1440, unit_fa="دقیقه"),
    Spec("security.user_max_failed_logins", 8, "int", "security", "تعداد ورود ناموفق تا قفل حساب کاربر", "", 3, 50),
    Spec("security.api_per_minute", 120, "int", "security", "سقف درخواست API در دقیقه برای هر کاربر", "", 10, 10_000),
    Spec("security.access_review_days", 90, "int", "security", "دورهٔ بازبینی دسترسی‌ها", "", 7, 365, unit_fa="روز"),
    # ── general ──
    Spec("terms.version", "1", "str", "general", "نسخهٔ شرایط طرح و حریم خصوصی"),
    Spec("support.phone", "", "str", "general", "شمارهٔ تماس پشتیبانی"),
)

BY_KEY: dict[str, Spec] = {s.key: s for s in SPECS}

CATEGORY_FA = {
    "eligibility": "صلاحیت و آستانه", "reading": "قرائت و ناهماهنگی", "points": "امتیاز",
    "finance": "مالی", "fraud": "ضدتقلب", "uploads": "آپلود", "otp": "کد یک‌بارمصرف",
    "security": "امنیت", "general": "عمومی",
}


def coerce(spec: Spec, value: Any) -> Any:
    """Validate + coerce an incoming value; raise ValueError with a Persian message."""
    if spec.kind == "bool":
        if isinstance(value, bool):
            return value
        raise ValueError("مقدار باید بله/خیر باشد.")
    if spec.kind in ("int", "float"):
        if isinstance(value, bool) or not isinstance(value, int | float | str):
            raise ValueError("مقدار باید عدد باشد.")
        try:
            num: float = float(str(value).strip())
        except ValueError as e:
            raise ValueError("مقدار باید عدد باشد.") from e
        if spec.kind == "int":
            if num != int(num):
                raise ValueError("مقدار باید عدد صحیح باشد.")
            num = int(num)
        if spec.min is not None and num < spec.min:
            raise ValueError(f"حداقل مقدار مجاز {spec.min:g} است.")
        if spec.max is not None and num > spec.max:
            raise ValueError(f"حداکثر مقدار مجاز {spec.max:g} است.")
        return num
    if spec.kind == "choice":
        allowed = {c for c, _ in spec.choices}
        if str(value) not in allowed:
            raise ValueError("گزینهٔ انتخاب‌شده معتبر نیست.")
        # numeric choices (reading.period_months) are stored as ints
        return int(value) if str(value).isdigit() and isinstance(spec.default, int) else str(value)
    if not isinstance(value, str) or len(value) > 500:
        raise ValueError("مقدار متنی معتبر نیست.")
    return value.strip()


def get(db: Session, key: str) -> Any:
    from app.modules.settings.models import Setting

    spec = BY_KEY[key]  # KeyError on typos is intentional
    cache: dict[str, Any] = db.info.setdefault("settings_cache", {})
    if key not in cache:
        row = db.scalar(select(Setting).where(Setting.key == key))
        cache[key] = row.value if row is not None else spec.default
    return cache[key]


def get_int(db: Session, key: str) -> int:
    return int(get(db, key))


def invalidate(db: Session) -> None:
    db.info.pop("settings_cache", None)
