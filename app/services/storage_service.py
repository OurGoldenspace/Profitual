from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.data_version import get_data_version
from app.services.json_store import load_json, save_json_atomic

BASE_DIR = Path(__file__).resolve().parent.parent
STORE_PATH = BASE_DIR / "data" / "benchmark_store.json"


def ensure_store_exists() -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not STORE_PATH.exists():
        save_json_atomic(STORE_PATH, [])


def load_benchmarks() -> List[Dict[str, Any]]:
    ensure_store_exists()
    data = load_json(STORE_PATH, [])
    if not isinstance(data, list):
        return []
    return data


def save_benchmarks(records: List[Dict[str, Any]]) -> None:
    ensure_store_exists()
    save_json_atomic(STORE_PATH, records)


def make_lookup_key(
    industry_code: str,
    geography: str,
    company_stage: str,
) -> str:
    geo = geography.strip().lower()
    stage = company_stage.strip().lower()
    version = get_data_version()
    return f"{industry_code}::{geo}::{stage}::{version}"


def find_benchmark(
    industry_code: str,
    geography: str,
    company_stage: str,
) -> Optional[Dict[str, Any]]:
    records = load_benchmarks()
    lookup_key = make_lookup_key(
        industry_code=industry_code,
        geography=geography,
        company_stage=company_stage,
    )

    for record in records:
        if record.get("lookup_key") == lookup_key:
            return record

    return None


def upsert_benchmark(record: Dict[str, Any]) -> Dict[str, Any]:
    records = load_benchmarks()
    lookup_key = record["lookup_key"]

    updated = False

    for index, existing_record in enumerate(records):
        if existing_record.get("lookup_key") == lookup_key:
            records[index] = record
            updated = True
            break

    if not updated:
        records.append(record)

    save_benchmarks(records)
    return record


def list_saved_benchmarks() -> List[Dict[str, Any]]:
    return load_benchmarks()
