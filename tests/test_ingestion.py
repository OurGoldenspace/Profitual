from app.services.ingestion_service import chunk_text


def test_chunk_text():
    text = "This is a test document for chunking. " * 20
    chunks = chunk_text(text, max_chunk_size=100)

    assert len(chunks) > 1
    assert all(isinstance(chunk, str) for chunk in chunks)
    assert all(len(chunk) > 0 for chunk in chunks)