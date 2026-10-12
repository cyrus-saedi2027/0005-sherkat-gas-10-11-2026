# راهنمای راه‌اندازی — Deployment guide

## ۱. اجرای محلی (توسعه)

```bash
# پیش‌نیاز: Python 3.12+، Node 22، pnpm 10
cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"
python -m app.cli seed --demo        # جدول‌ها + کاربران نمونه + ۳۰۰ مشترک نمونه با سابقهٔ مصرف ۳ ساله
uvicorn app.main:app --reload        # http://localhost:8000/docs
cd .. && pnpm install
pnpm dev:user                         # اپ کاربر  http://localhost:5173
pnpm dev:admin                        # پنل مدیریت http://localhost:5174/admin/
```

کاربران نمونهٔ پنل (رمز همه `Gazyar1405`): `admin`، `operator`، `technician`، `ambassador1`، `ambassador2`، `finance`.
در حالت توسعه کد یک‌بارمصرف در پاسخ API (`dev_code`) و لاگ سرور نمایش داده می‌شود؛ در production خاموش است.

## ۲. استقرار (production)

```bash
cp deploy/.env.example deploy/.env      # همهٔ مقادیر را عوض کنید — با کلیدهای پیش‌فرض، API بالا نمی‌آید
pnpm install && pnpm build              # apps/user/dist و apps/admin/dist
docker compose -f deploy/docker-compose.yml up -d --build
docker compose -f deploy/docker-compose.yml exec api python -m app.cli create-admin --username admin --password '<strong>'
```

* مهاجرت‌های پایگاه داده هنگام بالا آمدن API خودکار اجرا می‌شوند (`alembic upgrade head`).
* سرویس `scheduler` پیامک‌های صف را می‌فرستد و امتیازهای «در انتظار» را در پایان هر ماهِ جلالی آزاد می‌کند.
* TLS را جلوی nginx قرار دهید (یا گواهی را در `deploy/nginx.conf` اضافه کنید)؛ کوکی‌ها در production فقط روی HTTPS ارسال می‌شوند.
* سرور ترجیحاً داخل ایران باشد (پنل پیامک و دسترسی کاربران).

## ۳. پشتیبان‌گیری (R35، R42)

`scripts/backup.sh` هر شب نسخهٔ کامل پایگاه داده و فایل‌های بارگذاری‌شده را با چرخش ۱۴ روزه نگه می‌دارد:

```
15 2 * * *  /opt/gazyar/scripts/backup.sh >> /var/log/gazyar-backup.log 2>&1
```
بازیابی: `pg_restore -U gazyar -d gazyar --clean db-<stamp>.dump` و `tar -xzf uploads-<stamp>.tgz -C /srv/var`.
آزمایش بازیابی را دست‌کم ماهی یک‌بار روی سرور جداگانه انجام دهید.

## ۴. ساخت اپ اندروید / iOS از همین کد (Capacitor)

```bash
cd apps/user && pnpm build
npx cap add android && npx cap sync android && npx cap open android   # نیاز به Android Studio
```
برای iOS: `npx cap add ios` روی macOS با Xcode، و اکانت توسعه‌دهندهٔ اپل برای انتشار.

## ۵. تنظیمات کسب‌وکار
همهٔ اعداد سند (آستانهٔ ۳۵۰۰، جدول امتیاز، سهم ۳۰/۷۰، نرخ ریالی، سقف‌ها) از «پنل › تنظیمات» و «پنل › امتیازها» قابل تغییرند و هر تغییر در لاگ ممیزی ثبت می‌شود.
