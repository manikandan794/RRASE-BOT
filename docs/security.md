# Security

## Implemented

- No secrets committed to source control (`.env` is git-ignored;
  `.env.example` holds only placeholders).
- Every credential-bearing value is read from the environment via
  `app/config.py` - never hard-coded.
- Passwords hashed with bcrypt (`passlib`); plaintext passwords are never
  stored or logged.
- JWT access + refresh tokens (`python-jose`), short-lived access tokens
  (`ACCESS_TOKEN_EXPIRE_MINUTES`), longer-lived refresh tokens
  (`REFRESH_TOKEN_EXPIRE_DAYS`) with a dedicated `/auth/refresh` endpoint.
- Role-based access control on every write endpoint via the
  `require_roles(...)` FastAPI dependency - verified by automated tests
  (`tests/test_auth.py`), including that a student is rejected (403) from
  admin-only routes.
- Staff accounts (faculty/admin/principal) can only be created by an
  existing admin through `/api/v1/users/staff` - never through public
  self-registration, which is hard-coded to the student role.
- Baseline secure HTTP headers on every response (`X-Content-Type-Options`,
  `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, and
  `Strict-Transport-Security` when `APP_ENV=production`).
- CORS restricted to an explicit, environment-configured origin list.
- `/docs` and `/redoc` automatically disabled when `APP_ENV=production`.
- File upload validation: PDF-only extension/content-type check, size
  capped at `MAX_UPLOAD_SIZE_MB`, filenames sanitized before touching disk
  (`app/utils/validators.py`).
- In-memory sliding-window rate limiting on the chat endpoint
  (`RATE_LIMIT_PER_MINUTE`, `app/utils/rate_limit.py`) - swap for a
  Redis-backed limiter if you scale to multiple backend processes.
- Structured audit logging (`audit_logs` table): every admin/principal
  create/update/delete, login, registration, document upload, and
  knowledge-review decision is recorded with actor, action, and target.
- SQL injection protection is inherent to using the SQLAlchemy ORM with
  parameterized queries throughout (no raw string-built SQL anywhere).
- The `/health` endpoint reports only booleans/short strings - no stack
  traces, connection strings, or internal configuration.

## Operational hardening still worth doing before a public launch

- Put the rate limiter behind Redis if you run more than one backend
  worker/process - the current in-memory limiter is per-process.
- Add CSRF protection if you ever serve the frontend and API from
  different origins with cookie-based auth (this project uses Bearer
  tokens in an `Authorization` header, which is not CSRF-vulnerable the
  way cookies are, but revisit this if the auth model changes).
- Rotate `JWT_SECRET_KEY` and any `GEMINI_API_KEY` periodically, and store
  them in a real secrets manager in production rather than a `.env` file
  on disk.
- Add automated dependency vulnerability scanning (`pip-audit` or similar)
  to CI.
- Review `RAG_MIN_SIMILARITY` and the system prompt in `app/ai/prompts.py`
  periodically against real chat logs to keep the "refuse rather than
  fabricate" behavior well-calibrated as the knowledge base grows.
