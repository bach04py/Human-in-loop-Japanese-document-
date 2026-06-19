# app/services/ocr_api.py
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException
import uvicorn

# Ensure backend path is accessible
backend_path = str(Path(__file__).resolve().parents[2])
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.services.ocr import OcrService

# Initialize the FastAPI app
app = FastAPI(title="PaddleOCR Microservice")

print("Booting PaddleOCR Engine...")
ocr_service = OcrService()


@app.get("/api/v1/ocr/{document_id}")
async def process_document(document_id: str):
    """
    Receives a document ID, runs PaddleOCR, and returns the structural JSON.
    """
    try:
        print(f"Incoming request to process: {document_id}")
        result = await ocr_service.run(document_id=document_id)

        # FastAPI automatically converts Pydantic models to JSON
        return result.model_dump()

    except Exception as e:
        print(f"OCR Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # Run this server on port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
