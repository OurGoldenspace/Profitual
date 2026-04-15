import json
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.schemas.benchmark import BenchmarkRequest
from app.schemas.benchmark_facts import SuggestedExtraction, SuggestExtractResponse
from app.services.metric_catalog import METRIC_CATALOG, get_metrics_for_industry
from app.services.retrieval_service import build_retrieval_context, retrieve_relevant_chunks
from app.services.source_sectors import get_source_sector_id


def _allowed_metric_codes_for_industry(industry_name: str) -> List[str]:
    metrics = get_metrics_for_industry(industry_name)
    return [m["metric_code"] for m in metrics]


def validate_numeric_bounds(metric_code: str, lo: float, hi: float) -> List[str]:
    warnings: List[str] = []
    if lo > hi:
        warnings.append("benchmark_min exceeds benchmark_max")

    percentage_like = {
        "gross_margin",
        "net_margin",
        "ebitda_margin",
        "operating_expense_ratio",
        "churn_rate",
        "mrr_growth",
        "utilization_rate",
    }
    if metric_code in percentage_like:
        if lo < -0.2 or hi > 1.2:
            warnings.append("percentage-like value outside typical [-0.2, 1.2]")

    if metric_code in {"inventory_turnover", "current_ratio", "ltv_cac_ratio", "burn_multiple"}:
        if lo < 0 or hi > 500:
            warnings.append("ratio-like value outside [0, 500]")

    if metric_code in {
        "days_inventory_outstanding",
        "cash_conversion_cycle",
        "accounts_receivable_days",
    }:
        if lo < 0 or hi > 2000:
            warnings.append("day-based metric outside [0, 2000]")

    if metric_code in {"customer_acquisition_cost", "revenue_per_employee"}:
        if lo < 0 or hi > 10_000_000:
            warnings.append("currency-like metric outside sane bounds")

    return warnings


def _normalize_llm_item(raw: Dict[str, Any]) -> Tuple[Optional[SuggestedExtraction], List[str]]:
    err_out: List[str] = []
    metric_code = str(raw.get("metric_code", "")).strip()
    if metric_code not in METRIC_CATALOG:
        return None, [f"Unknown metric_code: {metric_code}"]

    try:
        lo = float(raw["benchmark_min"])
        hi = float(raw["benchmark_max"])
    except (KeyError, TypeError, ValueError):
        return None, [f"Invalid min/max for {metric_code}"]

    source_file = str(raw.get("source_file", "unknown")).strip() or "unknown"
    citation = str(raw.get("citation", "")).strip()
    extra: List[str] = []
    if len(citation) < 8:
        extra.append(f"Citation very short for {metric_code}")

    warnings = validate_numeric_bounds(metric_code, lo, hi)
    suggestion = SuggestedExtraction(
        metric_code=metric_code,
        benchmark_min=lo,
        benchmark_max=hi,
        source_file=source_file,
        citation=citation,
        validation_warnings=warnings + extra,
    )
    return suggestion, err_out


def suggest_benchmark_extractions(payload: BenchmarkRequest) -> SuggestExtractResponse:
    if not settings.OPENAI_API_KEY.strip():
        return SuggestExtractResponse(
            detail="Set OPENAI_API_KEY to enable LLM-assisted extraction.",
            errors=["OPENAI_API_KEY is empty"],
        )

    try:
        from openai import OpenAI
    except ImportError:
        return SuggestExtractResponse(
            detail="Install the openai package: pip install openai",
            errors=["openai package not installed"],
        )

    sector_id = get_source_sector_id(payload.industry_name)
    allowed = _allowed_metric_codes_for_industry(payload.industry_name)
    chunks = retrieve_relevant_chunks(
        industry_name=payload.industry_name,
        industry_description=payload.industry_description,
        geography=payload.geography,
        company_stage=payload.company_stage,
        top_k=12,
    )
    context = build_retrieval_context(
        industry_name=payload.industry_name,
        industry_description=payload.industry_description,
        geography=payload.geography,
        company_stage=payload.company_stage,
        top_k=12,
        relevant_chunks=chunks,
    )

    if not context.strip():
        return SuggestExtractResponse(
            sector_id=sector_id,
            context_used=False,
            detail="No retrieved context; ingest PDFs under source_docs/<sector>/ and run POST /sources/ingest.",
            errors=["empty_retrieval_context"],
        )

    metric_lines = "\n".join(
        f"- {code}: {METRIC_CATALOG[code]['metric_name']}" for code in allowed
    )

    user_prompt = f"""You are helping build a structured benchmark table from report excerpts.

Allowed metric_code values (use these exact ids only):
{metric_lines}

Context (excerpts from ingested PDFs):
---
{context[:24000]}
---

Task:
1. For each metric where the context contains explicit numeric guidance (ranges, medians, quartiles), propose benchmark_min and benchmark_max as DECIMALS (e.g. gross margin 75%% -> 0.75).
2. Each proposal MUST include a short VERBATIM citation copied from the context above.
3. If the context does not support a metric, omit it.
4. source_file should be the filename mentioned in the context headers like [Source: filename | Score: ...].

Return JSON only with this shape:
{{"suggestions": [{{"metric_code": "...", "benchmark_min": 0.0, "benchmark_max": 0.0, "source_file": "...", "citation": "..."}}]}}
"""

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    completion = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You output only valid JSON. Never invent numbers not implied by the provided context.",
            },
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )

    raw_text = completion.choices[0].message.content or "{}"
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        return SuggestExtractResponse(
            sector_id=sector_id,
            llm_model=settings.OPENAI_MODEL,
            context_used=True,
            errors=["LLM returned non-JSON"],
            detail=raw_text[:500],
        )

    items = parsed.get("suggestions") if isinstance(parsed, dict) else None
    if not isinstance(items, list):
        return SuggestExtractResponse(
            sector_id=sector_id,
            llm_model=settings.OPENAI_MODEL,
            context_used=True,
            errors=["Missing suggestions array"],
        )

    suggestions: List[SuggestedExtraction] = []
    all_errors: List[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        sug, errs = _normalize_llm_item(item)
        all_errors.extend(errs)
        if sug:
            suggestions.append(sug)

    return SuggestExtractResponse(
        sector_id=sector_id,
        llm_model=settings.OPENAI_MODEL,
        context_used=True,
        suggestions=suggestions,
        errors=all_errors,
    )
