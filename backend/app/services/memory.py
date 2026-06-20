"""Correction memory: durably records validator feedback and applies it.

When a human validator corrects the OCR text or the extracted fields, the
feedback is (1) appended to a per-document audit log on disk and (2) applied to
the stored extracted document so the chatbot and any later reads use the
human-approved version instead of the original machine output.
"""

import logging

from app.schemas import FeedbackRequest, FeedbackResponse
from app.services import document_store

logger = logging.getLogger(__name__)


class CorrectionMemoryService:
    """Persists human corrections and feeds them back into the stored document."""

    async def store_feedback(self, feedback: FeedbackRequest) -> FeedbackResponse:
        record = {
            "user": feedback.user,
            "notes": feedback.notes,
            "document_type": feedback.document_type,
            "corrections": feedback.corrections,
            "ocr_text_corrected": feedback.ocr_text is not None,
            "ocr_text": feedback.ocr_text,
        }
        revision = document_store.append_feedback(feedback.document_id, record)

        applied = document_store.apply_correction(
            document_id=feedback.document_id,
            corrections=feedback.corrections,
            ocr_text=feedback.ocr_text,
            user=feedback.user,
            revision=revision,
        )
        if not applied:
            logger.warning(
                "Feedback recorded for %s but no stored document to update "
                "(run the pipeline first).",
                feedback.document_id,
            )

        return FeedbackResponse(
            document_id=feedback.document_id,
            stored=True,
            applied=applied,
            revision=revision,
        )
