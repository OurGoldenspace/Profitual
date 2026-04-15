from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

_BENCHMARK_STORE = Path(__file__).resolve().parents[1] / "app" / "data" / "benchmark_store.json"


def _clear_benchmark_store() -> None:
    _BENCHMARK_STORE.write_text("[]", encoding="utf-8")


def test_health_ok():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_generate_benchmark_for_saas():
    _clear_benchmark_store()
    payload = {
        "industry_name": "B2B SaaS",
        "geography": "Canada",
        "company_stage": "less_than_1M_revenue",
    }

    response = client.post("/benchmark/generate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["industry_code"] == "b2b_saas"
    assert len(data["metrics"]) > 0
    assert data["geography"] == "canada"
    gm = next(m for m in data["metrics"] if m["metric_code"] == "gross_margin")
    assert "benchmark_facts.json" in gm["sources"][0]["source_name"]


def test_benchmark_facts_endpoint():
    response = client.get("/benchmark/facts")
    assert response.status_code == 200
    facts = response.json()["facts"]
    assert isinstance(facts, list)
    assert any(f.get("id") == "saas_gross_margin_canada_any_stage_2024" for f in facts)


def test_suggest_extract_without_api_key_returns_detail():
    response = client.post(
        "/benchmark/suggest-extract",
        json={
            "industry_name": "B2B SaaS",
            "geography": "Canada",
            "company_stage": "less_than_1M_revenue",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body.get("errors") or body.get("detail")


def test_benchmark_generate_cache_hit():
    payload = {
        "industry_name": "AI SaaS",
        "geography": "Canada",
        "company_stage": "1M_to_5M_revenue",
    }
    first = client.post("/benchmark/generate", json=payload)
    second = client.post("/benchmark/generate", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    notes = second.json()["notes"]
    assert any("loaded from local json storage" in n.lower() for n in notes)


def test_unsupported_industry_returns_422():
    response = client.post(
        "/benchmark/generate",
        json={
            "industry_name": "Unknown Lunar Mining",
            "geography": "Canada",
            "company_stage": "less_than_1M_revenue",
        },
    )
    assert response.status_code == 422


def test_distilleries_sector_metrics():
    _clear_benchmark_store()
    payload = {
        "industry_name": "Distilleries",
        "geography": "Canada",
        "company_stage": "1M_to_5M_revenue",
    }
    response = client.post("/benchmark/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["industry_code"] == "distilleries"
    codes = [m["metric_code"] for m in data["metrics"]]
    assert "inventory_turnover" in codes
    assert "days_inventory_outstanding" in codes
    assert "mrr_growth" not in codes
    gm = next(m for m in data["metrics"] if m["metric_code"] == "gross_margin")
    inv = next(m for m in data["metrics"] if m["metric_code"] == "inventory_turnover")
    assert "benchmark_facts.json" in gm["sources"][0]["source_name"]
    assert "benchmark_facts.json" in inv["sources"][0]["source_name"]


def test_alias_resolution_for_furniture_resale():
    payload = {
        "industry_name": "Furniture Resale",
        "geography": "Canada",
        "company_stage": "1M_to_5M_revenue",
    }

    response = client.post("/benchmark/generate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["industry_code"] == "used_furniture_retail"
    metric_codes = [metric["metric_code"] for metric in data["metrics"]]
    assert "inventory_turnover" in metric_codes
