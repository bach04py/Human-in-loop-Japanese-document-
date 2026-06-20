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
FEEDBACK_DIR = settings.upload_dir.parent / "feedback"


def _document_path(document_id: str) -> Path:
    return EXTRACTED_DIR / f"{document_id}.json"


def _feedback_path(document_id: str) -> Path:
    return FEEDBACK_DIR / f"{document_id}.json"


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


# ---------------------------------------------------------------------------
# Human feedback / corrections
# ---------------------------------------------------------------------------
def append_feedback(document_id: str, record: dict[str, Any]) -> int:
    """Append one correction event to the document's durable feedback log.

    Returns the new revision number (1-based count of recorded corrections).
    """
    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
    path = _feedback_path(document_id)
    history: list[dict[str, Any]] = []
    if path.exists():
        try:
            history = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            history = []
    revision = len(history) + 1
    entry = {"revision": revision, "recorded_at": datetime.now(timezone.utc).isoformat(), **record}
    history.append(entry)
    path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    return revision


def load_feedback(document_id: str) -> list[dict[str, Any]]:
    """Return the full correction history for a document (oldest first)."""
    path = _feedback_path(document_id)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def apply_correction(
    document_id: str,
    corrections: dict[str, Any] | None = None,
    ocr_text: str | None = None,
    user: str | None = None,
    revision: int = 0,
) -> bool:
    """Update the stored extracted document with a validator's corrections.

    Makes the human-approved values the source of truth that the chatbot and
    future reads use. Keeps the pre-correction snapshot for audit. Returns
    ``True`` if a stored document existed and was updated.
    """
    document = load_document(document_id)
    if document is None:
        return False

    # Preserve the machine output once, on the first human correction.
    if not document.get("human_reviewed"):
        document["data_original"] = document.get("data")
        document["ocr_text_original"] = document.get("ocr_text")

    if corrections:
        document["data"] = corrections
    if ocr_text is not None:
        document["ocr_text"] = ocr_text

    document["human_reviewed"] = True
    document["reviewed_by"] = user
    document["reviewed_at"] = datetime.now(timezone.utc).isoformat()
    document["revision"] = revision

    save_document(document_id, document)
    return True
