# تحویل کار — از کجا ادامه بدهیم (HANDOFF)

> آخرین به‌روزرسانی: ۲۲ مهر ۱۴۰۵ · شاخهٔ کار: `claude/upbeat-keller-0xd6wv`
> این فایل برای ادامهٔ کار با یک اکانت/جلسهٔ دیگرِ Claude نوشته شده. اول **بخش فارسی** (خلاصه برای صاحب پروژه)، بعد **بخش انگلیسی** (دستور کار دقیق برای Claude).

---

## خلاصه برای صاحب پروژه

### چه چیزی تمام شده ✅
| بخش | وضعیت |
|---|---|
| تحلیل کامل سند و فلوچارت (۴۷ خواسته) | `ROADMAP.md` |
| معماری و قرارداد مهندسی | `docs/ARCHITECTURE.md` |
| **بک‌اند هر سه مرحله** (۱۲۶ endpoint) | تمام — ۲۶۸ تست سبز روی SQLite و PostgreSQL |
| مهاجرت‌های پایگاه داده (۳ نسخه) | تست رفت‌وبرگشت شده |
| داده‌های نمایشی (`seed --demo`) | ۳۰۰ مشترک، کاربر، پرونده، فروشگاه، مقاله، نظرسنجی |
| لایهٔ API تایپ‌شدهٔ فرانت (`packages/core`, `packages/data`) | تمام — ۲۶۹ تست |
| موتور موشن (`packages/motion`) | تمام — ۳۸ تست |
| استقرار: Docker Compose، nginx، پشتیبان‌گیری، راهنما | `deploy/`, `docs/DEPLOYMENT.md` |
| تنظیمات Vite/PWA/Capacitor و آیکون‌های دو اپ | `apps/user`, `apps/admin` |

### چه چیزی مانده ⏳
1. **سیستم طراحی (`packages/ui`)** — پایه (توکن، تم، متن، دکمه، فیلد، کارت، سوییچ، تب، …) ساخته شده؛ این‌ها مانده: شیت کشویی، دیالوگ، توست، جدول داده، تقویم جلالی، نمودارها، انتخاب عکس، نمایشگر عکس، روتر اپ موبایل، نوار پایین، سایدبار پنل، صفحهٔ گالری.
2. **صفحات اپ کاربر** (حدود ۲۰ صفحه) و **صفحات پنل مدیریت** (حدود ۲۵ صفحه) — هنوز شروع نشده؛ فهرست کامل پایین هست.
3. **تست سرتاسری (Playwright)** — زیرساخت آماده؛ سناریوها مانده.
4. به‌روزرسانی جدول وضعیت در `ROADMAP.md` بعد از هر بخش.

### چطور در اکانت جدید ادامه بدهم
1. در Claude Code (وب یا اپ) همین مخزن `cyrus-saedi2027/0005-sherkat-gas-10-11-2026` را وصل کنید و شاخهٔ `claude/upbeat-keller-0xd6wv` را انتخاب کنید.
2. این پیام را بفرستید:
   > فایل `HANDOFF.md` و `CLAUDE.md` را کامل بخوان و کار را دقیقاً از «Next steps» ادامه بده. روی همین شاخه کار کن، بعد از هر بخش تست بگیر، commit و push کن، و جدول وضعیت ROADMAP را به‌روز کن.
3. اگر حجم اکانت محدود است، بگویید «هر بار فقط یک قدم از Next steps را انجام بده» تا کار نصفه نماند.

---

## Handoff for Claude (English, binding)

Read in this order: `CLAUDE.md` → this file → `docs/ARCHITECTURE.md` → `ROADMAP.md` (Persian requirement list R01–R47).

### Environment bootstrap (cloud container)
```bash
cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]" && cd ..
pnpm install
# sanity
(cd backend && .venv/bin/python -m pytest -q -p no:warnings)        # expect 268 passed
scripts/test-backend-pg.sh                                           # same on PostgreSQL 16 (starts cluster)
pnpm -r typecheck && pnpm -r test && pnpm lint
node scripts/gen-api.mjs                                             # regenerate TS API types after ANY backend change
```
Run the stack: `scripts/e2e-backend.sh` (fresh seeded API on :8000) + `pnpm dev:user` (:5173) + `pnpm dev:admin` (:5174/admin/).
Demo staff logins (password `Gazyar1405`): admin, operator, technician, ambassador1, ambassador2, finance. Demo subscriber with password: first seeded user (see `app/cli.py::_demo_rich`); others log in by OTP — in dev the API returns `dev_code`.

### Repository map
```
backend/app/core/        infrastructure (config, db, auth/JWT, crypto, rbac, audit, ratelimit, settings_registry, jalali, normalize, images, storage, sms, events, scheduler)
backend/app/modules/     auth staff audit settings files regions subscribers users readings notifications points dashboard   (stage 1)
                         cases referrals content analytics                                                                  (stage 2)
                         store finance tickets reports surveys                                                              (stage 3)
backend/tests/           conftest factories; core/ unit; api/ per stage (+ permission matrix)
backend/alembic/         3 migrations (stage1, stage2, stage3) — generate new ones with autogenerate, verify on PostgreSQL
packages/core            pure TS: ApiClient, generated schema.ts (S<"Name"> types), i18n (digits/jalali/normalize), validators, labels, format, platform(.web)
packages/data            TanStack Query client, SessionProvider/useSession/useCan, qk key factory, useApiGet/useApiMutation
packages/motion          Spring, shared ticker, tween, presets (ζ documented), VelocityTracker, rubberband, reduced-motion
packages/ui              React DOM design system — PARTIAL (see below)
apps/user                PWA shell config only (vite.config.ts, index.html, src/env.ts, icons, capacitor.config.ts) — NO screens yet
apps/admin               shell config only (vite base /admin/, src/env.ts) — NO screens yet
e2e/                     playwright.config.ts (3 projects), helpers.ts — no specs yet
deploy/ scripts/ docs/   compose, nginx, backup, gen-api, test-backend-pg, e2e-backend; DEPLOYMENT/TESTING/SECURITY docs
docs/handoff/            the exact sub-agent prompts used so far (reuse them)
```

### State of packages/ui (what exists)
tokens.ts (R, SHADOW, EASE, GESTURE, Z, SPACE, FONT, BREAKPOINTS), theme/ (palettes day+night with contrast test, ThemeProvider writing CSS vars, `v()`, bootTheme, modes day/night/system), styles/global.css (Vazirmatn font-face from the `vazirmatn` npm pkg, reset, keyframes, reduced-motion), text/ (Title, Head, Body, Cap, Num, Lat, Code, Money, Points), primitives/ (Pressable, Portal, VisuallyHidden, FocusTrap), motion/ (useSpringRef/useSpringBind/useSpringState/useReducedMotionSync, Fade, Reveal, Presence, CountUp, Collapse, Shake), icons/ (hand-drawn set), kit/ (Button, Badge, Card, Choice[Checkbox/Radio], Feedback[Empty/Banner?], Field[TextField/TextArea/Select], KeyValue, Layout[Stack/Inline], ListRow, Progress[Ring/Bar], Segmented, Skeleton, Spinner, Stat, Switch, Tabs, Toolbar).
`src/index.ts` barrel was being rewritten when work stopped — **verify it exports everything** (`pnpm --filter @gazyar/ui typecheck && test`).

**Still to build in packages/ui** (full spec = `docs/handoff/workflow-ui-design-system.js`, constant `UI_ADVANCED_PROMPT`, items 1–10):
1. overlays: overlayStack (+Android back), draggable Sheet (port MediStock maths), Dialog, ConfirmDialog, Toast system, Popover/Menu
2. list: VirtualList, HStrip, DataTable (server sort/paging, selection, responsive cards < md), Pagination, FilterBar
3. pickers: JalaliCalendar, JalaliDatePicker, JalaliRangePicker (presets), PickerSheet (searchable)
4. charts (load the `dataviz` skill first): LineChart, BarChart (actual vs 3-yr baseline), Donut, Sparkline, Gauge — animated draw-in, RTL axes, Persian digits, accessible
5. media: PhotoPicker (capture=environment, client downscale), UploadProgress, ImageViewer (zoom/pan/rotate, shared-element), FileDrop
6. feedback: SuccessBurst, StepProgress, ScreenScroll (elastic + pull-to-refresh), OfflineBanner, ErrorBoundary
7. layout: PillNav, TopBar (phone); Sidebar, AdminTopBar, PageHeader (admin)
8. router: StackRouter (push/pop parallax, edge swipe-back, tab stacks, History API deep links)
9. demo gallery app (`pnpm --filter @gazyar/ui demo`) showing every component
10. tests for all of the above

Design reference (motion/gestures/RTL lessons): public repo `cyrus-saedi2027/nemoone-medistock` → `MediStock_App.zip` → `README.md`, `docs/01..07`, `source/system/**`, `source/ui/**`, `screenshots/`. Clone + unzip into /tmp and read before UI work.

### Next steps (do them in this order; commit + push after each)
1. **Finish packages/ui** items 1–10 above. Verify: typecheck, vitest, eslint, then Playwright screenshots of the demo at 390×844 and 1440×900 in day/night (look at them).
2. **User app shell** (`apps/user/src`): `main.tsx` (ThemeProvider + useReducedMotionSync + DataProvider(api, queryClient) + SessionProvider(restore = api.restoreSession() then GET /api/v1/app/me)), `App.tsx` with StackRouter + PillNav tabs [خانه، مصرف، کیف پول، آموزش، پروفایل], auth gate, OfflineBanner, route table `routes.tsx` pointing to lazy `features/<x>/index.tsx`.
3. **User app features** (each a folder under `apps/user/src/features/`, endpoints in brackets):
   - auth: onboarding slides; signup [POST app/auth/signup/start|verify|complete]; not-eligible screen with the exact R09 text; OTP input with countdown/resend; terms; login OTP/password [app/auth/login/*]
   - home: points card (CountUp) [app/points/balance], current period card [app/readings/current], case banner [app/case], tips [app/content]
   - readings: new reading flow (PhotoPicker → value with Persian digits → Jalali date → upload progress → SuccessBurst) [POST app/readings multipart], history + detail with revisions/events/resubmit [app/readings, app/readings/{id}]
   - analytics: consumption vs 3-yr baseline charts, totals, CO₂ [app/analytics/consumption]
   - case: timeline, visit, estimate consent sheet (accept/decline) [app/case, POST app/case/consent]
   - wallet & store: balance + next release, ledger [app/points/ledger], store categories/items, redeem sheets (product+address / cash+IBAN / donation amount) [app/store, POST app/store/redeem], my requests + cancel [app/store/redemptions]
   - learn: feed by tier + article reader (render Markdown as text — no HTML) [app/content, app/content/{slug}]
   - profile: name, national code, IBAN, login method/password, theme [app/me, PATCH app/me, POST app/me/login-method]; referrals [app/referrals]; surveys [app/surveys, POST …/answers]; tickets list/new(with attachments)/thread/rate [app/tickets…]; notifications inbox [app/notifications, POST …/read]
4. **Admin shell** (`apps/admin/src`): React Router 7 under basename `/admin`, login (+2FA, must-change-password) [admin/auth/*], Sidebar filtered by `useCan(permission)`, AdminTopBar (notifications, theme, user menu).
5. **Admin features** (`apps/admin/src/features/`):
   - dashboard: KPI cards + series + breakdown, filters region/date/status/expert [admin/dashboard, admin/regions]
   - readings queue: tabs pending/flagged/…, keyboard review, ImageViewer, 3-yr history chart, approve/correct/needs-correction/reject with reasons, claim [admin/readings…]
   - subscribers & users: list/search/detail, Excel import wizard (template download → upload → error report → commit) [admin/subscribers…, admin/users…]
   - cases: list/kanban, detail with allowed_actions (call, checklist, evaluate, visit, photos, estimate, executed, submit-final, final-approve, return, close, assign), calendar, workload [admin/cases…, admin/staff/ambassadors]
   - points & referrals & finance & store: rules editor, ledger, suspend/adjust, referral review, redemption queue + fulfill, catalog CRUD [admin/points…, admin/referrals…, admin/finance…, admin/store…]
   - tickets, content (Markdown editor + preview + cover upload + tier targeting), broadcasts (segment preview), surveys builder/results [admin/tickets…, admin/content…, admin/notifications/broadcasts…, admin/surveys…]
   - reports (catalog, filters, chart, export xlsx/csv, snapshots), settings (grouped, finance keys read-only unless permitted), staff & roles, access review, audit + login logs [admin/reports…, admin/settings, admin/staff…, admin/audit…]
6. **E2E specs** in `e2e/user/*.spec.ts` and `e2e/admin/*.spec.ts`: signup→OTP→reading→operator approves→points pending; ineligible signup message; case flow to consent; redeem + finance approve; ticket round trip; admin responsive check. Run `pnpm e2e`.
7. Update `ROADMAP.md` §7 status table; final review pass (`/code-review`, `/security-review`).

### How sub-agents were used (and why runs failed)
`docs/handoff/*.js` are Workflow scripts with the full prompts (PREAMBLE + per-package instructions). Every failed run failed only on the **account usage limit**, never on code — partial files persist, so re-running with the "RESUMING INTERRUPTED WORK" note continues where it stopped. If the account is limited, prefer doing one item at a time inline instead of large parallel workflows.

### Conventions you must keep
- Every business number is a setting (`backend/app/core/settings_registry.py`), never a literal.
- Points only via `app.modules.points.service.award/spend/refund/suspend` with idempotency keys.
- Staff mutations → `audit.record(...)`; admin routes declare permissions (`require(P.X)`); row-level rules in services.
- No enumeration on public auth endpoints (identical answers; decoy OTP).
- Frontend: no business logic in screens; `packages/core|motion|data` stay DOM-free (ESLint enforces) so a React Native app can reuse them later (native-vs-web decision is still open — see ROADMAP §4).
- Persian UI: `dir=rtl`, Persian digits on output (`toFa`/`<Num>`), ASCII digits for values, Jalali dates, **no letter-spacing on Persian text**, logical CSS properties only.
- After any backend change: `node scripts/gen-api.mjs`, run backend tests on SQLite **and** `scripts/test-backend-pg.sh`, autogenerate an Alembic migration and verify `alembic check`.
- Tests ship with each feature; whole suite re-runs after each feature (regression).

### Known issues / open questions
- Business numbers awaiting the client's decision (threshold basis, reduction %, free cap, co-pay share, point→rial rate) — all editable in settings; defaults in ROADMAP §5.
- Client has not yet sent the UI design files / "Flowchart 1" — current visual design is ours.
- One mobile number can own only one account (`users.mobile_bidx` unique) — confirm with client.
- Native app decision pending; Capacitor config is ready for an APK from the PWA.
- SMS provider credentials (Kavenegar adapter exists; `GAZYAR_SMS_PROVIDER=kavenegar`).
