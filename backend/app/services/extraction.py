from app.schemas import ExtractionResult


class ExtractionService:
    """Week 1 baseline stub for LayoutLM/LLM structured extraction."""

    async def extract(
        self,
        document_id: str,
        ocr_text: str | None = None,
        document_type: str = "unknown",
    ) -> ExtractionResult:
        return ExtractionResult(
            document_id=document_id,
            data={
                "document_type": document_type,
                "invoice_id": "INV001",
                "company": "株式会社ABC",
                "amount": 120000,
                "currency": "JPY",
                "source_text": ocr_text,
            },
            confidence=0.88,
        )
