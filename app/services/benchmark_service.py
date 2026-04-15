from datetime import datetime, timezone
from typing import Dict, List, Tuple

from app.services.benchmark_facts_service import resolve_fact_for_request
from app.services.retrieval_service import (
    retrieve_relevant_chunks,
    retrieval_mode_from_chunks,
)
from app.services.source_sectors import get_source_sector_id

from app.schemas.benchmark import (
    BenchmarkRequest,
    BenchmarkResponse,
    MetricBenchmark,
    SourceRef,
)
from app.services.metric_catalog import (
    get_industry_code,
    get_metrics_for_industry,
    get_resolved_industry_name,
)
from app.services.storage_service import find_benchmark, make_lookup_key, upsert_benchmark

DEFAULT_BENCHMARKS = {
    "gross_margin": (0.45, 0.55, "high"),
    "net_margin": (0.08, 0.15, "medium"),
    "ebitda_margin": (0.10, 0.20, "medium"),
    "current_ratio": (1.2, 2.0, "medium"),
    "operating_expense_ratio": (0.20, 0.35, "medium"),
    "inventory_turnover": (4.0, 6.0, "high"),
    "days_inventory_outstanding": (45.0, 90.0, "high"),
    "cash_conversion_cycle": (20.0, 60.0, "medium"),
    "churn_rate": (0.03, 0.08, "high"),
    "customer_acquisition_cost": (500.0, 3000.0, "medium"),
    "ltv_cac_ratio": (3.0, 5.0, "high"),
    "mrr_growth": (0.05, 0.15, "high"),
    "burn_multiple": (1.0, 2.0, "medium"),
    "utilization_rate": (0.65, 0.85, "high"),
    "revenue_per_employee": (120000.0, 250000.0, "medium"),
    "accounts_receivable_days": (30.0, 60.0, "medium"),
}

# Illustrative ranges per resolved industry; extend as you add sectors / extract from reports.
SECTOR_BENCHMARK_OVERRIDES: Dict[str, Dict[str, Tuple[float, float, str]]] = {
    "distilleries": {
        "gross_margin": (0.42, 0.58, "high"),
        "net_margin": (0.06, 0.16, "medium"),
        "ebitda_margin": (0.14, 0.26, "medium"),
        "inventory_turnover": (1.2, 2.8, "high"),
        "days_inventory_outstanding": (120.0, 280.0, "high"),
        "cash_conversion_cycle": (60.0, 180.0, "medium"),
        "current_ratio": (1.3, 2.2, "medium"),
        "operating_expense_ratio": (0.22, 0.38, "medium"),
    },
}


def get_benchmark_triplet(metric_code: str, resolved_industry: str) -> Tuple[float, float, str]:
    sector_table = SECTOR_BENCHMARK_OVERRIDES.get(resolved_industry)
    if sector_table and metric_code in sector_table:
        return sector_table[metric_code]
    return DEFAULT_BENCHMARKS.get(metric_code, (0.0, 0.0, "medium"))


def adjust_for_stage(
    metric_code: str,
    benchmark_min: float,
    benchmark_max: float,
    company_stage: str,
    resolved_industry: str,
) -> Tuple[float, float]:
    stage = company_stage.strip().lower()

    if stage == "less_than_1m_revenue":
        if metric_code == "mrr_growth":
            return benchmark_min + 0.02, benchmark_max + 0.05
        if metric_code == "burn_multiple":
            return benchmark_min + 0.3, benchmark_max + 0.7
        if metric_code == "customer_acquisition_cost":
            return benchmark_min * 0.8, benchmark_max * 0.9
        if metric_code == "net_margin":
            return max(0.0, benchmark_min - 0.05), max(0.02, benchmark_max - 0.04)
        if metric_code == "ebitda_margin":
            return max(0.0, benchmark_min - 0.05), max(0.05, benchmark_max - 0.05)

    if stage == "1m_to_5m_revenue":
        return benchmark_min, benchmark_max

    if stage == "5m_to_20m_revenue":
        if metric_code == "gross_margin":
            return benchmark_min + 0.02, benchmark_max + 0.03
        if metric_code == "net_margin":
            return benchmark_min + 0.02, benchmark_max + 0.03
        if metric_code == "ebitda_margin":
            return benchmark_min + 0.02, benchmark_max + 0.03
        if metric_code == "burn_multiple":
            return max(0.8, benchmark_min - 0.2), max(1.5, benchmark_max - 0.3)
        if metric_code == "accounts_receivable_days":
            return max(20.0, benchmark_min - 5), max(50.0, benchmark_max - 5)

    return benchmark_min, benchmark_max

def adjust_for_geography(
    metric_code: str,
    benchmark_min: float,
    benchmark_max: float,
    geography: str,
) -> Tuple[float, float]:
    geo = geography.strip().lower()

    if geo == "canada":
        if metric_code == "customer_acquisition_cost":
            return benchmark_min * 0.95, benchmark_max * 1.05
        if metric_code == "revenue_per_employee":
            return benchmark_min * 0.9, benchmark_max * 0.95
        if metric_code == "accounts_receivable_days":
            return benchmark_min + 2, benchmark_max + 3

    if geo == "us":
        if metric_code == "customer_acquisition_cost":
            return benchmark_min * 1.05, benchmark_max * 1.15
        if metric_code == "revenue_per_employee":
            return benchmark_min * 1.05, benchmark_max * 1.15

    return benchmark_min, benchmark_max

def round_benchmark(metric_code: str, benchmark_min: float, benchmark_max: float) -> Tuple[float, float]:
    percentage_metrics = {
        "gross_margin",
        "net_margin",
        "ebitda_margin",
        "operating_expense_ratio",
        "churn_rate",
        "mrr_growth",
        "utilization_rate",
    }

    if metric_code in percentage_metrics:
        return round(benchmark_min, 2), round(benchmark_max, 2)

    if metric_code in {"current_ratio", "ltv_cac_ratio", "burn_multiple", "inventory_turnover"}:
        return round(benchmark_min, 2), round(benchmark_max, 2)

    return round(benchmark_min, 0), round(benchmark_max, 0)


def build_pipeline_notes(
    input_industry: str,
    resolved_industry: str,
    geography: str,
    company_stage: str,
    cache_hit: bool,
    retrieved_chunk_count: int,
    citation_backed: int = 0,
    heuristic_backed: int = 0,
    retrieval_mode: str = "none",
) -> list[str]:
    notes = [
        "Pipeline: industry mapping, optional stage/geo adjustments, sector-scoped retrieval, local JSON cache.",
        f"Resolved industry: {resolved_industry}",
        f"Geography: {geography}",
        f"Stage: {company_stage}",
        f"Retrieved source chunks: {retrieved_chunk_count}",
        (
            f"benchmark_facts.json: {citation_backed} metrics use stored citation-backed bands; "
            f"{heuristic_backed} metrics use heuristic demo rules."
        ),
    ]

    if retrieval_mode == "semantic":
        notes.append(
            "Retrieval mode: Chroma semantic search (vectors in app/data/chroma; re-run POST /sources/ingest after PDF changes).",
        )
    elif retrieval_mode == "lexical":
        notes.append(
            "Retrieval mode: lexical keyword overlap (used when the Chroma index is empty or semantic query returned no results).",
        )
    else:
        notes.append("Retrieval mode: no chunks retrieved for this query.")

    sector_folder = get_source_sector_id(input_industry)
    if sector_folder:
        notes.append(
            f"Retrieval uses only ingested documents under source_docs/{sector_folder}/.",
        )

    if input_industry.strip().lower() != resolved_industry:
        notes.append(
            f"Input industry '{input_industry}' was normalized to '{resolved_industry}'."
        )

    if cache_hit:
        notes.append("Result was loaded from local JSON storage.")
    else:
        notes.append("Result was newly generated and saved to local JSON storage.")

    notes.append(
        "Optional: POST /benchmark/suggest-extract (OPENAI_API_KEY) to draft rows; merge into app/data/benchmark_facts.json after review.",
    )

    return notes


def _count_metric_sources(metrics: List[MetricBenchmark]) -> Tuple[int, int]:
    citation = 0
    heuristic = 0
    for metric in metrics:
        if not metric.sources:
            heuristic += 1
            continue
        if "benchmark_facts.json" in metric.sources[0].source_name:
            citation += 1
        else:
            heuristic += 1
    return citation, heuristic



def response_to_record(
    response: BenchmarkResponse,
    lookup_key: str,
) -> dict:
    return {
        "lookup_key": lookup_key,
        "industry_name": response.industry_name,
        "industry_code": response.industry_code,
        "geography": response.geography,
        "company_stage": response.company_stage,
        "generated_at": response.generated_at.isoformat(),
        "metrics": [metric.model_dump() for metric in response.metrics],
        "notes": response.notes,
    }


def record_to_response(record: dict) -> BenchmarkResponse:
    return BenchmarkResponse(
        industry_name=record["industry_name"],
        industry_code=record["industry_code"],
        geography=record["geography"],
        company_stage=record["company_stage"],
        generated_at=datetime.fromisoformat(record["generated_at"]),
        metrics=[MetricBenchmark(**metric) for metric in record["metrics"]],
        notes=record["notes"],
    )


def generate_new_benchmark_response(payload: BenchmarkRequest) -> BenchmarkResponse:
    resolved_industry = get_resolved_industry_name(payload.industry_name)
    industry_code = get_industry_code(payload.industry_name)
    sector_id = get_source_sector_id(payload.industry_name)
    selected_metrics = get_metrics_for_industry(payload.industry_name)

    retrieved_chunks = retrieve_relevant_chunks(
        industry_name=payload.industry_name,
        industry_description=payload.industry_description,
        geography=payload.geography,
        company_stage=payload.company_stage,
        top_k=5,
    )

    metric_benchmarks: List[MetricBenchmark] = []
    citation_backed = 0
    heuristic_backed = 0

    for metric in selected_metrics:
        metric_code = metric["metric_code"]
        stored = resolve_fact_for_request(
            sector_id=sector_id,
            industry_code=industry_code,
            metric_code=metric_code,
            geography=payload.geography,
            company_stage=payload.company_stage,
        )

        if stored:
            citation_backed += 1
            benchmark_min = stored.benchmark_min
            benchmark_max = stored.benchmark_max
            relevance = get_benchmark_triplet(metric_code, resolved_industry)[2]
            if stored.apply_pipeline_adjustments:
                benchmark_min, benchmark_max = adjust_for_stage(
                    metric_code=metric_code,
                    benchmark_min=benchmark_min,
                    benchmark_max=benchmark_max,
                    company_stage=payload.company_stage,
                    resolved_industry=resolved_industry,
                )
                benchmark_min, benchmark_max = adjust_for_geography(
                    metric_code=metric_code,
                    benchmark_min=benchmark_min,
                    benchmark_max=benchmark_max,
                    geography=payload.geography,
                )
            benchmark_min, benchmark_max = round_benchmark(
                metric_code=metric_code,
                benchmark_min=benchmark_min,
                benchmark_max=benchmark_max,
            )
            label = stored.statistic_label or "reported range"
            quote = f"[{label}] {stored.citation}"
            sources = [
                SourceRef(
                    source_name=f"{stored.source_file} (benchmark_facts.json)",
                    source_type="report",
                    quote_or_note=quote[:2000],
                )
            ]
            confidence = 0.88
        else:
            heuristic_backed += 1
            benchmark_min, benchmark_max, relevance = get_benchmark_triplet(
                metric_code,
                resolved_industry,
            )

            benchmark_min, benchmark_max = adjust_for_stage(
                metric_code=metric_code,
                benchmark_min=benchmark_min,
                benchmark_max=benchmark_max,
                company_stage=payload.company_stage,
                resolved_industry=resolved_industry,
            )

            benchmark_min, benchmark_max = adjust_for_geography(
                metric_code=metric_code,
                benchmark_min=benchmark_min,
                benchmark_max=benchmark_max,
                geography=payload.geography,
            )

            benchmark_min, benchmark_max = round_benchmark(
                metric_code=metric_code,
                benchmark_min=benchmark_min,
                benchmark_max=benchmark_max,
            )
            sources = [
                SourceRef(
                    source_name="Demo Rules Engine",
                    source_type="manual",
                    quote_or_note="Heuristic demo band; replace by adding a row to benchmark_facts.json or running suggest-extract.",
                )
            ]
            confidence = 0.70

        metric_benchmarks.append(
            MetricBenchmark(
                metric_name=metric["metric_name"],
                metric_code=metric_code,
                relevance=relevance,
                benchmark_min=benchmark_min,
                benchmark_max=benchmark_max,
                benchmark_unit=metric["benchmark_unit"],
                why_it_matters=metric["why_it_matters"],
                confidence_score=confidence,
                sources=sources,
            )
        )

    rmode = retrieval_mode_from_chunks(retrieved_chunks)

    return BenchmarkResponse(
        industry_name=payload.industry_name,
        industry_code=industry_code,
        geography=payload.geography,
        company_stage=payload.company_stage,
        generated_at=datetime.now(timezone.utc),
        metrics=metric_benchmarks,
        notes=build_pipeline_notes(
            input_industry=payload.industry_name,
            resolved_industry=resolved_industry,
            geography=payload.geography,
            company_stage=payload.company_stage,
            cache_hit=False,
            retrieved_chunk_count=len(retrieved_chunks),
            citation_backed=citation_backed,
            heuristic_backed=heuristic_backed,
            retrieval_mode=rmode,
        ),
    )
        


def build_benchmark_response(payload: BenchmarkRequest) -> BenchmarkResponse:
    industry_code = get_industry_code(payload.industry_name)
    lookup_key = make_lookup_key(
        industry_code=industry_code,
        geography=payload.geography,
        company_stage=payload.company_stage,
    )

    saved_record = find_benchmark(
        industry_code=industry_code,
        geography=payload.geography,
        company_stage=payload.company_stage,
    )

    if saved_record:
        response = record_to_response(saved_record)
        resolved_industry = get_resolved_industry_name(payload.industry_name)
        retrieved_chunks = retrieve_relevant_chunks(
            industry_name=payload.industry_name,
            industry_description=payload.industry_description,
            geography=payload.geography,
            company_stage=payload.company_stage,
            top_k=5,
        )
        cit, heu = _count_metric_sources(response.metrics)
        rmode = retrieval_mode_from_chunks(retrieved_chunks)
        response.notes = build_pipeline_notes(
            input_industry=payload.industry_name,
            resolved_industry=resolved_industry,
            geography=payload.geography,
            company_stage=payload.company_stage,
            cache_hit=True,
            retrieved_chunk_count=len(retrieved_chunks),
            citation_backed=cit,
            heuristic_backed=heu,
            retrieval_mode=rmode,
        )
        return response

    response = generate_new_benchmark_response(payload)
    record = response_to_record(response=response, lookup_key=lookup_key)
    upsert_benchmark(record)
    return response


