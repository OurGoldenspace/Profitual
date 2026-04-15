from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.core.data_version import bump_data_version
from app.services.chroma_index import reindex_from_chunk_records
from app.services.json_store import load_json, save_json_atomic

BASE_DIR = Path(__file__).resolve().parent.parent
SOURCE_DOCS_DIR = BASE_DIR / "data" / "source_docs"
CHUNK_STORE_PATH = BASE_DIR / "data" / "chunk_store.json"


def ensure_chunk_store_exists() -> None:
    CHUNK_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not CHUNK_STORE_PATH.exists():
        save_json_atomic(CHUNK_STORE_PATH, [])


def load_chunk_store() -> List[Dict[str, Any]]:
    ensure_chunk_store_exists()
    data = load_json(CHUNK_STORE_PATH, [])
    if not isinstance(data, list):
        return []
    return data


def save_chunk_store(records: List[Dict[str, Any]]) -> None:
    ensure_chunk_store_exists()
    save_json_atomic(CHUNK_STORE_PATH, records)


def _extract_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""

    try:
        reader = PdfReader(str(path))
    except Exception:
        return ""

    parts: List[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            parts.append(text)
    return "\n".join(parts)


def read_document_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix == ".txt":
        return file_path.read_text(encoding="utf-8", errors="replace")
    if suffix == ".pdf":
        return _extract_pdf_text(file_path)
    return ""


def iter_sector_documents() -> List[Tuple[str, Path]]:
    """
    List (sector_id, file_path) for supported source layouts.
    Expected: app/data/source_docs/<sector_id>/*.{txt,pdf}
    """
    if not SOURCE_DOCS_DIR.exists():
        return []

    pairs: List[Tuple[str, Path]] = []
    for sector_dir in sorted(SOURCE_DOCS_DIR.iterdir()):
        if not sector_dir.is_dir():
            continue
        name = sector_dir.name
        if name.startswith(".") or name == "__pycache__":
            continue
        for pattern in ("*.txt", "*.pdf"):
            for file_path in sorted(sector_dir.glob(pattern)):
                if file_path.is_file():
                    pairs.append((name, file_path))

    return pairs


def chunk_text(text: str, max_chunk_size: int = 300) -> List[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []

    chunks = []
    start = 0

    while start < len(cleaned):
        end = start + max_chunk_size
        chunk = cleaned[start:end]

        if end < len(cleaned):
            last_space = chunk.rfind(" ")
            if last_space > 0:
                chunk = chunk[:last_space]
                end = start + last_space

        chunks.append(chunk.strip())
        start = end

    return [chunk for chunk in chunks if chunk]


def build_chunk_records(
    sector_id: str,
    file_name: str,
    text: str,
) -> List[Dict[str, Any]]:
    chunks = chunk_text(text)
    records = []

    for index, chunk in enumerate(chunks):
        records.append(
            {
                "chunk_id": f"{sector_id}/{file_name}::chunk_{index}",
                "sector_id": sector_id,
                "file_name": file_name,
                "chunk_index": index,
                "text": chunk,
            }
        )

    return records


def ingest_source_documents() -> Dict[str, Any]:
    pairs = iter_sector_documents()
    all_records: List[Dict[str, Any]] = []
    sectors_seen: set[str] = set()

    for sector_id, file_path in pairs:
        sectors_seen.add(sector_id)
        text = read_document_text(file_path)
        chunk_records = build_chunk_records(sector_id, file_path.name, text)
        all_records.extend(chunk_records)

    save_chunk_store(all_records)
    new_version = bump_data_version()

    chroma_vectors = 0
    try:
        chroma_vectors = reindex_from_chunk_records(all_records)
    except Exception:
        chroma_vectors = 0

    return {
        "files_processed": len(pairs),
        "chunks_created": len(all_records),
        "file_names": [f"{s}/{p.name}" for s, p in pairs],
        "sectors": sorted(sectors_seen),
        "data_version": new_version,
        "chroma_vectors_indexed": chroma_vectors,
    }


def get_all_chunks() -> List[Dict[str, Any]]:
    return load_chunk_store()
