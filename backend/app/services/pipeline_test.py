import asyncio
import json
import sys
from pathlib import Path

# Path fix
backend_path = str(Path(__file__).resolve().parents[2])
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.services.validation import ValidationService
from app.services.ocr import OcrService
from app.services.extraction import ExtractionService
from app.services.summary import SummaryService  # <-- NEW IMPORT
from app.services.orchestrator import OrchestratorService


async def test_full_pipeline():
    print("Booting Pipeline...")

    # all the individual services
    ocr = OcrService()
    extractor = ExtractionService()
    validator = ValidationService()
    summary = SummaryService()

    # Hand to the Orchestrator
    orchestrator = OrchestratorService(
        ocr_service=ocr,
        extraction_service=extractor,
        validation_service=validator,
        summary_service=summary
    )

    target_document_id = "real_invoice_01"
    print(f"\nRunning Full Pipeline on: {target_document_id}")
    print("Step 1: Running OCR...")
    print("Step 2: Feeding OCR Text & Layout into LLM Extractor...")
    print("Step 3: Validating Math & Logic...")
    print("Step 4: Generating Summary...")

    try:
        result = await orchestrator.run_pipeline(document_id=target_document_id)

        print("\n" + "=" * 50)
        print("PIPELINE SUCCESSFUL")
        print("=" * 50)

        print("\n[NODE 1] RAW OCR TEXT TRANSCRIPT (Preview):")
        print(result.ocr.text[:150] + "...\n")

        print("-" * 50)
        print("[NODE 2] LLM EXTRACTION RESULT:")
        print(json.dumps(result.extraction.data, ensure_ascii=False, indent=2))

        print("-" * 50)
        print("[NODE 3] VALIDATION RESULT:")
        print(f"Is Valid: {result.validation.valid}")
        print(f"Confidence Penalty/Score: {result.validation.confidence * 100}%")
        if result.validation.issues:
            print("Issues Found:")
            for issue in result.validation.issues:
                print(f"  - [{issue.severity.upper()}] {issue.field}: {issue.message}")
        else:
            print("  - No issues found.")

        print("-" * 50)
        print("[NODE 4] SUMMARY:")
        print(result.summary)
        print("\n" + "=" * 50)

    except Exception as e:
        print(f"\n PIPELINE FAILED: {e}")


if __name__ == "__main__":
    asyncio.run(test_full_pipeline())