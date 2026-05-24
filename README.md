# ytdlp_client

Self-hosted yt-dlp downloader backend + frontend template.

## Admin bootstrap configuration

The backend supports explicit initial admin creation through environment variables.
This is a one-time bootstrap that runs on startup, and it only creates or promotes an admin if no admin user already exists.

### Environment variables

- `INITIAL_ADMIN_USERNAME`
  - desired admin username
- `INITIAL_ADMIN_EMAIL`
  - desired admin email
- `INITIAL_ADMIN_PASSWORD`
  - desired admin password
- `ADMIN_BOOTSTRAP_FORCE_ELEVATE_EXISTING`
  - `true` / `1` / `yes` to allow promotion of an existing user with the same username or email

### `.env` format example

```dotenv
SQLALCHEMY_DATABASE_URI=sqlite+aiosqlite:///./app.db
JWT_SECRET=your-very-secret-key
CORS_ORIGINS=http://localhost:5173,http://10.0.0.124:5173

INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_EMAIL=admin@example.com
INITIAL_ADMIN_PASSWORD=supersecret
```

### Behavior details

- The app will bootstrap an admin if no admin exists and all three admin env vars are set.
- If an admin user already exists, the bootstrap does nothing, even if the admin env vars are present.
- If a user already exists with the same `username` or `email` and no admin exists:
  - that user will be promoted to admin only when `ADMIN_BOOTSTRAP_FORCE_ELEVATE_EXISTING=true`.
  - otherwise the bootstrap does nothing and preserves existing users.

#### Force-elevation example

```dotenv
INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_EMAIL=admin@example.com
INITIAL_ADMIN_PASSWORD=supersecret
ADMIN_BOOTSTRAP_FORCE_ELEVATE_EXISTING=true
```

This allows the bootstrap to promote an existing account that matches `username` or `email`.

### Recommended usage

- For self-hosted Docker with one user, set just the admin credentials.
- If you already have users and want to promote one of them by username or email, set `ADMIN_BOOTSTRAP_FORCE_ELEVATE_EXISTING=true`.
- Keep `JWT_SECRET` and `INITIAL_ADMIN_PASSWORD` secret.

### Notes

- The bootstrap happens once on server startup.
- After an admin exists, the startup bootstrap will no longer create or promote admin accounts.
- If you want to change the admin user after bootstrap, use the application UI/API or direct database updates, not env bootstrap.
