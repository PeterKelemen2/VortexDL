# VortexDL

A self-hosted video downloader with a full authentication system, background job processing, and optional delivery to remote machines via SFTP. Built on FastAPI and Vue 3.

## Table of contents

- [Features](#features)
- [Architecture](#architecture)
- [Quick start (Docker)](#quick-start-docker)
- [Local development](#local-development)
- [Configuration reference](#configuration-reference)
- [API reference](#api-reference)
- [Security model](#security-model)

---

## Features

### Downloads

- Enqueue yt-dlp download jobs from any URL yt-dlp supports
- Choose video quality (best, 1080p, 720p, 480p, 360p, audio-only)
- Choose audio format (AAC, MP3, Opus, FLAC, no extraction)
- Choose container format (MP4, MKV, WebM, best)
- Embed subtitles and thumbnails into the output file
- Download to browser, to a remote SFTP machine, or both
- Real-time job progress via Server-Sent Events
- Cancel and retry individual jobs
- Auto-download finished jobs in the browser (optional, persisted per device)
- Configurable concurrent workers (`JOB_WORKER_CONCURRENCY`)
- Per-job file size cap (default 10 GiB)

### Authentication

- Register and login with username and password
- Strict password policy: 12+ characters, uppercase letter, digit or special character
- JWT access tokens (short-lived) + refresh token rotation
- Refresh tokens are hashed with SHA-256 before storage - plaintext is never persisted
- Token rotation only triggers when <24 hours from expiry, preventing race conditions on rapid page reloads
- Secure, HttpOnly cookies with configurable `SameSite` policy
- CSRF token validation on all state-changing requests
- Rate limiting per endpoint (login, register, refresh, password reset, email verification)

### Two-factor authentication (TOTP)

- Set up TOTP via QR code (compatible with any authenticator app)
- 10 backup codes generated on setup, bcrypt-hashed in storage
- Regenerate backup codes with current TOTP code
- Disable 2FA with account password

### Email verification and password reset

- Optional email verification gate on registration
- Time-limited verification links (24h)
- Password reset tokens with 30-minute expiry
- Generic success messages on all email flows to prevent account enumeration

### Session management

- Track all active refresh sessions per user with device name, OS, and last-used timestamp
- Revoke individual sessions or all sessions at once
- Sessions survive cross-device use; each device gets its own token

### API keys

- Create named API keys with optional expiry
- Keys are displayed in full once on creation; only a SHA-256 hash is stored
- Revoke keys individually
- Authenticate API requests with the `X-API-Key` header

### Remote machines (SFTP delivery)

- Admin-managed remote machine registry (host, port, username, auth type)
- Authentication via password (Fernet-encrypted at rest) or SSH key path
- Trust-on-first-use host key pinning - fingerprint stored on first successful test
- Admin assigns machines to specific users
- Users browse remote folder trees before submitting jobs
- Downloaded files staged locally then transferred over SFTP; local copy deleted on remote-only jobs

### Profile management

- Upload a profile photo (JPEG, PNG, WebP; max 5 MB; max 16 MP / 8000px)
- Crop the image in the UI; backend regenerates variants on crop change
- Three automatic image variants: avatar (120px), thumbnail (200px), preview (420px)
- Keep up to N recent profile photos and restore any previous one
- EXIF orientation corrected automatically

### Admin settings

- Paginated user listing
- Update user roles, usernames, and passwords without the current password
- Delete users
- List and filter the append-only audit log (action, user, IP, timestamp)
- Create, update, delete, and test remote machine connections
- Assign and unassign machines per user

### Audit logging

- Append-only log; records are never updated or deleted by the application
- Events: LOGIN, LOGOUT, PASSWORD_CHANGED, 2FA_ENABLED, 2FA_DISABLED, API_KEY_CREATED, API_KEY_REVOKED, and more
- Survives user deletion (user_id set to NULL, username denormalized)

---

## Architecture

```
browser / API client
        │
        ▼
   nginx :80  ──── static SPA (Vue 3 + Vite)
        │
        │  proxy /auth /admin /uploads /jobs /health
        ▼
  uvicorn :8000  ──── FastAPI
        │
        ├── JWT + CSRF auth middleware
        ├── slowapi rate limiting
        ├── in-process job queue (asyncio workers)
        └── SQLite via SQLAlchemy 2.0 async + Alembic
```

**Backend**: Python 3.12, FastAPI, SQLAlchemy 2.0 (`Mapped[]` style), Alembic, yt-dlp, asyncssh, Pillow, passlib, python-jose, slowapi

**Frontend**: Vue 3 (Composition API), Vite, Pinia, Vue Router, Tailwind CSS 4, Lucide icons

**Database**: SQLite (single file, easy to back up)

**Container**: Combined image - supervisord runs nginx and uvicorn together

---

## Quick start (Docker)

### 1. Pull the image

```sh
docker pull ghcr.io/peterkelemen2/vortex-dl:latest
```

### 2. Create an `.env` file

```dotenv
JWT_SECRET=<at-least-32-chars-cryptographically-random-secret>

INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_EMAIL=admin@example.com
INITIAL_ADMIN_PASSWORD=<strong-password>

CORS_ORIGINS=http://your-domain.com
```

### 3. Create a `compose.yml`

```yaml
services:
  vortex-dl:
    image: ghcr.io/peterkelemen2/vortex-dl:latest # or pin to :1.0.0
    env_file:
      - .env
    volumes:
      - ./data:/app/data # SQLite database
      - ./uploads:/app/uploads # profile images
      - ./downloads:/app/downloads # finished job files
    ports:
      - "80:80"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost/health"]
      interval: 30s
      timeout: 5s
      retries: 5
      start_period: 30s

volumes: {}
```

### 4. Start

```sh
docker compose up -d
```

The app is available at `http://localhost`. The initial admin account is created automatically on first startup.

### Backing up

The entire application state lives in three directories next to `compose.yml`:

```sh
# Database
cp ./data/app.db ./data/app.db.bak

# Or archive everything
tar -czf vortex-backup-$(date +%Y%m%d).tar.gz data/ uploads/ downloads/
```

### Versioned images

Images are tagged by version and by `latest`:

```
ghcr.io/peterkelemen2/vortex-dl:latest
ghcr.io/peterkelemen2/vortex-dl:0.1.0
ghcr.io/peterkelemen2/vortex-dl:v0.1.0
```

Pin to a specific version in production to avoid unintended updates.

---

## Local development

### Prerequisites

- Python 3.12
- Node.js 22
- `ffmpeg` on your `PATH`

### Backend

```sh
cd backend

# Create a .env file
cat > .env <<EOF
JWT_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")
SQLALCHEMY_DATABASE_URI=sqlite+aiosqlite:///./app.db
CORS_ORIGINS=http://localhost:5173
INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_EMAIL=admin@example.com
INITIAL_ADMIN_PASSWORD=Admin1234!
EOF

pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend

```sh
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

### Building and testing the combined Docker image locally

```sh
# Build from the repo root
docker build -t vortex-dl-test .

# Create a test env file
echo "JWT_SECRET=$(openssl rand -hex 32)" > test.env
echo "INITIAL_ADMIN_USERNAME=admin" >> test.env
echo "INITIAL_ADMIN_EMAIL=admin@example.com" >> test.env
echo "INITIAL_ADMIN_PASSWORD=Admin1234!" >> test.env
echo "CORS_ORIGINS=http://localhost:8080" >> test.env

# Run it
docker compose -f docker-compose.local.yml up
```

The app is available at `http://localhost:8080`.

---

## Configuration reference

All configuration is via environment variables. Only `JWT_SECRET` is required.

### Core

| Variable          | Default                      | Description                                                                                      |
| ----------------- | ---------------------------- | ------------------------------------------------------------------------------------------------ |
| `JWT_SECRET`      | -                            | **Required.** At least 32 random characters. Used to sign JWTs and derive the remote secret key. |
| `JWT_ISSUER`      | `ytdlp_client`               | JWT `iss` claim.                                                                                 |
| `JWT_AUDIENCE`    | `ytdlp_client`               | JWT `aud` claim.                                                                                 |
| `JWT_ALGORITHM`   | `HS256`                      | Signing algorithm. Allowed: `HS256/384/512`, `RS256/384/512`, `ES256/384/512`.                   |
| `SECURE_COOKIES`  | `false`                      | Set to `true` when serving over HTTPS. Adds `Secure` flag to auth cookies.                       |
| `COOKIE_SAMESITE` | `lax`                        | `lax`, `strict`, or `none`.                                                                      |
| `CORS_ORIGINS`    | `http://localhost:5173`      | Comma-separated list of allowed origins. Wildcards are not allowed (credentialed CORS).          |
| `LOG_LEVEL`       | `INFO`                       | Python logging level.                                                                            |
| `APP_VERSION`     | _(read from `VERSION` file)_ | Override the reported application version.                                                       |

### Database

| Variable                  | Default                                | Description                         |
| ------------------------- | -------------------------------------- | ----------------------------------- |
| `SQLALCHEMY_DATABASE_URI` | `sqlite+aiosqlite:////app/data/app.db` | SQLAlchemy async connection string. |

### Admin bootstrap

| Variable                                 | Default | Description                                          |
| ---------------------------------------- | ------- | ---------------------------------------------------- |
| `INITIAL_ADMIN_USERNAME`                 | -       | Username for the initial admin account.              |
| `INITIAL_ADMIN_EMAIL`                    | -       | Email for the initial admin account.                 |
| `INITIAL_ADMIN_PASSWORD`                 | -       | Password for the initial admin account.              |
| `ADMIN_BOOTSTRAP_FORCE_ELEVATE_EXISTING` | `false` | If the username already exists, promote it to admin. |

### Email

When `SMTP_HOST` is unset the application runs in console mode: emails are printed to the log instead of sent.

| Variable                                | Default                 | Description                                      |
| --------------------------------------- | ----------------------- | ------------------------------------------------ |
| `SMTP_HOST`                             | -                       | SMTP server hostname. Unset = console mode.      |
| `SMTP_PORT`                             | `587`                   | SMTP port.                                       |
| `SMTP_USERNAME`                         | -                       | SMTP auth username.                              |
| `SMTP_PASSWORD`                         | -                       | SMTP auth password.                              |
| `SMTP_USE_TLS`                          | `true`                  | STARTTLS.                                        |
| `SMTP_USE_SSL`                          | `false`                 | SMTPS (implicit TLS).                            |
| `SMTP_TIMEOUT`                          | `10`                    | Connection timeout in seconds.                   |
| `EMAIL_FROM`                            | `no-reply@localhost`    | Sender address.                                  |
| `EMAIL_FROM_NAME`                       | _(APP_NAME)_            | Sender display name.                             |
| `REQUIRE_EMAIL_VERIFICATION`            | `false`                 | Block login until email is verified.             |
| `EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS` | `24`                    | Verification link lifetime.                      |
| `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES`   | `30`                    | Password reset link lifetime.                    |
| `FRONTEND_URL`                          | `http://localhost:5173` | Base URL used to build links in outgoing emails. |

### Rate limiting

| Variable                        | Default     |
| ------------------------------- | ----------- |
| `RATE_LIMIT_ENABLED`            | `true`      |
| `RATE_LIMIT_LOGIN`              | `5/minute`  |
| `RATE_LIMIT_REGISTER`           | `5/minute`  |
| `RATE_LIMIT_REFRESH`            | `30/minute` |
| `RATE_LIMIT_PASSWORD_RESET`     | `5/hour`    |
| `RATE_LIMIT_EMAIL_VERIFICATION` | `5/hour`    |

### Downloads

| Variable                       | Default                | Description                                                                             |
| ------------------------------ | ---------------------- | --------------------------------------------------------------------------------------- |
| `DOWNLOAD_DIR`                 | `./downloads`          | Root directory for downloaded files. Per-user subdirectories are created automatically. |
| `DOWNLOAD_MAX_FILE_SIZE_BYTES` | `10737418240` (10 GiB) | Maximum size of a single downloaded file.                                               |
| `JOB_WORKER_CONCURRENCY`       | `2`                    | Number of concurrent download workers.                                                  |

### Remote machines (SFTP)

| Variable                    | Default                     | Description                                                                                   |
| --------------------------- | --------------------------- | --------------------------------------------------------------------------------------------- |
| `REMOTE_SECRET_KEY`         | _(derived from JWT_SECRET)_ | Fernet key for encrypting stored SSH passwords. Set explicitly to decouple from JWT rotation. |
| `SSH_CONNECT_TIMEOUT`       | `15`                        | SSH connection timeout in seconds.                                                            |
| `REMOTE_BROWSE_MAX_ENTRIES` | `1000`                      | Maximum directory entries returned per browse call.                                           |

### Profile images

| Variable                               | Default          | Description                                            |
| -------------------------------------- | ---------------- | ------------------------------------------------------ |
| `PROFILE_IMAGE_UPLOAD_DIR`             | `./uploads`      | Root directory for uploaded files.                     |
| `PROFILE_IMAGE_UPLOAD_SUBDIR`          | `profile_images` | Subdirectory within the upload root.                   |
| `PROFILE_IMAGE_URL_PATH`               | `/uploads`       | URL path the backend mounts the upload directory at.   |
| `PROFILE_IMAGE_MAX_SIZE_MB`            | `5`              | Maximum upload size in megabytes.                      |
| `PROFILE_IMAGE_VARIANT_AVATAR_SIZE`    | `120`            | Avatar variant size in pixels.                         |
| `PROFILE_IMAGE_VARIANT_THUMBNAIL_SIZE` | `200`            | Thumbnail variant size in pixels.                      |
| `PROFILE_IMAGE_VARIANT_PREVIEW_SIZE`   | `420`            | Preview variant size in pixels.                        |
| `PROFILE_IMAGE_VARIANT_QUALITY`        | `85`             | JPEG quality for generated variants.                   |
| `PROFILE_IMAGE_VARIANT_SEPARATOR`      | `__`             | Filename separator between base name and variant name. |

---

## API reference

### Health

| Method | Path      | Auth | Description                                     |
| ------ | --------- | ---- | ----------------------------------------------- |
| `GET`  | `/health` | None | Returns `{"status":"ok","version":"<version>"}` |

### Auth (`/auth`)

| Method   | Path                                  | Auth           | Description                                           |
| -------- | ------------------------------------- | -------------- | ----------------------------------------------------- |
| `POST`   | `/auth/register`                      | None           | Register a new user                                   |
| `POST`   | `/auth/login`                         | None           | Login; issues access token and refresh cookie         |
| `POST`   | `/auth/refresh`                       | Refresh cookie | Rotate refresh token and issue new access token       |
| `POST`   | `/auth/logout`                        | Access token   | Revoke current refresh session                        |
| `POST`   | `/auth/request-verification`          | Access token   | Send email verification link                          |
| `POST`   | `/auth/verify-email`                  | None           | Verify email with token from link                     |
| `POST`   | `/auth/request-password-reset`        | None           | Send password reset link                              |
| `POST`   | `/auth/reset-password`                | None           | Reset password with token from link                   |
| `GET`    | `/auth/me`                            | Access token   | Get current user                                      |
| `PATCH`  | `/auth/me`                            | Access token   | Update username or password                           |
| `POST`   | `/auth/me/avatar`                     | Access token   | Upload a new profile image                            |
| `PATCH`  | `/auth/me/avatar/{image_id}`          | Access token   | Save crop for a profile image                         |
| `PATCH`  | `/auth/me/avatar/{image_id}/activate` | Access token   | Make a previous image active                          |
| `GET`    | `/auth/me/avatars`                    | Access token   | List recent profile images                            |
| `GET`    | `/auth/sessions`                      | Access token   | List active refresh sessions                          |
| `DELETE` | `/auth/sessions`                      | Access token   | Revoke all sessions                                   |
| `DELETE` | `/auth/sessions/current`              | Access token   | Revoke current session                                |
| `DELETE` | `/auth/sessions/{session_id}`         | Access token   | Revoke a specific session                             |
| `GET`    | `/auth/2fa/status`                    | Access token   | Get 2FA enabled status                                |
| `POST`   | `/auth/2fa/setup`                     | Access token   | Begin 2FA setup; returns QR code URI and backup codes |
| `POST`   | `/auth/2fa/verify`                    | Access token   | Confirm 2FA setup with a TOTP code                    |
| `POST`   | `/auth/2fa/disable`                   | Access token   | Disable 2FA (requires account password)               |
| `POST`   | `/auth/2fa/backup-codes`              | Access token   | Regenerate backup codes (requires current TOTP)       |

### Jobs (`/jobs`)

| Method | Path                    | Auth                       | Description                                 |
| ------ | ----------------------- | -------------------------- | ------------------------------------------- |
| `POST` | `/jobs`                 | Access token               | Enqueue a new download job                  |
| `GET`  | `/jobs`                 | Access token               | List jobs (paginated, filterable by status) |
| `GET`  | `/jobs/{job_id}`        | Access token               | Get a single job                            |
| `GET`  | `/jobs/{job_id}/file`   | Access token               | Download the completed file                 |
| `POST` | `/jobs/{job_id}/cancel` | Access token               | Cancel a queued or running job              |
| `POST` | `/jobs/{job_id}/retry`  | Access token               | Re-enqueue a failed or cancelled job        |
| `GET`  | `/jobs/stream`          | Access token (query param) | SSE stream for real-time job progress       |

**Job create payload**:

```json
{
  "url": "https://...",
  "quality": "best | 1080p | 720p | 480p | 360p | audio_only",
  "audio_format": "none | aac | mp3 | opus | flac",
  "container": "best | mp4 | mkv | webm",
  "embed_subtitles": false,
  "embed_thumbnail": false,
  "destination": "local | remote | both",
  "remote_machine_id": null
}
```

### API keys (`/auth/api-keys`)

| Method   | Path                      | Auth         | Description          |
| -------- | ------------------------- | ------------ | -------------------- |
| `GET`    | `/auth/api-keys`          | Access token | List API keys        |
| `POST`   | `/auth/api-keys`          | Access token | Create a new API key |
| `DELETE` | `/auth/api-keys/{key_id}` | Access token | Revoke a key         |

### Admin (`/admin`)

| Method   | Path                                          | Auth  | Description                             |
| -------- | --------------------------------------------- | ----- | --------------------------------------- |
| `GET`    | `/admin/users`                                | Admin | List users (paginated)                  |
| `PATCH`  | `/admin/users/{user_id}`                      | Admin | Update user role, username, or password |
| `DELETE` | `/admin/users/{user_id}`                      | Admin | Delete a user                           |
| `GET`    | `/admin/roles`                                | Admin | List roles                              |
| `GET`    | `/admin/audit-logs`                           | Admin | List audit log entries (filterable)     |
| `GET`    | `/admin/remote-machines`                      | Admin | List remote machines                    |
| `POST`   | `/admin/remote-machines`                      | Admin | Create a remote machine                 |
| `PATCH`  | `/admin/remote-machines/{id}`                 | Admin | Update a remote machine                 |
| `DELETE` | `/admin/remote-machines/{id}`                 | Admin | Delete a remote machine                 |
| `POST`   | `/admin/remote-machines/{id}/test`            | Admin | Test SSH/SFTP connection                |
| `GET`    | `/admin/remote-machines/{id}/users`           | Admin | List users assigned to a machine        |
| `POST`   | `/admin/remote-machines/{id}/users/{user_id}` | Admin | Assign a user to a machine              |
| `DELETE` | `/admin/remote-machines/{id}/users/{user_id}` | Admin | Unassign a user                         |

### Remote machines (user) (`/remote-machines`)

| Method | Path                           | Auth         | Description                            |
| ------ | ------------------------------ | ------------ | -------------------------------------- |
| `GET`  | `/remote-machines`             | Access token | List machines assigned to current user |
| `GET`  | `/remote-machines/{id}/browse` | Access token | Browse a directory on the machine      |

---

## Security model

- **Passwords** are hashed with bcrypt (passlib). Plaintext is never written anywhere.
- **Refresh tokens** are hashed with SHA-256 before storage. The plaintext token is only ever in memory or in a cookie.
- **JWT algorithm allowlist** prevents selection of the `none` algorithm regardless of configuration.
- **CORS** is configured to reject wildcard origins when credentials are enabled.
- **CSRF** cookies are validated on all state-changing requests.
- **Rate limiting** is applied per-endpoint to slow credential stuffing and enumeration attacks.
- **Account enumeration** is prevented with constant-time authentication and generic success messages on email flows.
- **Path traversal** in file downloads is prevented by resolving paths and asserting they are within the user's download directory. Remote SFTP paths are constrained to the machine's configured download folder.
- **SSH passwords** are encrypted at rest with Fernet symmetric encryption. The key defaults to a derivative of `JWT_SECRET` but can be set independently via `REMOTE_SECRET_KEY`.
- **SSH host keys** are pinned on first successful connection (TOFU). Subsequent connections reject a changed fingerprint.
- **Decompression bomb prevention** is applied to all uploaded images (16 MP / 8000px hard limits).
- **Security headers** are set on every response: `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`. HSTS is added when `SECURE_COOKIES=true`.
- **Audit logs** are append-only and survive user deletion.
