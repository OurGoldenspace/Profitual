from fastapi import APIRouter, Query

from app.schemas.sources import (
    ChunkListResponse,
    IngestSourcesResponse,
    RetrieveSourcesResponse,
)
from app.services.ingestion_service import get_all_chunks, ingest_source_documents
from app.services.retrieval_service import build_retrieval_context, retrieve_relevant_chunks

router = APIRouter(prefix="/sources", tags=["sources"])


@router.post("/ingest", response_model=IngestSourcesResponse)
def ingest_sources() -> IngestSourcesResponse:
    result = ingest_source_documents()
    return IngestSourcesResponse(**result)


@router.get("/chunks", response_model=ChunkListResponse)
def list_chunks() -> ChunkListResponse:
    return ChunkListResponse(chunks=get_all_chunks())


@router.get("/retrieve", response_model=RetrieveSourcesResponse)
def retrieve_sources(
    industry_name: str = Query(...),
    industry_description: str = Query(
        "",
        description="Optional; retrieval uses sector context when omitted.",
    ),
    geography: str = Query(...),
    company_stage: str = Query(...),
    top_k: int = Query(5),
) -> RetrieveSourcesResponse:
    chunks = retrieve_relevant_chunks(
        industry_name=industry_name,
        industry_description=industry_description,
        geography=geography,
        company_stage=company_stage,
        top_k=top_k,
    )

    context = build_retrieval_context(
        industry_name=industry_name,
        industry_description=industry_description,
        geography=geography,
        company_stage=company_stage,
        top_k=top_k,
        relevant_chunks=chunks,
    )

    return RetrieveSourcesResponse(retrieved_chunks=chunks, context=context)
