"""Standard review reasons (operators pick one + optional note; users see the Persian text)."""

REJECT_REASONS: dict[str, str] = {
    "blurry_photo": "تصویر کنتور واضح نیست.",
    "digits_unreadable": "ارقام کنتور در تصویر خوانا نیست.",
    "number_mismatch": "عدد واردشده با تصویر کنتور مطابقت ندارد.",
    "wrong_meter": "تصویر مربوط به کنتور این اشتراک نیست.",
    "date_invalid": "تاریخ قرائت معتبر نیست.",
    "duplicate_photo": "این تصویر قبلاً ارسال شده است.",
    "suspected_fraud": "اطلاعات ارسالی مشکوک تشخیص داده شد.",
    "other": "به توضیحات کارشناس مراجعه کنید.",
}

FLAG_FA: dict[str, str] = {
    "meter_rollback": "عدد کنتور از قرائت قبلی کمتر است",
    "sudden_drop": "افت ناگهانی مصرف نسبت به مبنا",
    "zero_consumption": "مصرف صفر",
    "spike": "جهش غیرعادی مصرف",
    "duplicate_photo": "تصویر تکراری",
    "exif_mismatch": "تاریخ عکس با تاریخ قرائت فاصلهٔ زیادی دارد",
    "future_date": "تاریخ قرائت در آینده است",
    "stale_date": "تاریخ قرائت خیلی قدیمی است",
    "manual_no_photo": "ثبت دستی بدون تصویر",
}
