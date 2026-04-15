from pathlib import Path

from app.services.json_store import load_json, save_json_atomic

_APP_DIR = Path(__file__).resolve().parent.parent
DATA_VERSION_PATH = _APP_DIR / "data" / "data_version.json"


def get_data_version() -> int:
    if not DATA_VERSION_PATH.exists():
        return 0
    data = load_json(DATA_VERSION_PATH, {"version": 0})
    if not isinstance(data, dict):
        return 0
    try:
        return int(data.get("version", 0))
    except (TypeError, ValueError):
        return 0


def bump_data_version() -> int:
    next_version = get_data_version() + 1
    save_json_atomic(DATA_VERSION_PATH, {"version": next_version})
    return next_version
