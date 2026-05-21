# Week 1 Tasks - Tang My Han

Role: Frontend & Human Feedback Engineer

## Goal

Create the first frontend skeleton and upload workflow so users can submit Japanese documents and later correct OCR/extraction results.

## What To Do

1. Research enterprise dashboard UI.
   - Focus on clear document upload, review, correction, and approval workflows.
   - Keep the UI practical and easy to scan.
   - Avoid a marketing-style landing page; the first screen should be useful.

2. Setup the Next.js frontend.
   - Work inside `frontend/`.
   - Use Next.js and TailwindCSS.
   - Add a simple API client that points to `http://localhost:8000/api/v1`.

3. Build upload UI prototype.
   - Create an upload page for PDF/image files.
   - Call `POST /api/v1/documents`.
   - Display:
     - uploaded filename
     - returned `document_id`
     - upload status

4. Prepare correction workflow mockup.
   - Add a page or component showing:
     - OCR text area
     - extracted fields editor
     - approve button
     - submit correction button
   - Use mock data first if backend integration is not ready.

5. Prepare thesis/evaluation notes.
   - Write the first outline in `docs/THESIS_OUTLINE.md`.
   - Write evaluation plan notes in `docs/EVALUATION_PLAN.md`.

## Expected Deliverables

- Frontend skeleton.
- Upload interface.
- Dashboard or correction mockup.
- Thesis outline.
- Evaluation plan.

## Files To Read First

- `frontend/README.md`
- `docs/API_CONTRACT.md`
- `docs/architecture.mmd`

## Done Means

A user can open the frontend, upload a file, see the backend response, and understand where OCR correction and approval will happen next.
