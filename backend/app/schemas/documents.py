from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str
    environment: str


class DocumentStatus(str, Enum):
    uploaded = "uploaded"
    ocr_completed = "ocr_completed"
    extracted = "extracted"
    validated = "validated"
    feedback_received = "feedback_received"


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    content_type: str | None = None
    status: DocumentStatus = DocumentStatus.uploaded


class DocumentSummary(BaseModel):
    document_id: str
    filename: str
    content_type: str | None = None
    uploaded_at: str
    document_type: Literal["invoice", "contract", "form", "unknown"] = "unknown"
    status: DocumentStatus = DocumentStatus.uploaded


class OcrRequest(BaseModel):
    document_id: str = Field(..., examples=["doc_invoice_001"])
    language: str = Field(default="ja", examples=["ja"])
    include_boxes: bool = True


class OcrBlock(BaseModel):
    text: str
    confidence: float = Field(ge=0, le=1)
    bbox: list[float] = Field(
        default_factory=list,
        description="Bounding box as [x1, y1, x2, y2] in page coordinates.",
    )
    page: int = Field(default=1, ge=1)
    orientation: Literal["horizontal", "vertical", "unknown"] = "unknown"


class OcrResult(BaseModel):
    document_id: str
    text: str
    blocks: list[OcrBlock]
    confidence: float = Field(ge=0, le=1)
    status: DocumentStatus = DocumentStatus.ocr_completed


class ExtractionRequest(BaseModel):
    document_id: str
    ocr_text: str | None = None
    document_type: Literal["invoice", "contract", "form", "unknown"] = "unknown"


class ExtractionResult(BaseModel):
    document_id: str
    data: dict[str, Any]
    confidence: float = Field(ge=0, le=1)
    status: DocumentStatus = DocumentStatus.extracted


class ValidationRequest(BaseModel):
    document_id: str
    extracted_data: dict[str, Any] | None = None


class ValidationIssue(BaseModel):
    field: str
    message: str
    severity: Literal["info", "warning", "error"] = "warning"


class ValidationResult(BaseModel):
    document_id: str
    valid: bool
    confidence: float = Field(ge=0, le=1)
    issues: list[ValidationIssue] = Field(default_factory=list)
    status: DocumentStatus = DocumentStatus.validated


class FeedbackRequest(BaseModel):
    document_id: str
    corrections: dict[str, Any]
    user: str | None = None
    notes: str | None = None


class FeedbackResponse(BaseModel):
    document_id: str
    stored: bool
    status: DocumentStatus = DocumentStatus.feedback_received


class PipelineRunRequest(BaseModel):
    document_id: str
    document_type: Literal["invoice", "contract", "form", "unknown"] = "unknown"


class PipelineRunResponse(BaseModel):
    document_id: str
    ocr: OcrResult
    extraction: ExtractionResult
    validation: ValidationResult
