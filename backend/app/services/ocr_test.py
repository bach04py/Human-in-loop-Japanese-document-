import asyncio
from pathlib import Path
from app.services.ocr import OcrService
import json

async def test_single_file():
    print("Initializing PaddleOCR Service...")
    service = OcrService()

    target_document_id = "real_invoice_02"

    print(f"Searching for and processing: {target_document_id}...")

    try:
        result = await service.run(document_id=target_document_id, include_boxes=True)

        print("\n=== RAW JSON OUTPUT ===")
        raw_json_str = result.model_dump_json()
        parsed_json = json.loads(raw_json_str)
        print(json.dumps(parsed_json, ensure_ascii=False, indent=2))
        print("\n" + "=" * 40)
        print("OCR TEST SUCCESSFUL!")
        print("=" * 40)
        print(f"Document ID: {result.document_id}")
        print(f"Average Confidence: {round(result.confidence * 100, 2)}%")
        print("\n--- Extracted Text Output ---")
        print(result.text)
        print("=" * 40)

    except FileNotFoundError:
        print(
            f"\nERROR: Could not find a file matching '{target_document_id}.*' inside your configured upload directory.")
        print(f"Current setting points to: {service._find_uploaded_document.__globals__['settings'].upload_dir}")

    except Exception as e:
        print(f"\nTEST FAILED: Unexpected error occurred: {e}")


if __name__ == "__main__":
    # Drive the async execution loop
    asyncio.run(test_single_file())