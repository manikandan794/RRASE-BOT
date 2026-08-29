# AI & RAG

## Pipeline

```
User Question
   -> FAQ fuzzy match (app/services/chat_service.py)
   -> if matched: return verified FAQ answer, no AI call made
   -> else: RAG retrieval (app/rag/retriever.py)
        - embed the question via ProviderManager.embed()
        - query the Chroma vector store, top RAG_TOP_K results
        - drop anything below RAG_MIN_SIMILARITY (cosine similarity)
   -> ProviderManager.generate(question, context)
        - tries Ollama first; on failure/unconfigured, tries Gemini
        - the model is always given the retrieved context and instructed
          (app/ai/prompts.py) to refuse rather than invent RRASE-specific facts
   -> if no context was found, or no provider is reachable:
        return "information unavailable" and log an UnansweredQuestion
```

## Document ingestion (PDF)

`POST /api/v1/documents/upload` (admin/principal only):
1. Validates it's a PDF, under `MAX_UPLOAD_SIZE_MB`.
2. Extracts text with `app/documents/pdf_extractor.py` (pypdf). Encrypted
   PDFs with an empty password are handled; scanned/image-only PDFs raise
   a clear "no extractable text" error rather than silently indexing
   nothing.
3. Chunks the text (`app/rag/chunking.py` - sentence-aware, ~800 chars
   with 120 char overlap, tunable via `RAG_CHUNK_SIZE`/`RAG_CHUNK_OVERLAP`).
4. Embeds each chunk and stores it in Chroma (`app/rag/vector_store.py`),
   with a matching `KnowledgeChunk` row in Postgres for bookkeeping.

Uploaded documents are indexed immediately (an admin chose to upload this
file deliberately) but every chunk is still tagged with its source
document, so `DELETE /api/v1/documents/{id}` removes it from the vector
store too.

## Website knowledge import (never auto-trusted)

```
POST /api/v1/knowledge/website/import   (admin/principal)
   -> crawls the official site (same-domain links, shallow, capped pages)
   -> strips nav/script/style, collapses whitespace
   -> saves each page as WebsiteImportBatch(status="pending")

GET  /api/v1/knowledge/website/pending  -> reviewer sees raw cleaned text

POST /api/v1/knowledge/website/{id}/review
   { "approve": true, "edited_text": "...optional cleanup..." }
   -> only on approval does the text get chunked + embedded into the
      knowledge base; rejected pages are simply marked rejected
```

This is what implements "Website information must NOT be blindly
trusted" - nothing from the crawl is ever searchable by the chatbot until
a human explicitly approves it.

## AI Provider abstraction

- `app/ai/base.py` - `AIProvider` interface (`is_configured`, `generate`,
  `embed`), `AIResponse`, `AIProviderError`.
- `app/ai/ollama_provider.py` - primary. Calls a local/self-hosted Ollama
  instance's `/api/generate` and `/api/embeddings` endpoints. No API key.
- `app/ai/gemini_provider.py` - optional fallback. Only activates if
  `GEMINI_API_KEY` is set; calls Google's Generative Language API.
- `app/ai/provider_manager.py` - tries providers in order (Ollama, then
  Gemini), catching `AIProviderError` and falling through. Returns `None`
  if nothing is reachable, which the chat service treats as "no AI
  available" rather than crashing the request.

**Adding a future provider**: subclass `AIProvider`, implement
`is_configured`/`generate`/`embed`, and append an instance in
`ProviderManager._load_providers()`. Nothing else in the application
needs to change - the chat service and RAG pipeline only ever talk to
`ProviderManager`.

## Vector store

Chroma, persisted to disk at `VECTOR_DB_PATH` (default `./vector_store`).
No separate vector-database server is required. Each chunk is stored with
metadata (`source_type`, `source_label`, `source_id`) so retrieved context
can be attributed back to the document or web page it came from.
