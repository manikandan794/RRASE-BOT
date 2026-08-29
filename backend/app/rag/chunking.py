"""
Document chunking.

Splits long text into overlapping, roughly-fixed-size chunks along
paragraph/sentence boundaries where possible, so each chunk is a coherent
unit for embedding + retrieval.
"""
import re

from app.config import get_settings


def _split_into_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    return re.split(r"(?<=[.!?])\s+", text)


def chunk_text(text: str, chunk_size: int | None = None, overlap: int | None = None) -> list[str]:
    """Greedy sentence-packing chunker: keeps adding sentences to the
    current chunk until it would exceed `chunk_size` characters, then
    starts a new chunk that overlaps the tail of the previous one."""
    settings = get_settings()
    chunk_size = chunk_size or settings.RAG_CHUNK_SIZE
    overlap = overlap or settings.RAG_CHUNK_OVERLAP

    sentences = _split_into_sentences(text)
    if not sentences:
        return []

    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip()
        if len(candidate) <= chunk_size or not current:
            current = candidate
        else:
            chunks.append(current)
            tail = current[-overlap:] if overlap > 0 else ""
            current = f"{tail} {sentence}".strip()
    if current:
        chunks.append(current)

    # Drop trivial fragments (nav labels, single words) that add noise.
    return [c.strip() for c in chunks if len(c.strip()) >= 40]
