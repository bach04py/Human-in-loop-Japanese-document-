# Week 1 Tasks - Lu Huy Khang

Role: LLM & Extraction Engineer

## Goal

Create the first structured extraction baseline so OCR text can become usable JSON data.

## What To Do

1. Research extraction approaches.
   - Study LayoutLMv3 for document-aware extraction.
   - Study prompt-based JSON generation with Phi-3 Mini or Qwen2.5.
   - Compare which approach is realistic for the first prototype.

2. Define the first JSON schema.
   - Start with invoice fields:
     - `invoice_id`
     - `company`
     - `amount`
     - `currency`
     - `date`
     - `line_items`
   - Add optional confidence per field if practical.
   - Save the schema in `docs/EXTRACTION_SCHEMA.md`.

3. Improve the extraction baseline.
   - Work from `backend/app/services/extraction.py`.
   - Keep the response compatible with `ExtractionResult` in `backend/app/schemas/documents.py`.
   - Accept OCR text and return structured data.
   - Keep placeholder logic simple if no model is installed yet, but make the function shape ready for model integration.

4. Prepare prompt baseline.
   - Write a prompt that asks an LLM to extract valid JSON from Japanese OCR text.
   - Include rules for missing values, uncertain fields, and Japanese company names.
   - Save it in `docs/LLM_EXTRACTION_PROMPT.md`.

## Expected Deliverables

- Extraction prototype.
- JSON schema.
- LLM prompting baseline.
- Notes about which model should be used in week 2.

## Files To Read First

- `docs/API_CONTRACT.md`
- `backend/app/services/extraction.py`
- `backend/app/schemas/documents.py`

## Done Means

The team can pass OCR text to the extraction module and receive predictable structured JSON for validation and frontend editing.
