from app.schemas import OcrBlock, OcrResult


class OcrService:
    """Week 1 baseline stub for the future PaddleOCR Japanese agent."""

    async def run(self, document_id: str, include_boxes: bool = True) -> OcrResult:
        blocks = [
            OcrBlock(
                text="株式会社ABC",
                confidence=0.94,
                bbox=[48, 80, 220, 112] if include_boxes else [],
                orientation="horizontal",
            ),
            OcrBlock(
                text="請求書番号: INV001",
                confidence=0.91,
                bbox=[48, 122, 260, 154] if include_boxes else [],
                orientation="horizontal",
            ),
        ]
        return OcrResult(
            document_id=document_id,
            text="\n".join(block.text for block in blocks),
            blocks=blocks,
            confidence=0.92,
        )
