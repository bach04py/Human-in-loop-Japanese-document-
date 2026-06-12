import asyncio
import os
import json
import sys
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
sys.path.insert(0, backend_dir)
from extraction import ExtractionService


async def run_mock_tests():
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    mock_dir = os.path.join(current_script_dir, "tests", "mock_ocr_data")

    # Safety check
    if not os.path.exists(mock_dir):
        print(f"Error: Directory '{mock_dir}' not found.")
        print("Add mock .txt files.")
        return

    service = ExtractionService()
    print(f"Starting Extraction Tests with {service.model_name} (via Ollama)...\n")

    for filename in os.listdir(mock_dir):
        if filename.endswith(".txt"):
            filepath = os.path.join(mock_dir, filename)

            # Read the mock OCR text
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    ocr_text = f.read()
            except UnicodeDecodeError:
                with open(filepath, 'r', encoding='utf-16') as f:
                    ocr_text = f.read()

            print(f"Processing: {filename}")

            result = await service.extract(
                document_id=filename.replace(".txt", ""),
                ocr_text=ocr_text
            )

            output = {
                "document_id": result.document_id,
                "status": result.status.value if hasattr(result.status, 'value') else result.status,
                "confidence": result.confidence,
                "data": result.data
            }

            print(json.dumps(output, indent=2, ensure_ascii=False))
            print("-" * 50 + "\n")


if __name__ == "__main__":
    asyncio.run(run_mock_tests())