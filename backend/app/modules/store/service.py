"""Reward store & redemptions (R20, R21, R25, R40).

Points are reserved immediately (a negative ledger entry) so the same points
cannot be spent twice while finance reviews; rejection refunds them. Only
`available` points (released at the month end) can be spent.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import audit, clock, crypto, jalali
from app.core import settings_registry as reg
from app.core.errors import AppError
from app.modules.notifications.service import notify
from app.modules.points import service as points
from app.modules.points.models import PointsLedger
from app.modules.store.models import Redemption, RewardCategory, RewardItem
from app.modules.users.models import User, UserDevice

DEFAULT_CATEGORIES = (
    # R25 — the exact options listed in the requirement document
    ("cash", "برداشت نقدی", "wallet"),
    ("pet_food", "غذای حیوانات خانگی", "paw"),
    ("insulation", "بسته‌های عایق‌سازی و بهینه‌سازی", "layers"),
    ("repair_discount", "تخفیف تعمیر بخاری، پکیج و آبگرمکن", "wrench"),
    ("charity", "کمک به خیریه‌ها و NGO", "heart"),
    ("stationery", "لوازم‌التحریر", "book"),
    ("gift", "سایر هدایا", "gift"),
)


def seed_categories(db: Session) -> None:
    have = set(db.scalars(select(RewardCategory.key)).all())
    for i, (key, title, icon) in enumerate(DEFAULT_CATEGORIES):
        if key not in have:
            db.add(RewardCategory(key=key, title=title, icon=icon, sort=i))
    db.flush()


def _window_open(db: Session) -> bool:
    """Optional rule: points may only be used within N days after a month end (0 = always)."""
    days = reg.get_int(db, "finance.redeem_window_days")
    if days <= 0:
        return True
    j = jalali.jdate_of(clock.now())
    return j.day <= days


def fraud_signals(db: Session, user: User) -> dict[str, Any]:
    """Signals shown to finance (R21, R40) — never decisions by themselves."""
    s: dict[str, Any] = {}
    now = clock.now()
    if (now - user.created_at) < timedelta(days=30):
        s["new_account_days"] = (now - user.created_at).days
    if db.scalar(select(func.count()).where(PointsLedger.user_id == user.id, PointsLedger.status == "suspended")):
        s["has_suspended_points"] = True
    devices = [d for (d,) in db.execute(select(UserDevice.device_id).where(UserDevice.user_id == user.id)).all()]
    if devices:
        shared = db.scalar(select(func.count(func.distinct(UserDevice.user_id))).where(UserDevice.device_id.in_(devices))) or 0
        if shared > reg.get_int(db, "fraud.max_accounts_per_device"):
            s["device_shared_by"] = int(shared)
    recent = db.scalar(select(func.count()).where(Redemption.user_id == user.id, Redemption.created_at >= now - timedelta(days=7))) or 0
    if recent >= 3:
        s["redemptions_last_7d"] = int(recent)
    referral_pts = db.scalar(select(func.coalesce(func.sum(PointsLedger.amount), 0)).where(
        PointsLedger.user_id == user.id, PointsLedger.event_type == "referral_success")) or 0
    total_pts = db.scalar(select(func.coalesce(func.sum(PointsLedger.amount), 0)).where(
        PointsLedger.user_id == user.id, PointsLedger.amount > 0)) or 0
    if total_pts and referral_pts / total_pts > 0.7:
        s["mostly_referral_points"] = True
    return s


def redeem(db: Session, *, user: User, item_id: int | None, kind: str, points_amount: int | None,
           delivery_address: str | None, note: str | None, request: Request | None) -> Redemption:
    if user.status != "active":
        raise AppError("account_suspended", "حساب کاربری شما معلق است.", 403)
    if not _window_open(db):
        raise AppError("window_closed", "مهلت استفاده از امتیاز این ماه به پایان رسیده است.", 409)
    rate = reg.get_int(db, "finance.point_rial_rate")
    item = None
    if kind == "cash":
        min_pts = reg.get_int(db, "finance.min_cash_withdraw_points")
        if not points_amount or points_amount < min_pts:
            raise AppError("validation_error", f"حداقل امتیاز برای برداشت نقدی {jalali.to_fa_digits(str(min_pts))} است.", 422)
        if not user.iban_enc:
            raise AppError("iban_required", "برای برداشت نقدی ابتدا شماره شبا را در پروفایل ثبت کنید.", 409)
        cost, title, rial = points_amount, "برداشت نقدی", points_amount * rate
    else:
        item = db.get(RewardItem, item_id or 0)
        if item is None or not item.is_active:
            raise AppError("not_found", "این مورد در فروشگاه موجود نیست.", 404)
        if item.kind == "donation" and points_amount:
            if points_amount < item.points_cost:
                raise AppError("validation_error", "مقدار اهدا کمتر از حداقل مجاز است.", 422)
            cost, rial = points_amount, points_amount * rate
        else:
            cost, rial = item.points_cost, item.rial_value or item.points_cost * rate
        if item.stock is not None:
            if item.stock <= 0:
                raise AppError("out_of_stock", "موجودی این کالا تمام شده است.", 409)
            item.stock -= 1
        if item.needs_address and not (delivery_address or "").strip():
            raise AppError("validation_error", "نشانی تحویل را وارد کنید.", 422, {"fields": {"delivery_address": "الزامی است."}})
        title, kind = item.title, item.kind
    r = Redemption(user_id=user.id, item_id=item.id if item else None, kind=kind, title=title, points=cost, rial_value=rial,
                   fraud_signals=fraud_signals(db, user), iban_enc=user.iban_enc if kind == "cash" else None,
                   delivery_address=(delivery_address or "").strip()[:500] or None, user_note=(note or "").strip()[:500] or None)
    db.add(r)
    db.flush()
    e = points.spend(db, user_id=user.id, amount=cost, idempotency_key=f"redeem:{r.id}", reason=f"درخواست: {title}",
                     ref_type="redemption", ref_id=r.id)
    r.spend_entry_id = e.id
    audit.record(db, audit.Actor("user", user.id), "redemption.submit", "redemption", r.id, None,
                 {"kind": kind, "points": cost, "signals": r.fraud_signals}, request)
    return r


def _refund(db: Session, r: Redemption, reason: str) -> None:
    e = points.refund(db, user_id=r.user_id, amount=r.points, idempotency_key=f"refund:{r.id}", reason=reason,
                      ref_type="redemption", ref_id=r.id)
    if e is not None:
        r.refund_entry_id = e.id
    if r.item_id:
        item = db.get(RewardItem, r.item_id)
        if item is not None and item.stock is not None:
            item.stock += 1


def cancel(db: Session, r: Redemption, user_id: int, request: Request | None) -> Redemption:
    if r.user_id != user_id:
        raise AppError("not_found", "درخواست پیدا نشد.", 404)
    if r.status != "submitted":
        raise AppError("bad_state", "این درخواست دیگر قابل لغو نیست.", 409)
    r.status = "cancelled"
    _refund(db, r, "لغو درخواست توسط کاربر")
    audit.record(db, audit.Actor("user", user_id), "redemption.cancel", "redemption", r.id, request=request)
    return r


def review(db: Session, r: Redemption, *, approve: bool, note: str | None, staff: audit.Actor, request: Request | None) -> Redemption:
    """R21: withdrawal/conversion only after fraud control and finance approval."""
    if r.status != "submitted":
        raise AppError("bad_state", "این درخواست قبلاً بررسی شده است.", 409)
    before = r.status
    r.reviewed_by, r.reviewed_at, r.finance_note = staff.id, clock.now(), note
    if approve:
        r.status = "approved"
        notify(db, user_id=r.user_id, kind="redemption_approved", title="درخواست شما تأیید شد", body=r.title,
               data={"route": "/wallet/requests"})
    else:
        r.status = "rejected"
        _refund(db, r, "رد درخواست و بازگشت امتیاز")
        notify(db, user_id=r.user_id, kind="redemption_rejected", title="درخواست شما تأیید نشد",
               body=(note or "امتیاز به کیف پول شما برگشت داده شد."), data={"route": "/wallet/requests"})
    audit.record(db, staff, "redemption.review", "redemption", r.id, {"status": before}, {"status": r.status, "note": note}, request)
    return r


def fulfill(db: Session, r: Redemption, *, payment_ref: str | None, note: str | None, staff: audit.Actor,
            request: Request | None) -> Redemption:
    if r.status != "approved":
        raise AppError("bad_state", "ابتدا درخواست باید تأیید شود.", 409)
    if r.kind == "cash" and not (payment_ref or "").strip():
        raise AppError("validation_error", "شمارهٔ پیگیری واریز را وارد کنید.", 422, {"fields": {"payment_ref": "الزامی است."}})
    r.status, r.fulfilled_at, r.payment_ref = "fulfilled", clock.now(), (payment_ref or "").strip() or None
    if note:
        r.finance_note = note
    notify(db, user_id=r.user_id, kind="redemption_fulfilled",
           title="مبلغ به حساب شما واریز شد" if r.kind == "cash" else "درخواست شما انجام شد", body=r.title,
           data={"route": "/wallet/requests"}, sms_text=f"گازیار: درخواست «{r.title}» انجام شد." if r.kind == "cash" else None)
    audit.record(db, staff, "redemption.fulfill", "redemption", r.id, {"status": "approved"},
                 {"status": "fulfilled", "payment_ref": r.payment_ref}, request)
    return r


def masked_iban(r: Redemption) -> str | None:
    v = crypto.decrypt(r.iban_enc) if r.iban_enc else None
    return f"{v[:4]}…{v[-4:]}" if v else None
