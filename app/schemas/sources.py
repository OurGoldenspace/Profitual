from typing import Any, Dict, List

from pydantic import BaseModel, Field


class ChunkListResponse(BaseModel):
    chunks: List[Dict[str, Any]]


class IngestSourcesResponse(BaseModel):
    files_processed: int
    chunks_created: int
    file_names: List[str]
    sectors: List[str] = Field(
        default_factory=list,
        description="source_docs subfolders that had files ingested (e.g. saas, distilleries).",
    )
    data_version: int = Field(description="Bumps when source docs are re-ingested; invalidates benchmark cache keys.")
    chroma_vectors_indexed: int = Field(
        default=0,
        description="Vectors stored in app/data/chroma for semantic retrieval (0 if indexing failed).",
    )


class RetrieveSourcesResponse(BaseModel):
    retrieved_chunks: List[Dict[str, Any]]
    context: str
