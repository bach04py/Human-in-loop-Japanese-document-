import os
import httpx
import logging

logger = logging.getLogger(__name__)


class ClassificationService:
    """Reads raw OCR text and routes it to the correct document schema."""

    def __init__(self):
        self.local_llm_url = os.environ.get("LLM_ENDPOINT", "http://127.0.0.1:11434/api/generate")
        self.model_name = os.environ.get("LLM_MODEL", "qwen2.5")

        self.valid_categories = [
            "invoice", "contract", "patent", "internal_form",
            "fax", "pdf_document", "scanned_document", "legacy_document"
        ]

    async def classify(self, ocr_text: str) -> str:
        if not ocr_text:
            return "document_pdf"  # Safe fallback
        sample_text = ocr_text[:1500]

        prompt = (
            "You are a strict, precise document classification routing AI.\n"
            "Look at the OCR text below and classify it into EXACTLY ONE of these categories:\n"
            f"{self.valid_categories}\n\n"
            "RULES:\n"
            "1. Output NOTHING but the exact string of the category.\n"
            "2. If it is an invoice, receipt, or bill, choose 'invoice'.\n"
            "3. If it is a legal agreement or contract, choose 'contract'.\n"
            "4. If it is an internal request or form, choose 'internal_form'.\n"
            "5. If it is a fax, choose 'fax'.\n"
            "6. If you are unsure, default to 'pdf_document'.\n\n"
            f"=== RAW OCR TEXT ===\n{sample_text}\n===================="
        )

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.0,  # Absolute zero creativity for strict routing
                "top_p": 0.9
            }
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.local_llm_url, json=payload)
                response.raise_for_status()

                result = response.json().get("response", "").strip().lower()

                # Verify the LLM didn't hallucinate a category
                for valid_key in self.valid_categories:
                    if valid_key in result:
                        return valid_key

                return "document_pdf"  # Fallback if confused

        except Exception as e:
            logger.error(f"Classification failed: {e}")
            return "document_pdf"