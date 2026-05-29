import json
import logging
import os
from typing import Any, Dict
import httpx
from app.schemas.documents import ExtractionResult, DocumentStatus

logger = logging.getLogger(__name__)
SYSTEM_PROMPT = """
**Role / System Prompt:**
You are an expert Data Extraction AI specialized in Japanese business documents. Your task is to process raw OCR text from an invoice and convert it into a strictly formatted JSON object.

**Extraction Rules:**
1. **JSON ONLY:** Output nothing but valid JSON. No markdown blocks, no explanations.
2. **MISSING VALUES:** If a field is not found in the text, set its `value` to `null` and `confidence` to `0.0`. Do not hallucinate or guess.
3. **CONFIDENCE SCORING:** - Assign `1.0` if the value is explicitly clear.
   - Assign `0.5` - `0.8` if the OCR text is messy, contains typos, or requires deduction.
   - Assign `0.0` if missing.
4. **JAPANESE COMPANY NAMES:** Extract the exact vendor/billing company name including legal entities like 株式会社 (Co., Ltd.) or 合同会社 (LLC). Strip any extra whitespace.
5. **DATES:** Convert all dates to ISO 8601 format (`YYYY-MM-DD`). Convert Japanese era dates (e.g., 令和5年 = 2023) automatically.
6. **AMOUNTS & CURRENCY:** Extract the **Grand Total** numerical value as a clean integer/float. Remove commas and symbols (¥, 円). Default the `currency` to "JPY" unless another currency (like USD) is explicitly stated.

**JSON Schema:**
{
  "type": "object",
  "properties": {
    "invoice_id": { "type": "object", "properties": { "value": { "type": ["string", "null"] }, "confidence": { "type": "number" } } },
    "company": { "type": "object", "properties": { "value": { "type": ["string", "null"] }, "confidence": { "type": "number" } } },
    "amount": { "type": "object", "properties": { "value": { "type": ["number", "null"] }, "confidence": { "type": "number" } } },
    "currency": { "type": "object", "properties": { "value": { "type": ["string", "null"] }, "confidence": { "type": "number" } } },
    "date": { "type": "object", "properties": { "value": { "type": ["string", "null"] }, "confidence": { "type": "number" } } },
    "line_items": { "type": "array", "items": { "type": "object", "properties": { "description": { "type": "string" }, "quantity": { "type": ["number", "null"] }, "unit_price": { "type": ["number", "null"] }, "total": { "type": ["number", "null"] } } } }
  },
  "required": ["invoice_id", "company", "amount", "currency", "date", "line_items"]
}

**Example Interaction:**
<document>
請求書
株式会社テストベンダー
2023年10月5日
請求番号: INV-992
合計金額: ¥15,000
</document>

{"invoice_id": {"value": "INV-992", "confidence": 1.0}, "company": {"value": "株式会社テストベンダー", "confidence": 1.0}, "amount": {"value": 15000, "confidence": 1.0}, "currency": {"value": "JPY", "confidence": 1.0}, "date": {"value": "2023-10-05", "confidence": 1.0}, "line_items": []}

**User Request:**
Extract the structured data from the following OCR text, adhering strictly to the schema and rules.

<document>
{ocr_text}
</document>
"""

class ExtractionService:
    """
    Week 1 baseline stub for LayoutLM/LLM structured extraction.
    currently supporting Qwen2.5 Baseline and LayoutLMv3 for future
    """
    CORE_FIELDS = ["invoice_id", "company", "amount", "currency", "date"]
    def __init__(self):
        # LLM server endpoint
        self.local_llm_url = os.environ.get("LLM_ENDPOINT", "http://127.0.0.1:11434/api/generate")
        self.model_name = os.environ.get("LLM_MODEL", "qwen2.5")
        # Future LayoutLMv3 Endpoint Placeholder
        self.layoutlm_url = os.environ.get("LAYOUTLM_ENDPOINT", "http://localhost:8001/predict")

    async def extract(
            self,
            document_id: str,
            ocr_text: str | None = None,
            document_type: str = "unknown",
            use_layoutlm: bool = False
    ) -> ExtractionResult:
        if not ocr_text or not ocr_text.strip():
            return self._get_empty_result(document_id)

        if use_layoutlm:
            logger.info(f"Routing document {document_id} to layoutLMv3 server...")
            parsed_data = await self._cal_layoutlm_v3(document_id, ocr_text)
        else:
            logger.info(f"Routing document {document_id} to {self.model_name}... ")
            parsed_data = await self._call_open_weights(ocr_text)

        overall_confidence = self._calculate_overall_confidence(parsed_data)

        return ExtractionResult(
            document_id=document_id,
            data=parsed_data,
            confidence=overall_confidence,
            status=DocumentStatus.extracted
        )

#--------------------------------------------------------------------------
# OPEN-WEIGHTS BASELINE (QWEN 2.5)
    async def _call_open_weights(self, ocr_text: str) -> Dict[str, Any]:
        """Handles extraction with JSON cleaning"""

        full_prompt = f"{SYSTEM_PROMPT}\n\nUser Request: Extract structured data from the following OCR text:\n\n{ocr_text}"

        payload = {
            "model": self.model_name,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": 0.0
            }
        }

        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(self.local_llm_url, json=payload)
            response.raise_for_status()

            try:
                result_data = response.json()
            except json.JSONDecodeError:
                return {}

            raw_json_string = result_data.get("response", "").strip()

            if not raw_json_string:
                return {}

            # MARKDOWN STRIPPING
            if raw_json_string.startswith("```json"):
                raw_json_string = raw_json_string[7:]
            elif raw_json_string.startswith("```"):
                raw_json_string = raw_json_string[3:]

            if raw_json_string.endswith("```"):
                raw_json_string = raw_json_string[:-3]

            raw_json_string = raw_json_string.strip()

            try:
                return json.loads(raw_json_string)
            except json.JSONDecodeError:
                return {}

#--------------------------------------------------------------------------
# LAYOUTLMv3 (FUTURE IMPLEMENTATION)
    async def _cal_layoutlm_v3(self, document_id: str, ocr_text: str) -> Dict[str, Any]:
        """
        Placeholder for layoutv3 if possible
        """
        logger.warning("LayoutLMv3 is not yet implemented. Falling back to empty data.")
        return self._get_empty_result(document_id).data
#--------------------------------------------------------------------------
# UTILITIES
    def _calculate_overall_confidence(self, parsed_data: Dict[str, Any]) -> float:
        """
        Calculates average confidence.
        """
        if not parsed_data:
            return 0.0

        # Uses assignment expression (walrus operator)
        confidence_scores = [
            field["confidence"]
            for key in self.CORE_FIELDS
            if isinstance(field := parsed_data.get(key), dict) and "confidence" in field
        ]

        if not confidence_scores:
            return 0.0

        return round(sum(confidence_scores) / len(confidence_scores), 2)

    def _get_empty_result(
        self,
        document_id: str,
        status: DocumentStatus = DocumentStatus.extracted
    ) -> ExtractionResult:
        """
        Dynamically builds the empty state structure from CORE_FIELDS.
        """
        empty_data = {
            key: {"value": None, "confidence": 0.0}
            for key in self.CORE_FIELDS
        }
        empty_data["line_items"] = []

        return ExtractionResult(
            document_id=document_id,
            data=empty_data,
            confidence=0.0,
            status=status
        )