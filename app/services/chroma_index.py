"""
Semantic index over ingested chunks (Chroma persistent store under app/data/chroma/).

Uses OpenAI embeddings when OPENAI_API_KEY is set; otherwise Chroma's default local embedding model.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings

BASE_DIR = Path(__file__).resolve().parent.parent
CHROMA_DIR = BASE_DIR / "data" / "chroma"
COLLECTION_NAME = "source_chunks"


def _client():
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def _embedding_function():
    if not settings.OPENAI_API_KEY.strip():
        return None
    try:
        from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
    except ImportError:
        return None
    return OpenAIEmbeddingFunction(
        api_key=settings.OPENAI_API_KEY,
        model_name=settings.OPENAI_EMBEDDING_MODEL,
    )


def reindex_from_chunk_records(records: List[Dict[str, Any]]) -> int:
    """Replace the collection with the given chunk records. Returns number of vectors indexed."""
    client = _client()
    try:
        client.delete_collection(COLLECTION_NAME)
    except (ValueError, Exception):
        pass

    ef = _embedding_function()
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
        embedding_function=ef,
    )

    if not records:
        return 0

    ids = [str(r["chunk_id"]) for r in records]
    documents = [str(r["text"]) for r in records]
    metadatas: List[Dict[str, Any]] = []
    for r in records:
        metadatas.append(
            {
                "sector_id": str(r.get("sector_id", "")),
                "file_name": str(r.get("file_name", "")),
                "chunk_index": int(r.get("chunk_index", 0)),
            }
        )

    batch_size = 128
    for start in range(0, len(ids), batch_size):
        end = start + batch_size
        collection.add(
            ids=ids[start:end],
            documents=documents[start:end],
            metadatas=metadatas[start:end],
        )

    return len(ids)


def semantic_query_chunks(
    *,
    query_text: str,
    sector_id: Optional[str],
    top_k: int,
) -> List[Dict[str, Any]]:
    """
    Return chunks ranked by semantic similarity.
    Each item: chunk_id, file_name, chunk_index, text, score (higher is better), retrieval=semantic.
    """
    client = _client()

    try:
        collection = client.get_collection(COLLECTION_NAME)
    except Exception:
        return []

    where: Optional[Dict[str, Any]] = None
    if sector_id is not None:
        where = {"sector_id": sector_id}

    try:
        result = collection.query(
            query_texts=[query_text],
            n_results=max(1, top_k),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
    except Exception:
        return []

    ids_batch = result.get("ids") or []
    docs_batch = result.get("documents") or []
    meta_batch = result.get("metadatas") or []
    dist_batch = result.get("distances") or []

    if not ids_batch or not ids_batch[0]:
        return []

    out: List[Dict[str, Any]] = []
    for chunk_id, text, meta, dist in zip(
        ids_batch[0],
        docs_batch[0],
        meta_batch[0],
        dist_batch[0],
    ):
        try:
            d = float(dist)
        except (TypeError, ValueError):
            d = 0.0
        score = max(0.0, 1.0 - min(d, 2.0) / 2.0)

        out.append(
            {
                "chunk_id": chunk_id,
                "file_name": meta.get("file_name", "") if meta else "",
                "chunk_index": int(meta.get("chunk_index", 0)) if meta else 0,
                "text": text or "",
                "score": round(score, 4),
                "retrieval": "semantic",
            }
        )

    return out[:top_k]


def collection_count() -> int:
    try:
        client = _client()
        coll = client.get_collection(COLLECTION_NAME)
        return int(coll.count())
    except Exception:
        return 0
