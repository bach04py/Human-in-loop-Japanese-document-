from pathlib import Path

from app.core.config import settings
from app.schemas import OcrBlock, OcrResult
from app.services.ocr_helpers import (
    IMAGE_EXTS,
    PDF_EXTS,
    init_ocr,
    run_ocr_on_image,
    run_ocr_on_pdf,
)


class OcrService:
    """OCR service that routes uploaded documents to PaddleOCR processing."""

    def __init__(self) -> None:
        self.ocr = init_ocr()

    async def run(self, document_id: str, include_boxes: bool = True) -> OcrResult:
        file_path = self._find_uploaded_document(document_id)

        if file_path.suffix.lower() in PDF_EXTS:
            raw_result = run_ocr_on_pdf(self.ocr, file_path, include_boxes=include_boxes)
        elif file_path.suffix.lower() in IMAGE_EXTS:
            raw_result = run_ocr_on_image(self.ocr, file_path, include_boxes=include_boxes)
        else:
            raise ValueError(f"Unsupported file type: {file_path.suffix}")

        if raw_result.get("status") != "ocr_completed":
            raise RuntimeError(raw_result.get("error", "OCR processing failed"))

        blocks = [OcrBlock(**block) for block in raw_result["blocks"]]

        return OcrResult(
            document_id=document_id,
            text=raw_result["text"],
            blocks=blocks,
            confidence=raw_result["confidence"],
        )

    def _find_uploaded_document(self, document_id: str) -> Path:
        #upload_dir = settings.upload_dir
        upload_dir = Path("data/samples/ocr")
        if not upload_dir.exists():
            raise FileNotFoundError(f"Upload directory not found: {upload_dir}")

        candidates = list(upload_dir.glob(f"{document_id}.*"))
        if not candidates:
            raise FileNotFoundError(f"Document not found: {document_id}")

        return candidates[0]
