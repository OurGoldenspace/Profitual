import re
from typing import Any, Dict, List, Optional

from app.services.chroma_index import semantic_query_chunks
from app.services.ingestion_service import get_all_chunks
from app.services.metric_catalog import get_resolved_industry_name
from app.services.source_sectors import get_source_sector_id

STOP_WORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "are",
    "is",
    "to",
    "of",
    "in",
    "a",
    "an",
    "on",
    "by",
    "as",
    "it",
    "be",
}


def tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[a-zA-Z0-9_]+", text.lower())
    return [token for token in tokens if token not in STOP_WORDS and len(token) > 1]


def build_semantic_query_text(
    industry_name: str,
    industry_description: str,
    geography: str,
    company_stage: str,
) -> str:
    resolved_industry = get_resolved_industry_name(industry_name)
    return " ".join(
        [
            industry_name,
            resolved_industry,
            industry_description,
            geography,
            company_stage,
        ]
    ).strip()


def build_query_terms(
    industry_name: str,
    industry_description: str,
    geography: str,
    company_stage: str,
) -> List[str]:
    combined_text = build_semantic_query_text(
        industry_name=industry_name,
        industry_description=industry_description,
        geography=geography,
        company_stage=company_stage,
    )
    return tokenize(combined_text)


def score_chunk(chunk_text: str, query_terms: List[str]) -> int:
    chunk_tokens = tokenize(chunk_text)
    chunk_token_set = set(chunk_tokens)

    score = 0
    for term in query_terms:
        if term in chunk_token_set:
            score += 1

    return score


def retrieve_relevant_chunks(
    industry_name: str,
    industry_description: str,
    geography: str,
    company_stage: str,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    sector_id = get_source_sector_id(industry_name)
    query_text = build_semantic_query_text(
        industry_name=industry_name,
        industry_description=industry_description,
        geography=geography,
        company_stage=company_stage,
    )

    # Chroma chunks are only tagged with sector_id; without it, semantic search could mix sectors — use lexical only.
    semantic: List[Dict[str, Any]] = []
    if sector_id is not None:
        semantic = semantic_query_chunks(
            query_text=query_text,
            sector_id=sector_id,
            top_k=top_k,
        )
    if semantic:
        return semantic

    chunks = get_all_chunks()
    if sector_id is not None:
        chunks = [chunk for chunk in chunks if chunk.get("sector_id") == sector_id]

    query_terms = build_query_terms(
        industry_name=industry_name,
        industry_description=industry_description,
        geography=geography,
        company_stage=company_stage,
    )

    scored_chunks = []
    for chunk in chunks:
        score = score_chunk(chunk["text"], query_terms)
        if score > 0:
            scored_chunks.append(
                {
                    "chunk_id": chunk["chunk_id"],
                    "file_name": chunk["file_name"],
                    "chunk_index": chunk["chunk_index"],
                    "text": chunk["text"],
                    "score": score,
                    "retrieval": "lexical",
                }
            )

    scored_chunks.sort(key=lambda item: item["score"], reverse=True)
    return scored_chunks[:top_k]


def _format_context_lines(relevant_chunks: List[Dict[str, Any]]) -> str:
    if not relevant_chunks:
        return ""

    context_parts = []
    for chunk in relevant_chunks:
        mode = chunk.get("retrieval", "lexical")
        label = "Semantic" if mode == "semantic" else "Lexical"
        context_parts.append(
            f"[{label} | Source: {chunk['file_name']} | Score: {chunk['score']}] {chunk['text']}"
        )

    return "\n\n".join(context_parts)


def build_retrieval_context(
    industry_name: str,
    industry_description: str,
    geography: str,
    company_stage: str,
    top_k: int = 5,
    relevant_chunks: Optional[List[Dict[str, Any]]] = None,
) -> str:
    if relevant_chunks is None:
        relevant_chunks = retrieve_relevant_chunks(
            industry_name=industry_name,
            industry_description=industry_description,
            geography=geography,
            company_stage=company_stage,
            top_k=top_k,
        )
    else:
        relevant_chunks = relevant_chunks[:top_k]

    return _format_context_lines(relevant_chunks)


def retrieval_mode_from_chunks(chunks: List[Dict[str, Any]]) -> str:
    if not chunks:
        return "none"
    if chunks[0].get("retrieval") == "semantic":
        return "semantic"
    return "lexical"
