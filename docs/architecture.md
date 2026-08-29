# Architecture Overview

## Current state

```
frontend/ (static HTML/CSS/JS, Bootstrap 5)
   index.html, chat.html, login.html, register.html, about.html
   admin/, principal/, faculty/  - role-specific dashboards
        |
        |  fetch("/api/v1/...") with a Bearer JWT once logged in
        v
backend/ (FastAPI)
   app/main.py           - app factory, middleware, router mount
   app/config.py         - environment-based settings (pydantic-settings)
   app/api/v1/           - versioned API routes (auth, users, content CRUD,
                            documents, knowledge, chat, feedback, analytics)
   app/auth/             - JWT issuing/verification, RBAC dependencies
   app/models/           - every SQLAlchemy ORM model
   app/schemas/          - Pydantic request/response models
   app/services/         - chat orchestration, website import, audit log
   app/ai/               - AIProvider interface, Ollama/Gemini implementations,
                            ProviderManager fallback chain
   app/rag/              - chunking, Chroma vector store, retriever, indexer
   app/documents/        - PDF text extraction
        |
        v
PostgreSQL (via DATABASE_URL, managed by Alembic migrations)
        |
        +-- Chroma persistent vector store (VECTOR_DB_PATH, on disk)
        +-- Ollama (primary AI + embeddings, self-hosted)
        +-- Gemini (optional fallback AI + embeddings, cloud API)
```

## Request flow: a student asks a question

```
POST /api/v1/chat {question}
   |
   v
1. Structured FAQ lookup (fuzzy match against published FAQs)
   |-- match found --> return verified FAQ answer (answer_source="faq")
   |
   v (no match)
2. RAG retrieval: embed the question, query the vector store for
   approved KnowledgeChunk rows, drop anything below RAG_MIN_SIMILARITY
   |
   v
3. AI Provider Manager: try Ollama, then Gemini, generating from the
   retrieved context only (never from open-ended model knowledge)
   |-- context + AI response --> return grounded answer (answer_source="rag_<provider>")
   |-- no context, or no provider reachable --> "information unavailable"
        + log an UnansweredQuestion for admin/principal review
```

## Design principles

1. **Database-first answering** - FAQs/structured data are checked before
   any AI call.
2. **Nothing reaches the AI ungrounded** - the AI is only ever asked to
   answer from retrieved context, and is explicitly instructed to refuse
   rather than invent RRASE-specific facts.
3. **Website content is never auto-trusted** - `WebsiteImportBatch` rows
   sit at `status=pending` until an admin/principal approves them; only
   then are they chunked, embedded, and searchable.
4. **AI provider abstraction** - `AIProvider` base class, `OllamaProvider`
   (primary) / `GeminiProvider` (optional fallback) implementations behind
   a `ProviderManager`. Adding a new provider is one new file plus one
   line in `ProviderManager._load_providers()` - no other code changes.
5. **RBAC from the schema up** - every write endpoint is protected by
   `require_roles(...)`; students can never reach admin/principal-only
   routes, and faculty dashboards are read-only by design.
6. **No secrets in code** - all configuration flows through environment
   variables; `app/config.py` is the single place that reads them.
7. **Environment-agnostic testing** - the test suite runs against an
   in-memory SQLite database with the AI provider manager mocked, so
   `pytest` passes identically on a laptop, CI, or the production server,
   without needing PostgreSQL/Ollama/Gemini reachable.
