from app.core.data_version import get_data_version
from app.services.storage_service import (
    ensure_store_exists,
    load_benchmarks,
    make_lookup_key,
)


def test_store_exists():
    ensure_store_exists()
    data = load_benchmarks()
    assert isinstance(data, list)


def test_lookup_key_includes_data_version():
    version = get_data_version()
    key = make_lookup_key(
        industry_code="b2b_saas",
        geography="Canada",
        company_stage="less_than_1M_revenue",
    )
    assert key == f"b2b_saas::canada::less_than_1m_revenue::{version}"
