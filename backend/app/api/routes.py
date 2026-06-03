from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.config import settings
from app.schemas import (
    ExtractionRequest,
    ExtractionResult,
    FeedbackRequest,
    FeedbackResponse,
    HealthResponse,
    OcrRequest,
    OcrResult,
    PipelineRunRequest,
    PipelineRunResponse,
    UploadResponse,
    ValidationRequest,
    ValidationResult,
)
from app.services.extraction import ExtractionService
from app.services.memory import CorrectionMemoryService
from app.services.ocr import OcrService
from app.services.orchestrator import OrchestratorService
from app.services.validation import ValidationService

router = APIRouter()

ocr_service = OcrService()
extraction_service = ExtractionService()
validation_service = ValidationService()
memory_service = CorrectionMemoryService()
orchestrator = OrchestratorService(
    ocr_service=ocr_service,
    extraction_service=extraction_service,
    validation_service=validation_service,
)


@router.get("/healthz", response_model=HealthResponse, tags=["system"])
async def healthz() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )


@router.post(
    "/documents",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["documents"],
)
async def upload_document(file: UploadFile = File(...)) -> UploadResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file needs a filename.")

    content = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {settings.max_upload_mb} MB upload limit.",
        )

    document_id = f"doc_{uuid4().hex}"
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename).suffix
    target = settings.upload_dir / f"{document_id}{suffix}"
    target.write_bytes(content)

    return UploadResponse(
        document_id=document_id,
        filename=file.filename,
        content_type=file.content_type,
    )


@router.post("/ocr", response_model=OcrResult, tags=["agents"])
async def run_ocr(request: OcrRequest) -> OcrResult:
    try:
        return await ocr_service.run(
            document_id=request.document_id,
            include_boxes=request.include_boxes,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/extract", response_model=ExtractionResult, tags=["agents"])
async def extract_structured(request: ExtractionRequest) -> ExtractionResult:
    return await extraction_service.extract(
        document_id=request.document_id,
        ocr_text=request.ocr_text,
        document_type=request.document_type,
    )


@router.post("/validate", response_model=ValidationResult, tags=["agents"])
async def validate_extraction(request: ValidationRequest) -> ValidationResult:
    return await validation_service.validate(
        document_id=request.document_id,
        extracted_data=request.extracted_data,
    )


@router.post("/feedback", response_model=FeedbackResponse, tags=["feedback"])
async def submit_feedback(request: FeedbackRequest) -> FeedbackResponse:
    return await memory_service.store_feedback(request)


@router.post("/pipeline/run", response_model=PipelineRunResponse, tags=["workflow"])
async def run_pipeline(request: PipelineRunRequest) -> PipelineRunResponse:
    return await orchestrator.run_pipeline(
        document_id=request.document_id,
        document_type=request.document_type,
    )
