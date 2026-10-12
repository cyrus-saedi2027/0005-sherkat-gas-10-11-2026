# Security controls (R34–R36, R42)

* **Least-privilege RBAC** — 5 roles, 42 permissions, asserted in code and by a role×endpoint matrix test.
  Operators can never edit finance settings or delete data. Roles are re-read on every request, so a
  revoked role takes effect immediately; role changes also revoke refresh tokens.
* **Row-level rules** — ambassadors see only their own cases; ticket handlers only their unit; users only their own data.
* **Authentication** — argon2id passwords, 15-min JWT access tokens, rotating refresh tokens with reuse
  detection (a replayed token kills the family), httpOnly SameSite=Strict cookie for browsers, optional SMS 2FA for staff,
  lockout after repeated failures, constant-work dummy hash for unknown accounts.
* **No enumeration (R09)** — ineligible signup and unknown-number login produce byte-identical answers and the
  same DB/rate-limit work (decoy OTP challenges that can never verify); SMS is queued, never sent inline.
* **OTP** — 5 digits, HMAC-peppered hash, 120 s TTL, 5 attempts, resend cooldown, per-mobile and per-IP limits.
* **Rate limiting** — OTP, logins, uploads, and per-subject API limits (Redis in production) + nginx `limit_req`.
* **Input limits (OWASP API4)** — 1 MB JSON / 25 MB multipart streaming ceiling, page size ≤ 100, image pixel cap,
  upload type checked by decoding (not extension), images re-encoded (EXIF/GPS stripped).
* **Data protection** — mobile, national code and IBAN encrypted with MultiFernet (key rotation) and searched via
  HMAC blind indexes; masked in every list response.
* **Files** — never public; served only through short-lived HMAC-signed URLs; non-images forced to download.
* **Exports** — CSV/Excel cells are neutralised against formula injection.
* **Audit** — every staff mutation and every login attempt is recorded (who, what, before/after, IP, request id);
  periodic access review stamps and snapshots all staff roles.
* **Headers** — nosniff, frame-deny, strict referrer, CSP on API and web, HSTS in production.
* **Production guard** — the API refuses to boot in prod with development secrets, the console SMS provider, or OTP echo enabled.
