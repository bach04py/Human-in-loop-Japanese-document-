from app.schemas import PipelineRunResponse
from app.services.extraction import ExtractionService
from app.services.ocr import OcrService
from app.services.validation import ValidationService


class OrchestratorService:
    """Coordinates the baseline OCR -> extraction -> validation workflow."""

    def __init__(
        self,
        ocr_service: OcrService,
        extraction_service: ExtractionService,
        validation_service: ValidationService,
    ) -> None:
        self.ocr_service = ocr_service
        self.extraction_service = extraction_service
        self.validation_service = validation_service

    async def run_pipeline(
            self, document_id: str, document_type: str = "unknown"
    ) -> PipelineRunResponse:
        ocr = await self.ocr_service.run(document_id=document_id)
        extraction = await self.extraction_service.extract(
            document_id=document_id,
            ocr_text=ocr.text,
            layout_blocks=ocr.blocks,
            document_type=document_type,
        )
        validation = await self.validation_service.validate(
            document_id=document_id,
            extracted_data=extraction.data,
        )
        return PipelineRunResponse(
            document_id=document_id,
            ocr=ocr,
            extraction=extraction,
            validation=validation,
        )
