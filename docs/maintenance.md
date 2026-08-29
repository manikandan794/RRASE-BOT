# Maintenance & Troubleshooting

## Common issues

**`/api/v1/health` returns `"status": "degraded"`, `"database": false`**
The backend started but can't reach PostgreSQL. Check `DATABASE_URL` in
`backend/.env`, confirm Postgres is running, and that the database exists
(`CREATE DATABASE rrase_college_ai;`).

**`alembic upgrade head` fails to connect**
Same checklist as above - Alembic reads the same `DATABASE_URL`.

**Chat always replies "I don't have verified information on that yet"**
This means no AI provider was reachable *and/or* no relevant knowledge
chunk was retrieved. Check, in order:
1. Is Ollama running and reachable at `OLLAMA_BASE_URL`? Try
   `curl $OLLAMA_BASE_URL/api/tags`.
2. Have you pulled the models? `ollama pull llama3.1` and
   `ollama pull nomic-embed-text`.
3. Has any content actually been approved into the knowledge base yet
   (Admin Dashboard -> Website Knowledge / Documents)? A fresh install has
   an empty vector store by design - add FAQs, upload documents, or run
   the website import before expecting AI-generated answers.
4. If you're relying on Gemini instead, confirm `GEMINI_API_KEY` is set
   and valid.

**PDF upload succeeds but the document stays "pending" with an error
about no embedding backend reachable**
The text was extracted and chunked fine, but nothing could embed it at
upload time. Once Ollama/Gemini is reachable, re-upload the document (or
extend the admin UI with a "re-index" action) - the extracted text isn't
lost, but chunks created with no reachable embedder are stored with
`embedded=false` and won't be retrieved until re-indexed.

**Website import returns a 502**
The backend couldn't reach `COLLEGE_WEBSITE_URL` at all (network egress
blocked, DNS issue, or the site is blocking automated requests). This is
expected on a server with no outbound internet access - the chatbot can
still answer from PDFs and FAQs entered directly.

**Import errors when running `pytest`**
Run `pytest` from inside `backend/` with the virtual environment
activated so `app.*` imports resolve correctly.

**CORS errors in the browser console**
Add the exact origin (protocol + host + port) you're serving the frontend
from to `CORS_ORIGINS` in `backend/.env`, then restart uvicorn.

**`bcrypt` / `passlib` errors like `AttributeError: module 'bcrypt' has no
attribute '__about__'`**
Some `bcrypt` 4.1+ releases changed an internal attribute `passlib` 1.7.4
reads. `requirements.txt` pins `bcrypt==4.0.1` to avoid this - if you've
upgraded it manually, reinstall with
`pip install "bcrypt==4.0.1" --force-reinstall`.

## Routine maintenance

- **Back up `vector_store/` and `uploads/` alongside your PostgreSQL
  backups** - losing either breaks document retrieval even if the
  database itself is intact, since embeddings and PDF/text sources live
  outside Postgres.
- **Re-run the website import periodically** (Admin Dashboard -> Website
  Knowledge -> Import) and re-review, since the official site will change
  over time and previously-approved pages are not automatically refreshed.
- **Check Unanswered Questions weekly** (Admin/Faculty Dashboard) - it's
  the fastest way to see what the FAQ/knowledge base is missing.
- **Review the Audit Log** periodically for unexpected admin/principal
  activity.

## Updating dependencies

```bash
cd backend
pip list --outdated
pip install --upgrade <package>
pip freeze > requirements.txt   # review the diff before committing
pytest                          # run the full suite after any upgrade
```
