# API Contract

Base URL:

```text
http://localhost:8000/api/v1
```

## System

### GET /healthz

Returns service status and version.

Response:

```json
{
  "status": "ok",
  "service": "HITL Japanese Document Processing API",
  "version": "0.1.0",
  "environment": "development"
}
```

## Documents

### POST /documents

Uploads a PDF, image, scan, invoice, contract, or form.

Request:

```text
multipart/form-data file=<binary>
```

Response:

```json
{
  "document_id": "doc_...",
  "filename": "invoice.pdf",
  "content_type": "application/pdf",
  "status": "uploaded"
}
```

## Agents

### POST /ocr

Runs the OCR agent baseline.

Request:

```json
{
  "document_id": "doc_invoice_001",
  "language": "ja",
  "include_boxes": true
}
```

Response includes full text, OCR blocks, bounding boxes, orientation, and confidence. The frontend uses `blocks[].bbox` to render the OCR bounding-box overlay in the correction workspace.

Example response:

```json
{
  "document_id": "doc_invoice_001",
  "text": "株式会社ABC\n請求書番号: INV001\nご請求金額: ￥120,000",
  "blocks": [
    {
      "text": "株式会社ABC",
      "confidence": 0.94,
      "bbox": [48, 80, 220, 112],
      "page": 1,
      "orientation": "horizontal"
    },
    {
      "text": "請求書番号: INV001",
      "confidence": 0.91,
      "bbox": [48, 122, 260, 154],
      "page": 1,
      "orientation": "horizontal"
    }
  ],
  "confidence": 0.92,
  "status": "ocr_completed"
}
```

### POST /extract

Runs the structured extraction baseline.

Request:

```json
{
  "document_id": "doc_invoice_001",
  "ocr_text": "株式会社ABC\n請求書番号: INV001",
  "document_type": "invoice"
}
```

Response includes extracted JSON and confidence.

### POST /validate

Runs validation rules against extracted data.

Request:

```json
{
  "document_id": "doc_invoice_001",
  "extracted_data": {
    "invoice_id": "INV001",
    "company": "株式会社ABC",
    "amount": 120000
  }
}
```

Response includes validity, confidence, and issue list.

## Human Feedback

### POST /feedback

Stores human corrections for future correction memory.

Request:

```json
{
  "document_id": "doc_invoice_001",
  "corrections": {
    "company": "株式会社ABC",
    "amount": 120000
  },
  "user": "reviewer@example.com",
  "notes": "Confirmed against original scan."
}
```

## Workflow

### POST /pipeline/run

Runs the week 1 baseline orchestration flow:

```text
OCR -> Extraction -> Validation
```

Request:

```json
{
  "document_id": "doc_invoice_001",
  "document_type": "invoice"
}
```

This endpoint is the week 1 integration contract that will later be replaced by LangGraph orchestration.
