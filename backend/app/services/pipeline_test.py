import asyncio
import json
import sys
from pathlib import Path

# Path fix
backend_path = str(Path(__file__).resolve().parents[2])
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# --- Add this missing import right here ---
from app.services.validation import ValidationService

from app.services.ocr import OcrService
from app.services.extraction import ExtractionService
from app.services.orchestrator import OrchestratorService


async def test_full_pipeline():
    print("Initializing Full AI Pipeline...")

    # 1. Boot up all the individual services
    ocr = OcrService()
    extractor = ExtractionService()
    validator = ValidationService()

    # 2. Hand them to the Orchestrator
    orchestrator = OrchestratorService(
        ocr_service=ocr,
        extraction_service=extractor,
        validation_service=validator
    )

    target_document_id = "receipt_01"
    print(f"\nRunning Full Pipeline on: {target_document_id}")
    print("Step 1: Running OCR...")
    print("Step 2: Feeding OCR Text & Layout into LLM Extractor...")

    try:
        # 3. Trigger the chain reaction!
        result = await orchestrator.run_pipeline(document_id=target_document_id)

        print("\n" + "=" * 50)
        print("PIPELINE SUCCESSFUL!")
        print("=" * 50)
        print("\nRAW OCR TEXT TRANSCRIPT:")
        print(result.ocr.text)
        print("-" * 50)
        print("\nLLM EXTRACTION RESULT:")
        # Print the final structured data the LLM generated!
        print(json.dumps(result.extraction.data, ensure_ascii=False, indent=2))

        print(f"\nOverall Extraction Confidence: {result.extraction.confidence * 100}%")

    except Exception as e:
        print(f"\nPIPELINE FAILED: {e}")


if __name__ == "__main__":
    asyncio.run(test_full_pipeline())