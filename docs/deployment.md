# Deployment

Target production architecture:

```
Internet -> College Subdomain (DNS) -> Nginx (HTTPS, static frontend + reverse proxy)
                                              |
                                        Uvicorn (FastAPI backend)
                                              |
                                        PostgreSQL
                                              |
                                        +-- Ollama (self-hosted, primary AI)
                                        +-- Gemini (optional fallback, cloud)
```

## Local development (Windows / VS Code / localhost)

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# edit .env: set DATABASE_URL to your local Postgres, leave OLLAMA_BASE_URL
# as http://localhost:11434 if you have Ollama installed locally
python scripts\seed_roles.py
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Serve `frontend/` with any static file server (e.g. the VS Code "Live
Server" extension) and set `assets/js/config.js` `API_BASE_URL` to
`http://localhost:8000/api/v1`.

## Docker Compose (recommended for anything beyond a laptop)

```bash
cp backend/.env.example backend/.env   # edit values as needed
docker compose up --build -d
docker compose exec backend python scripts/seed_roles.py
docker compose exec backend alembic upgrade head
docker compose exec ollama ollama pull llama3.1
docker compose exec ollama ollama pull nomic-embed-text
```

This starts `postgres`, `ollama`, `backend`, and `nginx` (serving the
static frontend and reverse-proxying `/api/` to the backend on port 80).

## Production: Linux server + official college subdomain

1. Provision a Linux VPS/server with Docker + Docker Compose installed.
2. Point the subdomain (e.g. `chatbot.rrase.com`) at the server's IP via
   DNS (an A record).
3. Copy this repository to the server, fill in `backend/.env` with
   production values (a strong `JWT_SECRET_KEY`, `APP_ENV=production`,
   `CORS_ORIGINS=https://chatbot.rrase.com`, `COLLEGE_WEBSITE_URL=https://rrase.com/`).
   **Never hard-code the subdomain in application code** - it only ever
   appears in `.env` and the Nginx config.
4. Update `deployment/nginx/rrase.conf`'s `server_name` to the real
   subdomain, and `docker-compose.yml`'s nginx volume mount if you renamed
   the config file.
5. `docker compose up --build -d`, then run migrations/seeding/model pulls
   as shown above.
6. Obtain a TLS certificate, e.g. with Certbot:
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d chatbot.rrase.com
   ```
   Certbot will rewrite the Nginx config to add the `listen 443 ssl`
   block and redirect HTTP to HTTPS - the commented-out HTTPS example in
   `deployment/nginx/rrase.conf` shows the resulting shape if you'd rather
   configure it by hand.
7. Create the first admin account (see `docs/database.md` for the
   one-off script), then use the Admin Dashboard for everything else -
   department/course/FAQ data entry, document upload, and the official
   website import + review workflow.

## What's environment-driven (never hard-coded)

- `DATABASE_URL`, `OLLAMA_BASE_URL`, `GEMINI_API_KEY`, `COLLEGE_WEBSITE_URL`,
  `CORS_ORIGINS`, `JWT_SECRET_KEY`, `VECTOR_DB_PATH`, `UPLOAD_DIR` - all
  read from `backend/.env` via `app/config.py`. The Nginx `server_name`
  and the frontend's `assets/js/config.js` `API_BASE_URL` are the only two
  places that need a manual one-line edit per environment.
