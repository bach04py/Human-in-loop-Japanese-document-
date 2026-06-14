import json
import logging
import os
from typing import Any, Dict
import httpx
from app.schemas.documents import ExtractionResult, DocumentStatus
import re
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
6. **AMOUNTS & CURRENCY:** Extract the **Grand Total** numerical value. Actively scan the bottom of the document for keywords like "総合計", "合計額", or "Total". The total value may be located far to the right of the keyword. Remove commas and symbols (¥, 円). Default `currency` to "JPY" unless explicitly stated otherwise.
7. **INVOICE ID FALLBACK:** If there is no explicit "Invoice Number" or "請求書番号", look for a Tracking Number, Mail Item No (e.g., EJ...JP), or Reference Number, and use that as the `invoice_id` instead.
8. **STRICTLY NO CALCULATION:** You are forbidden from doing math. Never multiply a unit price by a quantity. Only extract the exact final `total` number printed on the far right of the item line. If a number is missing, leave it as `null`.
9. **FLEXIBLE DATES:** Actively look for dates in standard formats and Japanese formats (e.g., "2025年 7月12日"). Always convert the final extracted value to the ISO 8601 format (`YYYY-MM-DD`).
10. **ZERO GUESSING:** If the OCR text for a field like the company name is garbled, illegible, or missing, you must return `null`. Do NOT invent, assume, or guess placeholder names (like "Takashimaya") just to fill the field.
11. **MESSY OCR RECOVERY:** If an OCR line looks like "ItemName.138" or "ItemName 19--2418", assume the trailing digits are the price (e.g., 138, 418). Do your best to separate the item description from the price, even if the text is garbled. Do not drop items.
12. **LINE ITEM PRICING:** Japanese receipts often do not list a quantity if the quantity is 1. The number at the far right of an item string is almost always the total price, NOT the quantity. Default quantity to null unless explicitly stated (e.g., "x2" or "2点").
**JSON Schema:**
{
  "type": "object",
  "properties": {
    "invoice_id": { "type": "object", "properties": { "value": { "type": ["string", "null"] }, "confidence": { "type": "number" }, "reasoning": { "type": "string" } } },
    "company": { "type": "object", "properties": { "value": { "type": ["string", "null"] }, "confidence": { "type": "number" }, "reasoning": { "type": "string" } } },
    "amount": { "type": "object", "properties": { "value": { "type": ["number", "null"] }, "confidence": { "type": "number" }, "reasoning": { "type": "string" } } },
    "currency": { "type": "object", "properties": { "value": { "type": ["string", "null"] }, "confidence": { "type": "number" }, "reasoning": { "type": "string" } } },
    "date": { "type": "object", "properties": { "value": { "type": ["string", "null"] }, "confidence": { "type": "number" }, "reasoning": { "type": "string" } } },
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
Extract the structured data using the raw text and the coordinate JSON below.

<raw_text>
{ocr_text}
</raw_text>

<layout_json>
{layout_json}
</layout_json>
"""

class ExtractionService:
    """
    Week 1 baseline stub for LayoutLM/LLM structured extraction.
    currently supporting Qwen2.5 Baseline and transformer for future
    """
    CORE_FIELDS = ["invoice_id", "company", "amount", "currency", "date"]
    def __init__(self):
        # LLM server endpoint
        self.local_llm_url = os.environ.get("LLM_ENDPOINT", "http://127.0.0.1:11434/api/generate")
        self.model_name = os.environ.get("LLM_MODEL", "qwen2.5")
        # Future transformer Endpoint Placeholder
        self.layoutlm_url = os.environ.get("LAYOUTLM_ENDPOINT", "http://localhost:8001/predict")

    async def extract(
            self,
            document_id: str,
            ocr_text: str | None = None,
            layout_blocks: list | None = None,  # Accept the blocks here
            document_type: str = "unknown",
            use_layoutlm: bool = False
    ) -> ExtractionResult:
        if not ocr_text or not ocr_text.strip():
            return self._get_empty_result(document_id)

        # Serialize the Pydantic blocks into a clean JSON string
        if layout_blocks:
            layout_json_string = json.dumps([b.model_dump() for b in layout_blocks], ensure_ascii=False)
        else:
            layout_json_string = "[]"

        if use_layoutlm:
            parsed_data = await self._cal_layoutlm_v3(document_id, ocr_text)
        else:
            # Pass both the text and the layout JSON to LLM caller
            parsed_data = await self._call_open_weights(ocr_text, layout_json_string)

        overall_confidence = self._calculate_overall_confidence(parsed_data)

        return ExtractionResult(
            document_id=document_id,
            data=parsed_data,
            confidence=overall_confidence,
            status=DocumentStatus.extracted
        )

#--------------------------------------------------------------------------
# OPEN-WEIGHTS BASELINE (QWEN 2.5)
    async def _call_open_weights(self, ocr_text: str, layout_json_string: str) -> Dict[str, Any]:

        # removed the <layout_json> block to stop confusing the AI
        full_prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"<raw_text>\n{ocr_text}\n</raw_text>\n\n"
            f"CRITICAL INSTRUCTION: Output ONLY valid JSON matching this exact blueprint schema structural shell:\n"
            f"{{\n"
            f'  "invoice_id": {{"value": null, "confidence": 0.0, "reasoning": "Explain why"}},\n'
            f'  "company": {{"value": null, "confidence": 0.0, "reasoning": "Explain why"}},\n'
            f'  "amount": {{"value": null, "confidence": 0.0, "reasoning": "Explain why"}},\n'
            f'  "currency": {{"value": "JPY", "confidence": 1.0, "reasoning": "Explain why"}},\n'
            f'  "date": {{"value": null, "confidence": 0.0, "reasoning": "Explain why"}},\n'
            f'  "line_items": []\n'
            f"}}"
        )

        payload = {
            "model": self.model_name,
            "prompt": full_prompt,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.1,  # <-- Change to 0.1 to clear Ollama's cache
                "top_p": 0.9,  # <-- Add this to help it think
                "seed": 42  # <-- Add a random seed to force a fresh run
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

            # TEMPORARY DEBUG: Let's see exactly what Qwen is doing
            print("\n" + "*" * 40)
            print("RAW LLM OUTPUT:")
            print(raw_json_string)
            print("*" * 40 + "\n")

            # JSON EXTRACTION
            # This looks for the very first '{' and the very last '}'
            # and ignores all conversational text outside of them.
            try:
                match = re.search(r'\{.*\}', raw_json_string, re.DOTALL)
                if match:
                    clean_json = match.group(0)
                    return json.loads(clean_json)
                else:
                    logger.error("No JSON brackets found in the LLM output.")
                    return {}
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM JSON: {e}")
                return {}

#--------------------------------------------------------------------------
# transformer (FUTURE IMPLEMENTATION)
    async def _cal_layoutlm_v3(self, document_id: str, ocr_text: str) -> Dict[str, Any]:
        """
        Placeholder for transformer if possible
        """
        logger.warning("transformer is not yet implemented. Falling back to empty data.")
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