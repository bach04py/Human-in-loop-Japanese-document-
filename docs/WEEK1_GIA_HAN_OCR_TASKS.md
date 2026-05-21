# Week 1 Tasks - Tang Gia Han

Role: OCR & Vision Engineer

## Goal

Create the first Japanese OCR baseline so the backend team can later connect real OCR output to the `/api/v1/ocr` endpoint.

## What To Do

1. Research Japanese OCR tools.
   - Start with PaddleOCR Japanese.
   - Check support for printed Japanese, scanned documents, receipts, and forms.
   - Note whether vertical Japanese text is supported directly or needs preprocessing.

2. Prepare sample input data.
   - Collect 5-10 simple Japanese sample documents.
   - Include at least one invoice or receipt.
   - Include at least one low-quality scanned image if possible.
   - Put only small safe sample files in `data/samples/ocr/` if they can be shared.

3. Build the OCR baseline.
   - Create code under `backend/app/services/ocr.py` or a helper module under `backend/app/services/ocr/` if it grows.
   - The output must match the API contract in `docs/API_CONTRACT.md`.
   - Return:
     - full extracted text
     - text blocks
     - confidence score
     - bounding boxes when available
     - text orientation when available

4. Create a simple evaluation note.
   - Record which documents worked well.
   - Record common errors: wrong Kanji, missed vertical text, broken bounding boxes, noisy scan failures.
   - Save notes in `docs/OCR_BASELINE_NOTES.md`.

## Expected Deliverables

- OCR baseline code or notebook.
- OCR result format compatible with `OcrResult`.
- Short benchmark notes.
- Recommendation for week 2 improvements.

## Files To Read First

- `docs/API_CONTRACT.md`
- `backend/app/services/ocr.py`
- `backend/app/schemas/documents.py`

## Done Means

The team can call the OCR service with a document ID and receive structured Japanese OCR output that can be passed to extraction.
