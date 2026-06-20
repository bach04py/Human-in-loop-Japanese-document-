import json
import logging
import os
import re
import unicodedata
from typing import Any, Dict
import httpx
from app.schemas.documents import ExtractionResult, DocumentStatus

logger = logging.getLogger(__name__)

# =========================================================================
# GLOBAL SYSTEM PROMPT (Applies to ALL documents)
# =========================================================================
GLOBAL_SYSTEM_PROMPT = """
**Role:**
You are an expert Data Extraction AI specialized in Japanese business documents. Your task is to process raw OCR text and convert it into a strictly formatted JSON object.

**Universal Extraction Rules:**
1. **JSON ONLY:** Output nothing but valid JSON. No markdown blocks, no explanations, no greetings.
2. **MISSING VALUES:** If a field is not found in the text, set its `value` to `null` and `confidence` to `0.0`. Do not hallucinate or guess.
3. **CONFIDENCE SCORING:** - Assign `1.0` if the value is explicitly clear.
   - Assign `0.5` - `0.8` if the OCR text is messy, contains typos, or requires deduction.
   - Assign `0.0` if missing.
4. **DATES:** Convert all dates to ISO 8601 format (`YYYY-MM-DD`). 
   - JAPANESE CALENDAR (和暦): Convert Heisei years (平成) correctly (e.g., Heisei 22 = 2010). Do not assume modern Gregorian years if the document context implies an older era.
5. **STRICTLY NO CALCULATION:** You are forbidden from doing math. Do not sum, add, or subtract any totals. Only extract the exact numbers printed on the page. If a total is not explicitly printed, return `null`.
6. **ZERO GUESSING:** If the OCR text for a field is garbled, illegible, or missing, return `null`. Do NOT invent or guess placeholder names.
7. **MESSY OCR RECOVERY:** If an OCR line looks garbled (e.g., "ItemName.138"), assume the trailing digits are the value.
8. **DYNAMIC EXTRACTION (HYBRID SCHEMA):** Your JSON blueprint contains a `dynamic_extra_fields` object. You MUST identify any other important business data points, financial values, clauses, or parameters not explicitly asked for. Invent clear, snake_case keys for each new piece of data and put them inside `dynamic_extra_fields`.
9. **SPATIAL ALIGNMENT:** You are provided with coordinate JSON. Use the Y-coordinates to align items horizontally. Items sharing similar Y-coordinates are on the same row.
10. **SEMANTIC ALIASING (CRITICAL):** Do not be overly literal with core field names. If a requested core field (like `invoice_id`, `contract_id`, `patent_number`) is missing, actively search for equivalent identifiers (e.g., 'Mail Item No', 'Tracking Number', 'Reference No', 'Application No'). Map that equivalent value directly into the core field, and explicitly state the alias used in the `reasoning` string. Do NOT exile primary identifiers to `dynamic_extra_fields`.
"""

# =========================================================================
# DYNAMIC DOCUMENT ROUTER CONFIGURATIONS
# =========================================================================
DOCUMENT_CONFIGS = {
    "invoice": {
        "core_fields": ["invoice_id", "company", "amount", "currency", "date"],
        "type_instructions": (
            "**INVOICE SPECIFIC RULES:**\n"
            "- Extract the Grand Total numerical value. Actively scan for keywords like '総合計', '合計額', or 'Total'.\n"
            "- Default `currency` to 'JPY' based on context.\n"
            "- LINE ITEMS: Extract to the array. The number at the far right is usually the total price.\n"
            "- CRITICAL FALLBACK: If an explicit 'Invoice ID' or 'Invoice Number' is missing, actively look for a 'Mail Item No.', 'Tracking Number', or 'Waybill' and map that value into the `invoice_id` field."
        ),
        "blueprint": '{\n  "invoice_id": {"value": null, "confidence": 0.0, "reasoning": "Explain"},\n  "company": {"value": null, "confidence": 0.0, "reasoning": "Explain"},\n  "amount": {"value": null, "confidence": 0.0, "reasoning": "Explain"},\n  "currency": {"value": null, "confidence": 0.0, "reasoning": "Explain"},\n  "date": {"value": null, "confidence": 0.0, "reasoning": "Explain"},\n  "line_items": [],\n  "dynamic_extra_fields": {\n    "[Insert Key 1]": {"value": null, "confidence": 0.0, "reasoning": "Explain"}\n  }\n}'
    },
    "contract": {
        "core_fields": ["contract_id", "party_a", "party_b", "effective_date", "total_value"],
        "type_instructions": (
            "**CONTRACT SPECIFIC RULES:**\n"
            "- Extract the Contract ID/Number.\n"
            "- Identify 'Party A' (Client) and 'Party B' (Provider).\n"
            "- Extract the Effective Date and Total Value."
        ),
        "blueprint": '{\n  "contract_id": {"value": null, "confidence": 0.0, "reasoning": "Explain"},\n  "party_a": {"value": null, "confidence": 0.0, "reasoning": "Explain"},\n  "party_b": {"value": null, "confidence": 0.0, "reasoning": "Explain"},\n  "effective_date": {"value": null, "confidence": 0.0, "reasoning": "Explain"},\n  "total_value": {"value": null, "confidence": 0.0, "reasoning": "Explain"},\n  "dynamic_extra_fields": {\n    "[Insert Key 1]": {"value": null, "confidence": 0.0, "reasoning": "Explain"}\n  }\n}'
    },
    "patent": {
        "core_fields": ["patent_number", "title", "applicant", "publication_date"],
        "type_instructions": (
            "**PATENT & TECHNICAL DOCUMENT RULES:**\n"
            "- Extract the Patent/Publication Number (e.g., WO... or 特願...).\n"
            "- Extract the Title of the Invention (発明の名称).\n"
            "- Extract the Applicant (出願人) and Publication Date.\n"
            "- IMPORTANT: Use `dynamic_extra_fields` to extract ALL rows/columns of experimental data, test results (実施例, 比較例), materials, and parameters."
        ),
        "blueprint": '{\n  "patent_number": {"value": null, "confidence": 0.0, "reasoning": "Explain"},\n  "title": {"value": null, "confidence": 0.0, "reasoning": "Explain"},\n  "applicant": {"value": null, "confidence": 0.0, "reasoning": "Explain"},\n  "publication_date": {"value": null, "confidence": 0.0, "reasoning": "Explain"},\n  "dynamic_extra_fields": {\n    "[Insert Key 1]": {"value": null, "confidence": 0.0, "reasoning": "Explain"}\n  }\n}'
    },
    "internal_form": {
        "core_fields": ["form_title", "employee_name", "department", "date_submitted"],
        "type_instructions": "**INTERNAL FORM SPECIFIC RULES:** Extract Form Title, Employee Name, Department, and Date.",
        "blueprint": '{\n  "form_title": {"value": null, "confidence": 0.0, "reasoning": "Explain"},\n  "employee_name": {"value": null, "confidence": 0.0, "reasoning": "Explain"},\n  "department": {"value": null, "confidence": 0.0, "reasoning": "Explain"},\n  "date_submitted": {"value": null, "confidence": 0.0, "reasoning": "Explain"},\n  "dynamic_extra_fields": {}\n}'
    },
    "fax": {
        "core_fields": ["sender", "recipient", "fax_number", "date", "subject"],
        "type_instructions": "**FAX SPECIFIC RULES:** Extract Sender, Recipient, Fax Number, Date, and Subject.",
        "blueprint": '{\n  "sender": {"value": null, "confidence": 0.0, "reasoning": "Explain"},\n  "recipient": {"value": null, "confidence": 0.0, "reasoning": "Explain"},\n  "fax_number": {"value": null, "confidence": 0.0, "reasoning": "Explain"},\n  "date": {"value": null, "confidence": 0.0, "reasoning": "Explain"},\n  "subject": {"value": null, "confidence": 0.0, "reasoning": "Explain"},\n  "dynamic_extra_fields": {}\n}'
    },
    "pdf_document": {
        "core_fields": ["document_title", "date", "author_or_sender", "summary"],
        "type_instructions": "**PDF DOCUMENT RULES:** Extract the main Title, Date, Author/Sender, and a 1-sentence Summary.",
        "blueprint": '{\n  "document_title": {"value": null, "confidence": 0.0, "reasoning": "Explain"},\n  "date": {"value": null, "confidence": 0.0, "reasoning": "Explain"},\n  "author_or_sender": {"value": null, "confidence": 0.0, "reasoning": "Explain"},\n  "summary": {"value": null, "confidence": 0.0, "reasoning": "Explain"},\n  "dynamic_extra_fields": {}\n}'
    },
    "scanned_document": {
        "core_fields": ["document_title", "date", "author_or_sender", "summary"],
        "type_instructions": "**SCANNED DOCUMENT RULES:** Extract Title, Date, Author/Sender, and Summary. Recover messy OCR.",
        "blueprint": '{\n  "document_title": {"value": null, "confidence": 0.0, "reasoning": "Explain"},\n  "date": {"value": null, "confidence": 0.0, "reasoning": "Explain"},\n  "author_or_sender": {"value": null, "confidence": 0.0, "reasoning": "Explain"},\n  "summary": {"value": null, "confidence": 0.0, "reasoning": "Explain"},\n  "dynamic_extra_fields": {}\n}'
    },
    "legacy_document": {
        "core_fields": ["document_title", "date", "author_or_sender", "summary"],
        "type_instructions": "**LEGACY DOCUMENT RULES:** Extract Title, Date, Author/Sender, and Summary. Formatting may be irregular.",
        "blueprint": '{\n  "document_title": {"value": null, "confidence": 0.0, "reasoning": "Explain"},\n  "date": {"value": null, "confidence": 0.0, "reasoning": "Explain"},\n  "author_or_sender": {"value": null, "confidence": 0.0, "reasoning": "Explain"},\n  "summary": {"value": null, "confidence": 0.0, "reasoning": "Explain"},\n  "dynamic_extra_fields": {}\n}'
    }
}


class ExtractionService:
    """
    Dynamic LayoutLM/LLM structured extraction service.
    Currently routes documents based on type to Qwen2.5 (32B).
    """

    def __init__(self):
        self.local_llm_url = os.environ.get("LLM_ENDPOINT", "http://127.0.0.1:11434/api/generate")
        self.model_name = os.environ.get("LLM_MODEL", "qwen2.5")
        self.layoutlm_url = os.environ.get("LAYOUTLM_ENDPOINT", "http://localhost:8001/predict")

    def _normalize_doc_type(self, raw_type: str) -> str:
        text = unicodedata.normalize('NFKD', raw_type).encode('ASCII', 'ignore').decode('utf-8')
        clean_key = re.sub(r'[\s\-]+', '_', text.strip().lower())
        return clean_key

    async def extract(
            self,
            document_id: str,
            ocr_text: str | None = None,
            layout_blocks: list | None = None,
            document_type: str = "invoice",
            use_layoutlm: bool = False
    ) -> ExtractionResult:

        route_key = self._normalize_doc_type(document_type)
        if route_key not in DOCUMENT_CONFIGS:
            logger.warning(
                f"Unknown document type '{document_type}' (Normalized: {route_key}). Falling back to 'pdf_document'.")
            route_key = "pdf_document"

        if not ocr_text or not ocr_text.strip():
            return self._get_empty_result(document_id, route_key)

        if layout_blocks:
            layout_json_string = json.dumps([b.model_dump() if hasattr(b, "model_dump") else b for b in layout_blocks],
                                            ensure_ascii=False)
        else:
            layout_json_string = "[]"

        if use_layoutlm:
            parsed_data = await self._cal_layoutlm_v3(document_id, ocr_text)
        else:
            parsed_data = await self._call_open_weights(ocr_text, layout_json_string, route_key)

        overall_confidence = self._calculate_overall_confidence(parsed_data, route_key)

        return ExtractionResult(
            document_id=document_id,
            data=parsed_data,
            confidence=overall_confidence,
            status=DocumentStatus.extracted
        )

    # --------------------------------------------------------------------------
    # LLM EXTRACTION LOGIC
    # --------------------------------------------------------------------------
    async def _call_open_weights(self, ocr_text: str, layout_json_string: str, route_key: str, lilt_context: str = "") -> Dict[str, Any]:

        config = DOCUMENT_CONFIGS[route_key]

        if layout_json_string and layout_json_string != "[]":
            layout_context = f"<layout_json>\n{layout_json_string}\n</layout_json>\n\n"
            instruction_text = "Extract the structured data using the raw text and the coordinate JSON below."
        else:
            layout_context = ""
            instruction_text = "Extract the structured data using the raw text below."

        full_prompt = (
            f"{GLOBAL_SYSTEM_PROMPT}\n\n"
            f"**Layout Context (LiLT):**\n{lilt_context}\n\n"  
            f"**User Request:**\n{instruction_text}\n\n"
            f"<raw_text>\n{ocr_text}\n</raw_text>\n\n"
            f"{layout_context}"
            f"CRITICAL INSTRUCTION: You must output ONLY valid JSON matching this exact blueprint schema. "
            f"Do not include any conversational text outside the JSON brackets:\n"
            f"{config['blueprint']}"
        )

        payload = {
            "model": self.model_name,
            "prompt": full_prompt,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
                "seed": 42
            }
        }

        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(self.local_llm_url, json=payload)

            if response.status_code != 200:
                print(f"\n[CRITICAL OLLAMA ERROR] Status Code: {response.status_code}")
                print(f"Ollama says: {response.text}\n")

            response.raise_for_status()

            try:
                result_data = response.json()
            except json.JSONDecodeError:
                return {}

            raw_json_string = result_data.get("response", "").strip()

            print("\n" + "=" * 50)
            print(f"RAW OLLAMA RESPONSE ({self.model_name} | Type: {route_key}):")
            print(raw_json_string)
            print("=" * 50 + "\n")

            if not raw_json_string:
                return {}

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

    # --------------------------------------------------------------------------
    # PLACEHOLDER FOR FUTURE AI
    # --------------------------------------------------------------------------
    async def _cal_layoutlm_v3(self, document_id: str, ocr_text: str) -> Dict[str, Any]:
        logger.warning("LayoutLM is not yet implemented. Falling back to empty data.")
        return self._get_empty_result(document_id, "pdf_document").data

    # --------------------------------------------------------------------------
    # PIPELINE UTILITIES
    # --------------------------------------------------------------------------
    def _calculate_overall_confidence(self, parsed_data: Dict[str, Any], route_key: str) -> float:
        if not parsed_data:
            return 0.0

        core_fields = DOCUMENT_CONFIGS[route_key]["core_fields"]

        confidence_scores = [
            field["confidence"]
            for key in core_fields
            if isinstance(field := parsed_data.get(key), dict) and "confidence" in field
        ]

        if not confidence_scores:
            return 0.0

        return round(sum(confidence_scores) / len(confidence_scores), 2)

    def _get_empty_result(self, document_id: str, route_key: str,
                          status: DocumentStatus = DocumentStatus.extracted) -> ExtractionResult:
        core_fields = DOCUMENT_CONFIGS[route_key]["core_fields"]

        # Build empty state dynamically based on the document type's core fields
        empty_data = {
            key: {"value": None, "confidence": 0.0, "reasoning": "Failed to extract"}
            for key in core_fields
        }

        # Ensure schemas maintain their array/object structures
        if route_key == "invoice":
            empty_data["line_items"] = []

        # Ensure dynamic_extra_fields is always present so downstream logic doesn't crash
        empty_data["dynamic_extra_fields"] = {}

        return ExtractionResult(
            document_id=document_id,
            data=empty_data,
            confidence=0.0,
            status=status
        )