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

Response includes full text, OCR blocks, bounding boxes, orientation, and confidence.

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
