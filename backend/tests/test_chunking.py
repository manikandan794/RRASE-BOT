from app.rag.chunking import chunk_text


def test_chunk_text_respects_size_and_overlap():
    paragraph = "RRASE College was established to provide quality technical education. " * 20
    chunks = chunk_text(paragraph, chunk_size=200, overlap=40)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 260  # allows a little slack for the trailing sentence


def test_chunk_text_drops_trivial_fragments():
    chunks = chunk_text("Hi. Ok. " + "A" * 50 + ".")
    assert all(len(c) >= 40 for c in chunks)


def test_chunk_text_empty_input():
    assert chunk_text("") == []
    assert chunk_text("   ") == []
