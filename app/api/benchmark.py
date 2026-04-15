from fastapi import APIRouter

from app.schemas.benchmark import BenchmarkRequest, BenchmarkResponse, SavedBenchmarksResponse
from app.schemas.benchmark_facts import SuggestExtractResponse
from app.services.benchmark_facts_service import load_fact_dicts
from app.services.benchmark_service import build_benchmark_response
from app.services.llm_extraction_service import suggest_benchmark_extractions
from app.services.storage_service import list_saved_benchmarks

router = APIRouter(prefix="/benchmark", tags=["benchmark"])


@router.post("/generate", response_model=BenchmarkResponse)
def generate_benchmark(payload: BenchmarkRequest) -> BenchmarkResponse:
    return build_benchmark_response(payload)


@router.get("/saved", response_model=SavedBenchmarksResponse)
def get_saved_benchmarks() -> SavedBenchmarksResponse:
    return SavedBenchmarksResponse(records=list_saved_benchmarks())


@router.get("/facts")
def list_stored_benchmark_facts() -> dict:
    """Read-only view of app/data/benchmark_facts.json for review and copy-paste workflows."""
    return {"facts": load_fact_dicts()}


@router.post("/suggest-extract", response_model=SuggestExtractResponse)
def suggest_extract(payload: BenchmarkRequest) -> SuggestExtractResponse:
    """Optional LLM assist: proposes rows with citations; merge into benchmark_facts.json after validation."""
    return suggest_benchmark_extractions(payload)
