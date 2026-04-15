from datetime import datetime
from typing import Any, List, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.services.metric_catalog import (
    is_supported_industry,
    list_supported_industry_labels,
)


def _normalize_geography_str(value: str) -> str:
    g = value.strip().lower()
    if g in ("canada", "ca"):
        return "canada"
    if g in ("us", "usa", "united states", "united states of america"):
        return "us"
    raise ValueError("Geography must be Canada or US.")


def _normalize_company_stage_str(value: str) -> str:
    s = value.strip().lower()
    allowed = {
        "less_than_1m_revenue",
        "1m_to_5m_revenue",
        "5m_to_20m_revenue",
    }
    if s in allowed:
        return s
    raise ValueError(
        "company_stage must be one of: less_than_1M_revenue, 1M_to_5M_revenue, 5M_to_20M_revenue "
        "(case-insensitive)."
    )


class BenchmarkRequest(BaseModel):
    industry_name: str
    industry_description: str = Field(
        default="",
        description="Optional free text; pipeline uses sector selection when empty.",
    )
    geography: str
    company_stage: str

    @field_validator("industry_name")
    @classmethod
    def strip_industry_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("industry_description")
    @classmethod
    def strip_industry_description(cls, value: str) -> str:
        return value.strip()

    @field_validator("geography")
    @classmethod
    def validate_geography(cls, value: str) -> str:
        return _normalize_geography_str(value)

    @field_validator("company_stage")
    @classmethod
    def validate_company_stage(cls, value: str) -> str:
        return _normalize_company_stage_str(value)

    @model_validator(mode="after")
    def validate_supported_industry(self) -> "BenchmarkRequest":
        if not is_supported_industry(self.industry_name):
            allowed = ", ".join(list_supported_industry_labels())
            raise ValueError(
                f"Unsupported industry. Supported sectors map to: {allowed}."
            )
        return self


class SourceRef(BaseModel):
    source_name: str
    source_type: Literal["report", "dataset", "filing", "web", "manual"]
    quote_or_note: str


class MetricBenchmark(BaseModel):
    metric_name: str
    metric_code: str
    relevance: Literal["high", "medium", "low"]
    benchmark_min: float
    benchmark_max: float
    benchmark_unit: Literal[
        "percentage",
        "ratio",
        "days",
        "months",
        "currency",
        "turns_per_year",
        "multiple",
    ]
    why_it_matters: str
    confidence_score: float = Field(ge=0, le=1)
    sources: List[SourceRef]


class BenchmarkResponse(BaseModel):
    industry_name: str
    industry_code: str
    geography: str
    company_stage: str
    generated_at: datetime
    metrics: List[MetricBenchmark]
    notes: List[str]


class SavedBenchmarksResponse(BaseModel):
    records: List[dict[str, Any]]
