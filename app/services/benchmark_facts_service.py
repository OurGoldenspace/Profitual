from pathlib import Path
from typing import Any, Dict, List, Optional

from app.schemas.benchmark_facts import BenchmarkFactRecord
from app.services.json_store import load_json, save_json_atomic

BASE_DIR = Path(__file__).resolve().parent.parent
FACTS_PATH = BASE_DIR / "data" / "benchmark_facts.json"


def load_fact_dicts() -> List[Dict[str, Any]]:
    data = load_json(FACTS_PATH, [])
    if not isinstance(data, list):
        return []
    return data


def load_facts() -> List[BenchmarkFactRecord]:
    out: List[BenchmarkFactRecord] = []
    for row in load_fact_dicts():
        try:
            out.append(BenchmarkFactRecord.model_validate(row))
        except Exception:
            continue
    return out


def save_fact_dicts(rows: List[Dict[str, Any]]) -> None:
    save_json_atomic(FACTS_PATH, rows)


def _specificity_score(fact: BenchmarkFactRecord) -> int:
    score = 0
    if fact.geography is not None:
        score += 2
    if fact.company_stage is not None:
        score += 2
    return score


def resolve_fact_for_request(
    *,
    sector_id: Optional[str],
    industry_code: str,
    metric_code: str,
    geography: str,
    company_stage: str,
) -> Optional[BenchmarkFactRecord]:
    """Pick the most specific matching stored fact, if any."""
    facts = load_facts()
    candidates: List[BenchmarkFactRecord] = []

    for fact in facts:
        if fact.metric_code != metric_code:
            continue

        if sector_id is not None:
            if fact.sector_id != sector_id:
                continue
        else:
            if fact.industry_code != industry_code:
                continue
            if fact.sector_id is not None:
                continue

        if fact.geography is not None and fact.geography != geography:
            continue
        if fact.company_stage is not None and fact.company_stage != company_stage:
            continue

        candidates.append(fact)

    if not candidates:
        return None

    candidates.sort(key=_specificity_score, reverse=True)
    return candidates[0]

