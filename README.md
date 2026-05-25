# ytdlp_client

A self-hosted downloader frontend/backend stack.

This repository includes a FastAPI backend, a Vue 3 + Vite frontend, SQLite persistence, JWT auth with refresh tokens, role-based admin support, and user profile image upload/cropping.

## What this template includes

- Authentication system with registration, login, access tokens, and refresh token rotation
- CSRF protection for state-changing API requests
- Role-based admin routes for user management
- User profile settings with username/password update
- Profile photo upload and crop workflow
- Optimized image variants for avatar, thumbnail, and preview views
- Recent profile image history with preview and restore support
- Static file serving for uploaded profile images
- Local SQLite support with SQLAlchemy 2.0 and Alembic migrations

## Architecture

- Backend: FastAPI + SQLAlchemy + SQLite
- Frontend: Vue 3 + Vite + Pinia
- Auth: JWT access tokens + refresh token rotation stored in secure cookies
- Image processing: Pillow for profile image resizing and cropping
- Migrations: Alembic for database schema changes

## Features

### Authentication

- Register new users
- Login with username/password
- Get current user details
- Refresh access tokens via long-lived refresh tokens
- Logout / revoke refresh session
- List and revoke active refresh sessions

### Profile management

- Update current username
- Change password
- Upload a profile image
- Crop the uploaded image to set the avatar area
- Edit an existing image crop
- Keep recent profile photos and restore previous images

### Admin support

- Bootstrap an initial admin account on startup via environment variables
- List users with pagination
- List roles
- Update users as an admin
- Delete users as an admin

## Getting started

### Backend

1. Create a `.env` file in `backend/` based on the example below.
2. Install dependencies:

```bash
cd backend
python -m pip install -r requirements.txt
```

3. Run database migrations:

```bash
cd backend
alembic upgrade head
```

4. Start the backend:

```bash
cd backend
uvicorn app.main:app --reload
```

### Frontend

1. Install dependencies:

```bash
cd frontend
npm install
```

2. Start the development server:

```bash
cd frontend
npm run dev
```

3. Open the app in your browser at `http://localhost:5173`

## Environment variables

The backend uses these environment variables:

- `SQLALCHEMY_DATABASE_URI` - database connection string (`sqlite+aiosqlite:///./app.db`)
- `JWT_SECRET` - required secret for signing JWTs
- `JWT_ISSUER` - JWT issuer string
- `JWT_AUDIENCE` - JWT audience string
- `JWT_ALGORITHM` - JWT algorithm (default `HS256`)
- `COOKIE_SAMESITE` - cookie same-site policy (`lax`, `strict`, `none`)
- `INITIAL_ADMIN_USERNAME` - initial admin username for bootstrap
- `INITIAL_ADMIN_EMAIL` - initial admin email for bootstrap
- `INITIAL_ADMIN_PASSWORD` - initial admin password for bootstrap
- `ADMIN_BOOTSTRAP_FORCE_ELEVATE_EXISTING` - allow promoting an existing user to admin
- `PROFILE_IMAGE_UPLOAD_DIR` - root directory for uploaded files
- `PROFILE_IMAGE_UPLOAD_SUBDIR` - subdirectory for profile uploads
- `PROFILE_IMAGE_URL_PATH` - mount path for static image serving
- `PROFILE_IMAGE_MAX_SIZE_MB` - max upload size for profile images
- `PROFILE_IMAGE_VARIANT_AVATAR_SIZE` - avatar image width/height
- `PROFILE_IMAGE_VARIANT_THUMBNAIL_SIZE` - thumbnail image size
- `PROFILE_IMAGE_VARIANT_PREVIEW_SIZE` - preview image size
- `PROFILE_IMAGE_VARIANT_QUALITY` - JPEG quality for generated image variants
- `PROFILE_IMAGE_VARIANT_SEPARATOR` - filename separator for variant files
- `CORS_ORIGINS` - comma-separated list of allowed frontend origins

### Example `.env`

```dotenv
SQLALCHEMY_DATABASE_URI=sqlite+aiosqlite:///./app.db
JWT_SECRET=your-very-secret-key
CORS_ORIGINS=http://localhost:5173

INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_EMAIL=admin@example.com
INITIAL_ADMIN_PASSWORD=supersecret
```

## API overview

### Auth routes (`/auth`)

- `POST /auth/register` - register a new user
- `POST /auth/login` - login and issue access token
- `POST /auth/refresh` - refresh access token using refresh cookie
- `POST /auth/logout` - revoke current refresh session
- `GET /auth/sessions` - list active refresh sessions
- `DELETE /auth/sessions` - revoke all sessions
- `DELETE /auth/sessions/current` - revoke the current session
- `DELETE /auth/sessions/{session_id}` - revoke a specific session
- `GET /auth/me` - get current authenticated user
- `PATCH /auth/me` - update username/password for current user
- `POST /auth/me/avatar` - upload a new profile image
- `PATCH /auth/me/avatar/{image_id}` - save crop metadata for a profile image
- `PATCH /auth/me/avatar/{image_id}/activate` - activate a previous image
- `GET /auth/me/avatars` - list recent profile images

### Admin routes (`/admin`)

- `GET /admin/users` - list users (admin only)
- `GET /admin/roles` - list roles (admin only)
- `PATCH /admin/users/{user_id}` - update a user (admin only)
- `DELETE /admin/users/{user_id}` - delete a user (admin only)

## Profile image workflow

- Profile images are uploaded to a static file directory and served from the backend under the configured upload path.
- The frontend crop editor sends crop coordinates back to the API.
- The backend stores crop metadata and generates optimized image variants:
  - `avatar` for app avatars
  - `thumbnail` for image previews
  - `preview` for the crop modal and restore flow
- Users can edit the current crop and restore a previous profile image.

## Guidance

This repository includes:

- working auth and profile management scaffolding
- frontend/backend separation with config-driven CORS
- profile image upload, crop, and variant generation
- admin role management

You can extend it by adding downloader jobs, background workers, additional frontend pages, or storage providers.

## Notes

- The backend mounts uploaded files at the configured `PROFILE_IMAGE_URL_PATH`.
- The admin bootstrap only runs when no admin user exists.
- Keep `JWT_SECRET` and admin credentials secure in production.
