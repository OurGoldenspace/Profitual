from app.services.source_sectors import (
    get_source_sector_id,
    list_configured_source_sectors,
)


def test_saas_maps_to_saas_folder():
    assert get_source_sector_id("B2B SaaS") == "saas"
    assert get_source_sector_id("AI SaaS") == "saas"


def test_distilleries_maps_to_distilleries_folder():
    assert get_source_sector_id("Distilleries") == "distilleries"
    assert get_source_sector_id("craft distillery") == "distilleries"


def test_unscoped_industry_returns_none():
    assert get_source_sector_id("Construction") is None


def test_list_configured_source_sectors():
    sectors = list_configured_source_sectors()
    assert "saas" in sectors
    assert "distilleries" in sectors
