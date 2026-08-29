# Database

PostgreSQL, accessed through SQLAlchemy 2.0 ORM, versioned with Alembic.
`DATABASE_URL` is read from the environment (`app/config.py`) and never
hard-coded. Tests use an isolated in-memory SQLite database built from the
same models, so `pytest` never touches a real Postgres instance.

## Tables

| Table                    | Purpose                                                          |
|--------------------------|-------------------------------------------------------------------|
| `roles`                  | The four standard roles: student, faculty, admin, principal      |
| `users`                  | All accounts (roles attached via `user_roles`)                   |
| `user_roles`             | Many-to-many link between users and roles                        |
| `system_settings`        | Small operational key/value settings (not for secrets)            |
| `college_info`           | Key/value general facts (address, affiliation, established year) |
| `departments`            | Academic departments                                              |
| `faculty_profiles`       | Faculty directory entries, optionally linked to a `users` row    |
| `courses`                | Programs offered, per department                                  |
| `faqs`                   | Published Q&A pairs checked before any AI call                   |
| `notices`                | Announcements                                                     |
| `events`                 | Campus events with start/end times                                 |
| `facilities`             | Campus facilities (library, labs, hostel, etc.)                   |
| `contacts`               | Office/department contact details                                 |
| `uploaded_documents`     | PDFs uploaded by admin/principal, with extraction status          |
| `website_import_batches` | Raw cleaned text pulled from the official site, pending review    |
| `knowledge_chunks`       | Approved, chunked text; embeddings live in the Chroma vector store, keyed by this row's `id` |
| `conversations`          | One row per chat session                                           |
| `chat_messages`          | Every user/assistant turn, tagged with `answer_source`             |
| `feedback`               | Thumbs up/down + optional comment per message                     |
| `unanswered_questions`   | Logged whenever the pipeline can't answer confidently              |
| `audit_logs`             | Every admin/principal write action                                 |

Every table includes `created_at` / `updated_at` (via `TimestampMixin`).
`users` additionally supports soft deletion.

## Running migrations

```bash
cd backend
alembic upgrade head        # apply all migrations (0001_initial_foundation, 0002_full_feature_set)
alembic revision --autogenerate -m "describe your change"
alembic downgrade -1         # roll back one migration
```

## Seeding

```bash
python scripts/seed_roles.py
```

Inserts the four standard role rows if they don't already exist - this is
structural data the application logic depends on (registration/login will
fail with a clear error if it hasn't been run).

Create your first admin account after seeding roles, either by promoting a
registered user directly in the database, or by temporarily running:

```bash
python -c "
from app.database.session import SessionLocal
from app.auth.security import hash_password
from app.models import User, UserRole, Role, RoleName
db = SessionLocal()
role = db.query(Role).filter_by(name=RoleName.ADMIN).first()
user = User(email='admin@rrase.edu', full_name='College Admin', hashed_password=hash_password('CHANGE_ME_NOW'))
db.add(user); db.flush()
db.add(UserRole(user_id=user.id, role_id=role.id))
db.commit()
print('Admin created - change the password immediately after first login.')
"
```
