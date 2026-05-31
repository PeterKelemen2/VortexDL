# Plan: Template Enhancement Features

## What Already Exists

**Backend:**

- JWT auth (access + refresh tokens with rotation, CSRF protection)
- Role-based access control (admin/user roles via DB table)
- Multi-device session management with metadata (device name, OS, IP)
- Admin user CRUD with pagination
- Profile image upload + cropping with variants (avatar/thumbnail/preview)
- Password strength validation
- Bootstrap initial admin on startup
- Alembic migrations
- Async SQLite via aiosqlite
- Health endpoint

**Frontend:**

- Login/register views (guestOnly guard)
- Settings view (tabbed: Account, Security, Users/admin)
- Admin view (minimal placeholder)
- Home view (minimal placeholder)
- Profile image cropper
- Session list + revocation UI
- Dark/light theme toggle
- PasswordStrengthMeter
- Modal, TextInput, PasswordInput, Dropdown reusable components
- Pinia auth store with retry logic
- Centralized API client with auto-refresh, CSRF, logging

---

## Proposed Feature Additions

### Phase 1 — Core Template Completeness (High Value)

1. **Email sending infrastructure** — SMTP service abstraction (`EmailService`) used by all email flows; configurable via env vars
2. **Email verification** — Mark users `is_verified`; require confirmation after register; resend endpoint; frontend verification landing page
3. **Password reset via email** — "Forgot password" link on login; time-limited reset token (stored hashed in DB); reset form view
4. **Rate limiting on auth endpoints** — `slowapi` middleware on `/auth/register`, `/auth/login`, `/auth/refresh` to prevent brute force
5. **Toast / notification system** — Frontend `useToast()` composable + `ToastContainer` component; currently no feedback mechanism exists outside inline error text

### Phase 2 — UX & Reusable Components (Medium Value)

6. **Reusable `<DataTable>` component** — Sortable/paginated table (the pagination in `UsersSettings` is currently inline, not reusable)
7. **Form validation composable** — `useForm({ fields, rules })` with field-level errors and dirty tracking; every form currently re-implements its own validation
8. **Loading skeleton components** — `SkeletonRow`, `SkeletonAvatar` etc. for list/card load states
9. **`useConfirm()` composable** — Promise-based confirm dialog (currently `Modal.vue` is wired manually per-use)

### Phase 3 — Security & Advanced Auth (High Value for Reuse)

10. **Two-factor authentication (TOTP)** — `pyotp`-based setup/verify endpoints; QR code provisioning URI; backup codes; frontend enrollment UI in Security settings
11. **API key management** — Per-user API keys (generated, stored hashed, named, revocable); useful for programmatic/CLI usage of the template app
12. **Audit log** — Append-only `audit_logs` table; records login, logout, password change, admin actions, user deletion; admin-visible in the UI

### Phase 4 — Infrastructure / DevOps

13. **Docker + docker-compose** — `Dockerfile` for backend, Vite prod build + nginx for frontend, `compose.yml` for one-command local dev
14. **`.env.example`** — Documented environment variable reference for all config options
15. **Background task queue** — Lightweight asyncio job queue with `JobStatus` tracking (queued → running → done/failed); the natural next step given this is the `ytdlp_client` template

---

## Files To Create / Modify

| File                                         | Action                                                                 |
| -------------------------------------------- | ---------------------------------------------------------------------- |
| `backend/app/services/email_service.py`      | Create                                                                 |
| `backend/app/models/user.py`                 | Add `is_verified`, `password_reset_token`, `password_reset_expires_at` |
| `backend/app/api/routes/auth.py`             | Add reset + verify endpoints                                           |
| `backend/app/core/config.py`                 | Add SMTP settings                                                      |
| `frontend/src/composables/useToast.js`       | Create                                                                 |
| `frontend/src/components/ToastContainer.vue` | Create                                                                 |
| `frontend/src/components/DataTable.vue`      | Create                                                                 |
| `frontend/src/views/VerifyEmailView.vue`     | Create                                                                 |
| `frontend/src/views/ResetPasswordView.vue`   | Create                                                                 |

---

## Open Questions

- **Email scope** — Is SMTP infrastructure in scope? If not, phases 1 and 3 can be deferred while phases 2 and 4 proceed first.
- **2FA complexity** — TOTP adds meaningful complexity (backup codes, recovery flow, enforcement). Include only if the template targets security-sensitive apps.
- **Priority order** — Recommended: Phase 1 → Phase 2 → Phase 4 → Phase 3. Adjust?
