"""Role-based access control (R26, R34).

Permissions are fine-grained strings; roles are fixed bundles. Row-level rules
(an ambassador only sees own cases, a ticket handler only its unit) live in
the services — this module answers "may this role call this endpoint at all".
"""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    SUPER_ADMIN = "super_admin"
    OPERATOR = "operator"
    TECHNICIAN = "technician"
    AMBASSADOR = "ambassador"
    FINANCE = "finance"


ROLE_FA = {
    Role.SUPER_ADMIN: "مدیر سامانه",
    Role.OPERATOR: "اپراتور",
    Role.TECHNICIAN: "کارشناس فنی",
    Role.AMBASSADOR: "سفیر",
    Role.FINANCE: "واحد مالی",
}


class P(StrEnum):
    """Permission ids (ARCHITECTURE §4.3)."""

    DASHBOARD_VIEW = "dashboard.view"
    SUBSCRIBERS_VIEW = "subscribers.view"
    SUBSCRIBERS_IMPORT = "subscribers.import"
    SUBSCRIBERS_EDIT = "subscribers.edit"
    USERS_VIEW = "users.view"
    USERS_SUSPEND = "users.suspend"
    READINGS_VIEW = "readings.view"
    READINGS_REVIEW = "readings.review"
    READINGS_CORRECT_VALUE = "readings.correct_value"
    CASES_VIEW_ALL = "cases.view_all"
    CASES_VIEW_OWN = "cases.view_own"
    CASES_ASSIGN = "cases.assign"
    CASES_WORK = "cases.work"
    CASES_FINAL_APPROVE = "cases.final_approve"
    POINTS_VIEW = "points.view"
    POINTS_RULES_EDIT = "points.rules_edit"
    POINTS_ADJUST = "points.adjust"
    POINTS_SUSPEND = "points.suspend"
    REFERRALS_VIEW = "referrals.view"
    REFERRALS_REVIEW = "referrals.review"
    REWARDS_VIEW = "rewards.view"
    REWARDS_MANAGE = "rewards.manage"
    REDEMPTIONS_VIEW = "redemptions.view"
    REDEMPTIONS_REVIEW = "redemptions.review"
    REDEMPTIONS_FULFILL = "redemptions.fulfill"
    TICKETS_VIEW = "tickets.view"
    TICKETS_HANDLE = "tickets.handle"
    CONTENT_VIEW = "content.view"
    CONTENT_MANAGE = "content.manage"
    NOTIFICATIONS_BROADCAST = "notifications.broadcast"
    SURVEYS_VIEW = "surveys.view"
    SURVEYS_MANAGE = "surveys.manage"
    REPORTS_VIEW = "reports.view"
    REPORTS_EXPORT = "reports.export"
    SETTINGS_VIEW = "settings.view"
    SETTINGS_EDIT = "settings.edit"
    SETTINGS_FINANCE_EDIT = "settings.finance_edit"
    STAFF_VIEW = "staff.view"
    STAFF_MANAGE = "staff.manage"
    ACCESS_REVIEW_PERFORM = "access_review.perform"
    AUDIT_VIEW = "audit.view"
    DATA_DELETE = "data.delete"


ROLE_PERMISSIONS: dict[Role, frozenset[P]] = {
    Role.SUPER_ADMIN: frozenset(P),
    Role.OPERATOR: frozenset({
        P.DASHBOARD_VIEW, P.SUBSCRIBERS_VIEW, P.SUBSCRIBERS_IMPORT, P.SUBSCRIBERS_EDIT, P.USERS_VIEW,
        P.READINGS_VIEW, P.READINGS_REVIEW, P.READINGS_CORRECT_VALUE, P.CASES_VIEW_ALL, P.POINTS_VIEW,
        P.REFERRALS_VIEW, P.REWARDS_VIEW, P.TICKETS_VIEW, P.TICKETS_HANDLE, P.CONTENT_VIEW, P.CONTENT_MANAGE,
        P.NOTIFICATIONS_BROADCAST, P.SURVEYS_VIEW, P.REPORTS_VIEW, P.SETTINGS_VIEW,
    }),
    Role.TECHNICIAN: frozenset({
        P.DASHBOARD_VIEW, P.SUBSCRIBERS_VIEW, P.USERS_VIEW, P.READINGS_VIEW, P.READINGS_REVIEW,
        P.READINGS_CORRECT_VALUE, P.CASES_VIEW_ALL, P.CASES_ASSIGN, P.CASES_FINAL_APPROVE, P.POINTS_VIEW,
        P.TICKETS_VIEW, P.TICKETS_HANDLE, P.CONTENT_VIEW, P.SURVEYS_VIEW, P.REPORTS_VIEW, P.REPORTS_EXPORT,
        P.SETTINGS_VIEW,
    }),
    Role.AMBASSADOR: frozenset({
        P.DASHBOARD_VIEW, P.CASES_VIEW_OWN, P.CASES_WORK, P.TICKETS_VIEW, P.TICKETS_HANDLE, P.CONTENT_VIEW,
    }),
    Role.FINANCE: frozenset({
        P.DASHBOARD_VIEW, P.SUBSCRIBERS_VIEW, P.USERS_VIEW, P.POINTS_VIEW, P.POINTS_ADJUST, P.POINTS_SUSPEND,
        P.REFERRALS_VIEW, P.REFERRALS_REVIEW, P.REWARDS_VIEW, P.REWARDS_MANAGE, P.REDEMPTIONS_VIEW,
        P.REDEMPTIONS_REVIEW, P.REDEMPTIONS_FULFILL, P.TICKETS_VIEW, P.TICKETS_HANDLE, P.REPORTS_VIEW,
        P.REPORTS_EXPORT, P.SETTINGS_VIEW, P.SETTINGS_FINANCE_EDIT,
    }),
}

# Hard guarantees from the business document — asserted at import so a future
# edit to the table above cannot silently break them (R34).
assert P.SETTINGS_FINANCE_EDIT not in ROLE_PERMISSIONS[Role.OPERATOR]
assert P.DATA_DELETE not in ROLE_PERMISSIONS[Role.OPERATOR]
assert all(P.DATA_DELETE not in perms for r, perms in ROLE_PERMISSIONS.items() if r != Role.SUPER_ADMIN)


def permissions_for(roles: list[str] | tuple[str, ...]) -> frozenset[P]:
    out: set[P] = set()
    for r in roles:
        try:
            out |= ROLE_PERMISSIONS[Role(r)]
        except ValueError:
            continue  # unknown role strings grant nothing
    return frozenset(out)


# Ticket units each role may work in (row-level scoping, used by the tickets service).
ROLE_TICKET_UNITS: dict[Role, frozenset[str]] = {
    Role.SUPER_ADMIN: frozenset({"support", "technical", "finance", "ambassador"}),
    Role.OPERATOR: frozenset({"support"}),
    Role.TECHNICIAN: frozenset({"technical"}),
    Role.AMBASSADOR: frozenset({"ambassador"}),
    Role.FINANCE: frozenset({"finance"}),
}
