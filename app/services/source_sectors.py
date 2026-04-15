"""Maps catalog industries to subfolders under app/data/source_docs/<sector_id>/."""

from typing import Dict, Optional

from app.services.metric_catalog import resolve_industry_name

# Folder names under source_docs/ — add a key here when you add a new sector + reports.
SOURCE_SECTOR_BY_RESOLVED_INDUSTRY: Dict[str, str] = {
    "b2b saas": "saas",
    "ai saas": "saas",
    "distilleries": "distilleries",
}


def get_source_sector_id(industry_name: str) -> Optional[str]:
    """Returns the source_docs subfolder for this industry, or None if retrieval is not scoped."""
    resolved = resolve_industry_name(industry_name)
    return SOURCE_SECTOR_BY_RESOLVED_INDUSTRY.get(resolved)


def list_configured_source_sectors() -> list[str]:
    return sorted(set(SOURCE_SECTOR_BY_RESOLVED_INDUSTRY.values()))
