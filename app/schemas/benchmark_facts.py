from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class BenchmarkFactRecord(BaseModel):
    """One row in app/data/benchmark_facts.json (manual or merged from LLM suggestions)."""

    id: str = Field(description="Stable id, e.g. saas_gm_ca_2024")
    metric_code: str
    benchmark_min: float
    benchmark_max: float
    source_file: str
    citation: str = Field(description="Short verbatim excerpt supporting the band.")
    sector_id: Optional[str] = Field(
        default=None,
        description="Subfolder under source_docs/ (e.g. saas, distilleries).",
    )
    industry_code: Optional[str] = Field(
        default=None,
        description="Use when sector_id is not used (unscoped industries).",
    )
    geography: Optional[str] = Field(
        default=None,
        description="canada / us, or null for any geography.",
    )
    company_stage: Optional[str] = Field(
        default=None,
        description="Canonical stage key, or null for any stage.",
    )
    report_year: Optional[int] = None
    statistic_label: Optional[str] = Field(
        default=None,
        description="e.g. median, interquartile range",
    )
    apply_pipeline_adjustments: bool = Field(
        default=False,
        description="If true, stage/geo heuristics still apply after loading facts.",
    )


class SuggestedExtraction(BaseModel):
    metric_code: str
    benchmark_min: float
    benchmark_max: float
    source_file: str
    citation: str
    validation_warnings: List[str] = Field(default_factory=list)


class SuggestExtractResponse(BaseModel):
    sector_id: Optional[str] = None
    llm_model: Optional[str] = None
    context_used: bool = False
    suggestions: List[SuggestedExtraction] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    detail: Optional[str] = None
