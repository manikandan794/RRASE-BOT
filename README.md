# RRASE College AI Assistant

A production-oriented AI chatbot platform for RRASE College. The chatbot
answers using **verified college information only** (structured database
records, admin-approved documents, admin-approved website content) - when
it can't find a confident, grounded answer it says so plainly rather than
inventing one, and logs the question for staff review.

## Status: core platform complete

Authentication + RBAC, all content-management modules, PDF/website
knowledge ingestion with a human-review gate, the Ollama-primary /
Gemini-fallback RAG chatbot, feedback, analytics, audit logging, and the
Admin/Principal/Faculty dashboards are implemented and covered by
automated tests (14 passing). What still needs a **live environment** to
fully light up - a running Ollama install with models pulled, a real
PostgreSQL server, network access to the official website - is called out
explicitly in [docs/deployment.md](docs/deployment.md) and the in-app
"About / Roadmap" page. See that page for the full breakdown of what's
implemented vs. what needs live infrastructure.

## Features

- **Auth & RBAC**: JWT access/refresh tokens, bcrypt password hashing,
  four roles (student, faculty, admin, principal). Students self-register;
  staff accounts are created by an admin.
- **College content management**: full CRUD for College Info, Departments,
  Faculty, Courses, FAQs, Notices, Events, Facilities, Contacts.
- **Document knowledge base**: PDF upload -> text extraction -> chunking
  -> embedding -> persistent Chroma vector store.
- **Official website import**: crawl -> extract -> clean -> admin/
  principal review -> approve -> knowledge base. Nothing from the site is
  searchable by the chatbot until a human approves it.
- **AI provider abstraction**: Ollama (primary, self-hosted, no API key)
  with Gemini as an optional fallback, behind a common interface so adding
  a future provider is one new file.
- **Database-first, RAG-backed chat**: FAQ lookup first, then retrieval-
  augmented generation grounded in approved content, then an honest
  "unavailable" fallback that gets logged for staff review - never
  fabricated answers.
- **Chat history, feedback, unanswered-question tracking.**
- **Admin, Principal, and Faculty dashboards** (Faculty's is read-only by
  design - content management stays with admin/principal).
- **Analytics summary and full audit logging** of every admin/principal
  action.
- **Security**: rate limiting, file/type/size validation on uploads,
  secure headers, restricted CORS, `/docs` disabled in production.
- **Automated tests**: RBAC, chunking, and the full chat decision pipeline
  (AI calls mocked so the suite runs offline, no Ollama/Gemini/Postgres
  required).
- **Docker Compose** (Postgres + Ollama + backend + Nginx), an example
  Nginx reverse-proxy config, and HTTPS/subdomain deployment docs.

## Architecture

See [docs/architecture.md](docs/architecture.md) for the full request-flow
diagram and design principles.

## Technology stack

| Layer      | Technology |
|------------|------------|
| Frontend   | HTML5, CSS3, Bootstrap 5, vanilla JavaScript |
| Backend    | Python 3.11+, FastAPI, Uvicorn, Pydantic, SQLAlchemy, Alembic |
| Database   | PostgreSQL |
| Vector store | ChromaDB (persistent, on-disk) |
| AI         | Ollama (primary), Google Gemini (optional fallback) |

## Folder structure

```
rrase-college-ai/
├── backend/
│   ├── app/
│   │   ├── main.py, config.py
│   │   ├── api/v1/            # every route module (auth, users, content CRUD,
│   │   │                        documents, knowledge, chat, feedback, analytics)
│   │   ├── auth/               # JWT + RBAC dependencies
│   │   ├── database/, models/, schemas/
│   │   ├── services/           # chat orchestration, website import, audit log
│   │   ├── ai/                 # provider interface, Ollama/Gemini, fallback manager
│   │   ├── rag/                # chunking, vector store, retriever, indexer
│   │   ├── documents/          # PDF text extraction
│   │   └── utils/               # validators, rate limiter
│   ├── migrations/versions/     # 0001_initial_foundation, 0002_full_feature_set
│   ├── scripts/seed_roles.py
│   ├── tests/                   # pytest suite, SQLite-backed, AI calls mocked
│   ├── requirements.txt, Dockerfile, .env.example
├── frontend/
│   ├── index.html, chat.html, login.html, register.html, about.html
│   ├── admin/, principal/, faculty/   # role dashboards
│   └── assets/{css,js}/
├── deployment/nginx/rrase.conf   # example reverse-proxy config
├── uploads/, vector_store/        # runtime data (git-ignored)
├── docs/                          # architecture, database, ai-rag, deployment, security, maintenance
├── docker-compose.yml             # postgres + ollama + backend + nginx
└── README.md
```

## Local development (Windows / VS Code / localhost)

### Prerequisites

- Python 3.11 or newer
- PostgreSQL 14+ (running locally, or reachable over the network)
- (Optional but needed for AI answers) [Ollama](https://ollama.com) installed locally
- Git

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
# Edit backend\.env: set DATABASE_URL, a real JWT_SECRET_KEY, and (if you
# want AI-generated answers locally) leave OLLAMA_BASE_URL as
# http://localhost:11434

# Create the database once (via psql or pgAdmin):
#   CREATE DATABASE rrase_college_ai;

python scripts\seed_roles.py
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

If you have Ollama installed locally:
```powershell
ollama pull llama3.1
ollama pull nomic-embed-text
```

Serve `frontend/` with any static file server (e.g. VS Code's "Live
Server" extension on port 5500, matching the default `CORS_ORIGINS`).
Visit `http://localhost:8000/docs` for interactive API documentation.

Create your first admin account after seeding roles - see
[docs/database.md](docs/database.md) for the one-off script - then sign
in at `login.html` and use the Admin Dashboard for everything else.

## Docker Compose (Postgres + Ollama + backend + Nginx)

```bash
cp backend/.env.example backend/.env
docker compose up --build -d
docker compose exec backend python scripts/seed_roles.py
docker compose exec backend alembic upgrade head
docker compose exec ollama ollama pull llama3.1
docker compose exec ollama ollama pull nomic-embed-text
```

Visit `http://localhost/` for the frontend (proxied through Nginx) and
`http://localhost:8000/docs` for interactive API documentation
(the backend port is still exposed directly for this).

## Running tests

```bash
cd backend
source venv/bin/activate   # or venv\Scripts\activate on Windows
pytest -v
```

The suite uses an isolated in-memory SQLite database and mocks the AI
provider manager, so it runs identically with or without PostgreSQL,
Ollama, or Gemini available. All 14 tests currently pass, covering the
health endpoint, ORM models, registration/login, role-based access
control (a student is correctly rejected with 403 from admin-only
routes), text chunking, and the full chat decision pipeline (FAQ
short-circuit, grounded RAG answer, and the "no context/no provider"
unavailable + logging path).

> **Note on `bcrypt`**: `requirements.txt` pins `bcrypt==4.0.1` because
> newer `bcrypt` releases changed an internal attribute that `passlib`
> 1.7.4 reads at import time, which otherwise breaks password hashing
> with a cryptic `AttributeError`. If you ever bump `passlib` past 1.7.4,
> re-check whether this pin is still needed.

## Database migrations

```bash
alembic upgrade head
alembic revision --autogenerate -m "description"
alembic downgrade -1
```

See [docs/database.md](docs/database.md) for the full schema reference.

### Migration 0003 - faculty department scoping + approval hardening

Adds `department_id` to `faqs`, `notices`, `uploaded_documents`, and
`unanswered_questions`; `expires_at` to `notices`; `content_hash`/
`superseded_by` to `website_import_batches`; `embedding_provider`/
`embedding_model` to `knowledge_chunks`; and `reviewed_by` to
`uploaded_documents`. All new columns are nullable, so this is a
non-destructive upgrade - existing rows are left untouched. Run
`alembic upgrade head` as usual; no manual data backfill is required.

**Not tested against a live PostgreSQL instance in the development
environment this migration was written in** (no database was reachable).
The file was reviewed for correctness and its up/downgrade functions were
confirmed to import and execute their SQLAlchemy statement builders
without error, but you should run it against a real (ideally staging)
Postgres database and confirm `alembic upgrade head` then `alembic
downgrade -1` both succeed before relying on it in production.

## Newly added endpoints (this audit pass)

- `POST /api/v1/documents/{id}/review` - admin/principal approve or reject
  a pending document. **Approving is now required** before its content is
  embedded/retrievable - see "Knowledge approval security" below.
- `POST /api/v1/knowledge/rebuild-index` - admin/principal only. Wipes the
  vector store and re-embeds every currently-APPROVED chunk from
  Postgres. Use after changing `OLLAMA_EMBEDDING_MODEL` or if the vector
  store and Postgres drift apart.
- `GET/PUT /api/v1/faculty/me/department`, `GET/POST/PUT/DELETE
  /api/v1/faculty/me/faqs`, `GET/POST/PUT/DELETE
  /api/v1/faculty/me/notices` - faculty self-service, scoped server-side
  to the faculty member's own department (see "Faculty permissions"
  below).
- `POST /api/v1/unanswered-questions/{id}/route` - admin/principal assigns
  an unanswered question to a department; faculty only ever see questions
  routed to their own department via `GET /api/v1/unanswered-questions`.

## Knowledge approval security (audit fix)

Previously, uploading a PDF immediately chunked and embedded its content
with no review step, even though the document row itself was marked
`pending` - meaning unreviewed content was already retrievable by the
chatbot. This has been fixed:

1. Upload now only **stages** chunks (`app/rag/indexer.py:stage_chunks`)
   as `PENDING` in Postgres. Nothing is embedded and nothing is written
   to the vector store at this point.
2. An admin/principal must call `POST /documents/{id}/review` with
   `{"approve": true}` to embed the chunks and flip them to `APPROVED`,
   or `{"approve": false}` to delete the staged chunks entirely.
3. `app/rag/retriever.py` independently re-checks each vector-store hit's
   status in Postgres before using it - it does not trust vector-store
   metadata alone. Any hit that Postgres no longer considers `APPROVED`
   is dropped and purged from the vector store (defense in depth).

The same `stage_chunks`/`approve_source_chunks`/`reject_source_chunks`
functions are shared by the website-import review flow, so both source
types follow one reviewable lifecycle. See
`tests/test_knowledge_approval.py` and `tests/test_documents_api.py`.

## Faculty permissions (audit fix)

Faculty accounts previously had no write access anywhere. Faculty can now
manage their **own department's** description, FAQs, and notices, and see
unanswered questions an admin/principal has routed to their department -
through the new `/api/v1/faculty/me/*` routes. Every one of these routes
resolves the faculty member's department **server-side** from their
`Faculty` profile row; a `department_id` sent in the request body is
always ignored in favor of this server-derived value, so a faculty
account can never read or write another department's records. See
`tests/test_faculty_portal.py`, in particular
`test_faculty_department_id_in_payload_is_ignored` and
`test_faculty_cannot_edit_another_departments_faq`.

Faculty still cannot rename their department, change its HOD, touch
another department, or reach any `/api/v1/departments`, `/users`, or other
admin/principal-only route - those continue to require `require_roles`
with `ADMIN`/`PRINCIPAL`.

## What this audit pass did NOT cover

Being upfront about scope, so nothing here is mistaken for more complete
than it is:

- **Frontend**: not touched. The new `/faculty/me/*`, `/documents/{id}/review`,
  and `/knowledge/rebuild-index` endpoints have no corresponding UI yet.
- **Manual knowledge management** (admin-authored knowledge entries with
  their own Draft/Approved/Rejected/Archived lifecycle) was not built as
  a separate feature.
- **Full sync between structured DB content (departments/courses/
  facilities/contacts) and the vector store** was not implemented -
  FAQs are answered live from Postgres in chat (never stale), but those
  other content types are not yet indexed into RAG at all, so there is
  nothing to go stale for them either. This is a real gap versus the
  "manual database content should have a clear path into the chatbot
  knowledge system" goal.
- Docker/Nginx configuration, rate-limiting values, branding/frontend
  design, and the full 30-point pre-packaging checklist from the audit
  brief were not re-verified in this pass.
- Migration 0003 was reviewed and structurally validated but **not run
  against a live PostgreSQL database** (none was reachable in this
  environment) - see the migration note above.
- No Ollama, Gemini, or PostgreSQL instance was reachable in this
  environment, so the AI provider fallback, real embedding calls, and
  end-to-end RAG retrieval against a live vector store were exercised
  only through the mocked unit/API tests in `tests/`, not against real
  services. `27/27` automated tests pass (`pytest tests/ -q`), including
  9 new tests added in this pass covering the approval-security and
  faculty-scoping fixes specifically.

## Environment variables

See `backend/.env.example` for the complete list with comments. Never
commit a real `.env` file - it's already in `.gitignore`.

## Production deployment

See [docs/deployment.md](docs/deployment.md) for the full walkthrough:
Docker Compose, the example Nginx config in `deployment/nginx/rrase.conf`,
and HTTPS/subdomain setup via Certbot. Nothing hard-codes a subdomain -
it's entirely environment/config-driven.

## Security

See [docs/security.md](docs/security.md) for what's implemented and what
operational hardening is still worth doing before a public launch.

## AI & RAG pipeline

See [docs/ai-rag.md](docs/ai-rag.md) for the full pipeline, the provider
abstraction, and how the website-import review gate works.

## Troubleshooting

See [docs/maintenance.md](docs/maintenance.md).
