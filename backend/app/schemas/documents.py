from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

# Supported document types. "form"/"unknown" are kept for backward compatibility
# and resolve to the generic "other" schema in the extraction service.
DocumentType = Literal[
    "invoice", "contract", "bill", "document", "other", "form", "unknown"
]


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
    document_type: DocumentType = "unknown"


class ExtractionResult(BaseModel):
    document_id: str
    data: dict[str, Any]
    confidence: float = Field(ge=0, le=1)
    status: DocumentStatus = DocumentStatus.extracted


class ValidationRequest(BaseModel):
    document_id: str
    extracted_data: dict[str, Any] | None = None
    document_type: str | None = None


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
    ocr_text: str | None = None  # validator-corrected OCR text (if edited)
    document_type: str | None = None
    user: str | None = None
    notes: str | None = None


class FeedbackResponse(BaseModel):
    document_id: str
    stored: bool
    applied: bool = False  # whether the correction updated the stored document
    revision: int = 0  # number of feedback revisions recorded for this document
    status: DocumentStatus = DocumentStatus.feedback_received


class PipelineRunRequest(BaseModel):
    document_id: str
    document_type: DocumentType = "unknown"


class PipelineRunResponse(BaseModel):
    document_id: str
    document_type: str | None = None  # type chosen by the classification agent
    ocr: OcrResult
    extraction: ExtractionResult
    validation: ValidationResult
    summary: str | None = None


class StoredDocument(BaseModel):
    """An extracted document persisted to JSON, used as the chatbot's knowledge."""

    document_id: str
    document_type: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    summary: str | None = None
    saved_at: str | None = None


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    document_id: str
    message: str
    history: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    document_id: str
    reply: str
