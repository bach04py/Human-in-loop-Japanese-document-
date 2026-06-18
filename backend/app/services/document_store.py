"""Persists extracted documents as JSON files that the chatbot reads as context.

Files are stored next to the upload directory (``data/extracted``) so the path
resolves the same way ``settings.upload_dir`` does, regardless of the current
working directory.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings

EXTRACTED_DIR = settings.upload_dir.parent / "extracted"


def _document_path(document_id: str) -> Path:
    return EXTRACTED_DIR / f"{document_id}.json"


def save_document(document_id: str, payload: dict[str, Any]) -> Path:
    """Write a document's extracted data to ``<document_id>.json``."""
    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
    record = {**payload, "saved_at": datetime.now(timezone.utc).isoformat()}
    path = _document_path(document_id)
    path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return path


def load_document(document_id: str) -> dict[str, Any] | None:
    """Read a single stored document, or ``None`` if it has not been extracted."""
    path = _document_path(document_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def list_documents() -> list[dict[str, Any]]:
    """Return every stored document, newest first."""
    if not EXTRACTED_DIR.exists():
        return []
    documents: list[dict[str, Any]] = []
    for path in EXTRACTED_DIR.glob("*.json"):
        try:
            documents.append(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    documents.sort(key=lambda doc: doc.get("saved_at") or "", reverse=True)
    return documents
