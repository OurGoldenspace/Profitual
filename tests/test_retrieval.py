from app.services.retrieval_service import build_query_terms, score_chunk


def test_build_query_terms():
    terms = build_query_terms(
        industry_name="B2B SaaS",
        industry_description="",
        geography="Canada",
        company_stage="less_than_1M_revenue",
    )
    assert "saas" in terms or "software" in terms


def test_score_chunk():
    chunk = "B2B SaaS companies focus on gross margin, churn rate, and CAC."
    terms = ["saas", "gross", "margin", "inventory"]
    score = score_chunk(chunk, terms)
    assert score > 0


    