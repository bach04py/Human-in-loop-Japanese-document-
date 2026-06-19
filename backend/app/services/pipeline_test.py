# app/services/pipeline_test.py
import asyncio
import json
import sys
import httpx
from pathlib import Path

backend_path = str(Path(__file__).resolve().parents[2])
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.services.validation import ValidationService
from app.services.extraction import ExtractionService
from app.services.summary import SummaryService
from app.services.classification import ClassificationService
from app.services.orchestrator import OrchestratorService
from app.schemas import OcrResult

from app.services.chat import ChatService
from app.services import document_store


async def fetch_ocr_from_microservice(document_id: str) -> OcrResult:
    """Makes an HTTP POST request to our isolated OCR server."""

    payload = {
        "document_id": document_id,
        "include_boxes": True
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post("http://localhost:8000/api/v1/ocr", json=payload)

        # Throw error if server fails
        response.raise_for_status()

        # Convert the JSON response back into Pydantic model
        return OcrResult(**response.json())


async def test_full_pipeline():
    print("Booting PyTorch Pipeline...")

    classifier = ClassificationService()
    extractor = ExtractionService()
    validator = ValidationService()
    summary = SummaryService()

    target_document_id = "real_invoice_01"

    print(f"\n Requesting OCR from Microservice for: {target_document_id}...")
    try:
        ocr_result = await fetch_ocr_from_microservice(target_document_id)
        print("Successfully received OCR JSON from server")
    except Exception as e:
        print(f"Failed to reach OCR Microservice. Is it running? Error: {e}")
        return

    orchestrator = OrchestratorService(
        extraction_service=extractor,
        validation_service=validator,
        summary_service=summary,
        classification_service=classifier,
    )

    try:
        result = await orchestrator.run_pipeline(
            document_id=target_document_id,
            precomputed_ocr=ocr_result
        )

        print("\n" + "=" * 50)
        print("PIPELINE SUCCESSFUL")
        print("=" * 50)

        print("\n[VALIDATION RESULTS]")
        print(f"Status: {'Valid' if result.validation.valid else 'Invalid'}")
        print(f"Confidence: {result.validation.confidence}")

        if result.validation.issues:
            print("\nIssues Found:")
            for issue in result.validation.issues:
                print(f"  - [{issue.severity.upper()}] {issue.field}: {issue.message}")
        else:
            print("\nIssues Found: None")

        print("\n[AI SUMMARY]")
        print(result.summary)

        # Test the Chat functionality using the saved document
        print("\n" + "=" * 50)
        print("TESTING CHATBOT")
        print("=" * 50)

        saved_doc = document_store.load_document(target_document_id)

        if saved_doc:
            chat_service = ChatService()
            test_question = "What is the total amount of this document, and what is the invoice ID?"

            print(f"User: {test_question}\n")
            print("Chatbot is thinking...")

            # Ask the LLM
            reply = await chat_service.answer(document=saved_doc, message=test_question)
            print(f"\nAI: {reply}")
        else:
            print(f"Error: Could not find saved document for {target_document_id}.")

        print("\n" + "=" * 50)

    except Exception as e:
        print(f"\n PIPELINE FAILED: {e}")


if __name__ == "__main__":
    asyncio.run(test_full_pipeline())
