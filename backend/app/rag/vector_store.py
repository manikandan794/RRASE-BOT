"""
Persistent vector database wrapper around Chroma.

Chroma persists to disk under VECTOR_DB_PATH (no separate vector-DB server
required), which keeps deployment simple for a single-college install.
"""
import logging
import threading

import chromadb

from app.config import get_settings

logger = logging.getLogger("rrase_college_ai.rag.vector_store")

_client = None
_collection = None
_lock = threading.Lock()

COLLECTION_NAME = "rrase_knowledge"


def get_collection():
    global _client, _collection
    if _collection is not None:
        return _collection
    with _lock:
        if _collection is None:
            settings = get_settings()
            _client = chromadb.PersistentClient(path=settings.VECTOR_DB_PATH)
            _collection = _client.get_or_create_collection(
                name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
            )
    return _collection


def upsert_chunk(chunk_id: str, text: str, embedding: list[float], metadata: dict) -> None:
    collection = get_collection()
    collection.upsert(ids=[chunk_id], embeddings=[embedding], documents=[text], metadatas=[metadata])


def reset_collection() -> None:
    """Deletes and recreates the collection - used by the admin rebuild-index
    operation (e.g. after switching embedding model/provider, where old
    vectors would otherwise sit at an incompatible dimension)."""
    global _client, _collection
    with _lock:
        settings = get_settings()
        if _client is None:
            _client = chromadb.PersistentClient(path=settings.VECTOR_DB_PATH)
        try:
            _client.delete_collection(COLLECTION_NAME)
        except Exception:  # pragma: no cover - collection may not exist yet
            pass
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
        )


def delete_chunk(chunk_id: str) -> None:
    try:
        get_collection().delete(ids=[chunk_id])
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed deleting chunk %s from vector store: %s", chunk_id, exc)


def query(embedding: list[float], top_k: int) -> list[dict]:
    """Returns a list of {id, text, metadata, distance} ordered by relevance."""
    collection = get_collection()
    if collection.count() == 0:
        return []
    result = collection.query(query_embeddings=[embedding], n_results=min(top_k, collection.count()))
    hits = []
    ids = result.get("ids", [[]])[0]
    docs = result.get("documents", [[]])[0]
    metas = result.get("metadatas", [[]])[0]
    dists = result.get("distances", [[]])[0]
    for i in range(len(ids)):
        hits.append({"id": ids[i], "text": docs[i], "metadata": metas[i], "distance": dists[i]})
    return hits
