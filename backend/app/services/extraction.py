import json
import logging
import os
import re
from typing import Any, Dict

import httpx

from app.schemas.documents import ExtractionResult, DocumentStatus

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PER-TYPE FIELD SCHEMAS
# Keys MUST match the frontend Structured Extraction Editor schemas so the
# extracted JSON populates the right inputs. `desc` guides the LLM; `type` is
# either "string" or "number".
# ---------------------------------------------------------------------------
FIELD_SCHEMAS: Dict[str, list[dict[str, str]]] = {
    "invoice": [
        {"key": "invoice_id", "type": "string", "desc": "Invoice number (請求書番号). If absent, use a tracking/reference number (e.g. EJ...JP)."},
        {"key": "company", "type": "string", "desc": "Vendor / billing company name (取引先), including legal entity such as 株式会社."},
        {"key": "date", "type": "string", "desc": "Issue date (発行日), ISO 8601 YYYY-MM-DD."},
        {"key": "due_date", "type": "string", "desc": "Payment due date (支払期限), ISO 8601 YYYY-MM-DD."},
        {"key": "amount", "type": "number", "desc": "Grand total (ご請求金額/合計) as a number, commas and ¥/円 stripped."},
        {"key": "tax", "type": "number", "desc": "Consumption tax amount (消費税) as a number, if shown."},
        {"key": "currency", "type": "string", "desc": "Currency code, default JPY."},
    ],
    "contract": [
        {"key": "company", "type": "string", "desc": "Counterparty / other party (相手方/甲乙) company name, with legal entity."},
        {"key": "contract_id", "type": "string", "desc": "Contract number (契約番号) or reference id."},
        {"key": "effective_date", "type": "string", "desc": "Effective / commencement date (発効日/契約開始日), ISO 8601."},
        {"key": "expiration_date", "type": "string", "desc": "Expiration / end date (満了日/契約終了日), ISO 8601."},
        {"key": "amount", "type": "number", "desc": "Contract value / total amount (契約金額) as a number."},
        {"key": "currency", "type": "string", "desc": "Currency code, default JPY."},
        {"key": "governing_law", "type": "string", "desc": "Governing law (準拠法), e.g. 日本法 / Japanese law."},
    ],
    "bill": [
        {"key": "company", "type": "string", "desc": "Biller / issuing company (請求元/発行者)."},
        {"key": "bill_id", "type": "string", "desc": "Account or customer number (お客様番号) / bill number."},
        {"key": "billing_period", "type": "string", "desc": "Billing period (請求期間/ご利用期間), kept as printed."},
        {"key": "date", "type": "string", "desc": "Issue date (発行日), ISO 8601."},
        {"key": "due_date", "type": "string", "desc": "Payment due date (お支払期限), ISO 8601."},
        {"key": "amount", "type": "number", "desc": "Amount due (請求金額/ご請求額) as a number."},
        {"key": "currency", "type": "string", "desc": "Currency code, default JPY."},
    ],
    "document": [
        {"key": "title", "type": "string", "desc": "Document title or subject (件名/タイトル)."},
        {"key": "document_id", "type": "string", "desc": "Document / control number (文書番号), if any."},
        {"key": "company", "type": "string", "desc": "Issuing organization or department (発行元/部署)."},
        {"key": "author", "type": "string", "desc": "Author / person in charge (担当者/作成者), if any."},
        {"key": "date", "type": "string", "desc": "Document date (日付), ISO 8601."},
        {"key": "reference", "type": "string", "desc": "Reference number or related document (参照番号), if any."},
    ],
    # Catch-all for documents that do not fit any structured type. Instead of
    # forcing rigid fields, capture a name and a faithful free-text summary.
    "other": [
        {"key": "name", "type": "string", "desc": "A short name/title describing what this document is (名称)."},
        {"key": "main_information", "type": "string", "desc": "A faithful 2-4 sentence summary of the document's key information (主な情報). Summarise only what is actually written; do not invent."},
    ],
}

# Document types that also carry an itemised list.
LINE_ITEM_TYPES = {"invoice", "bill"}

TYPE_LABELS = {
    "invoice": "invoice (請求書)",
    "contract": "contract (契約書)",
    "bill": "bill / receipt (請求・領収書)",
    "document": "enterprise document (社内文書)",
    "other": "other / general document (その他)",
}

BASE_RULES = """**Role:**
You are an expert data-extraction AI specialised in Japanese business documents
(invoices, contracts, bills/receipts and general enterprise documents). You read
raw OCR text and return a single, strictly-formatted JSON object.

**Rules:**
1. JSON ONLY: output nothing but valid JSON — no markdown, no commentary.
2. MISSING VALUES: if a field is not present in the text, set its "value" to null
   and "confidence" to 0.0. Never hallucinate or guess.
3. CONFIDENCE: 1.0 when explicit and clear; 0.5-0.8 when messy/typo'd/deduced; 0.0 when missing.
4. JAPANESE NAMES: keep legal entities (株式会社, 合同会社, etc.) and trim whitespace.
5. DATES: convert every date to ISO 8601 (YYYY-MM-DD); convert Japanese era dates
   (e.g. 令和5年 -> 2023) and formats like "2025年7月12日".
6. AMOUNTS: extract the printed number only; strip commas and symbols (¥, 円). Never
   do arithmetic. Default currency to "JPY" unless another currency is explicit.
7. ZERO GUESSING: if a value is garbled or absent, return null. Do NOT invent
   placeholder names or numbers.
8. LINE ITEMS (only when a "line_items" field is requested): the number at the far
   right of an item line is the total price, not the quantity. Default quantity to
   null unless explicit (e.g. "x2"). Recover prices from messy lines like
   "ItemName.138" -> 138. Do not drop items."""


class ExtractionService:
    """Type-aware structured extraction backed by Qwen2.5 (Ollama).

    The field set, prompt and JSON blueprint adapt to the document_type so that
    invoices, contracts, bills and enterprise documents each get their own
    structure filled automatically.
    """

    def __init__(self):
        # LLM server endpoint
        self.local_llm_url = os.environ.get("LLM_ENDPOINT", "http://127.0.0.1:11434/api/generate")
        self.model_name = os.environ.get("LLM_MODEL", "qwen2.5")
        self.llm_timeout_seconds = float(os.environ.get("LLM_TIMEOUT_SECONDS", "120"))
        # Future LayoutLMv3 Endpoint Placeholder
        self.layoutlm_url = os.environ.get("LAYOUTLM_ENDPOINT", "http://localhost:8001/predict")

    # ------------------------------------------------------------------
    # Type helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _resolve_type(document_type: str | None) -> str:
        """Map an incoming document_type to a schema.

        Anything unrecognised ('unknown', 'form', etc.) falls back to 'other',
        which captures a name plus a free-text summary instead of forcing the
        document into a rigid structure it does not match.
        """
        if document_type and document_type in FIELD_SCHEMAS:
            return document_type
        return "other"

    def _fields_for(self, document_type: str) -> list[dict[str, str]]:
        return FIELD_SCHEMAS[self._resolve_type(document_type)]

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    async def extract(
            self,
            document_id: str,
            ocr_text: str | None = None,
            layout_blocks: list | None = None,  # Accept the blocks here
            document_type: str = "unknown",
            use_layoutlm: bool = False
    ) -> ExtractionResult:
        dtype = self._resolve_type(document_type)

        if not ocr_text or not ocr_text.strip():
            return self._get_empty_result(document_id, dtype)

        # Serialize the Pydantic blocks into a clean JSON string
        if layout_blocks:
            layout_json_string = json.dumps([b.model_dump() for b in layout_blocks], ensure_ascii=False)
        else:
            layout_json_string = "[]"

        if use_layoutlm:
            parsed_data = await self._cal_layoutlm_v3(document_id, ocr_text)
        else:
            parsed_data = await self._call_open_weights(dtype, ocr_text, layout_json_string)

        if not parsed_data:
            parsed_data = self._baseline_extract(ocr_text, dtype)

        # Tag the resolved type so downstream consumers know the schema used.
        parsed_data.setdefault("document_type", dtype)

        overall_confidence = self._calculate_overall_confidence(parsed_data, dtype)

        return ExtractionResult(
            document_id=document_id,
            data=parsed_data,
            confidence=overall_confidence,
            status=DocumentStatus.extracted
        )

    # ------------------------------------------------------------------
    # Prompt building
    # ------------------------------------------------------------------
    def _build_prompt(self, document_type: str, ocr_text: str, layout_json_string: str) -> str:
        dtype = self._resolve_type(document_type)
        fields = FIELD_SCHEMAS[dtype]
        has_line_items = dtype in LINE_ITEM_TYPES

        field_doc = "\n".join(
            f'- "{f["key"]}" ({f["type"]}): {f["desc"]}' for f in fields
        )

        blueprint_lines = []
        for f in fields:
            if f["key"] == "currency":
                blueprint_lines.append(
                    '  "currency": {"value": "JPY", "confidence": 1.0, "reasoning": "..."}'
                )
            else:
                blueprint_lines.append(
                    f'  "{f["key"]}": {{"value": null, "confidence": 0.0, "reasoning": "..."}}'
                )
        if has_line_items:
            blueprint_lines.append('  "line_items": []')
        blueprint = "{\n" + ",\n".join(blueprint_lines) + "\n}"

        line_item_note = (
            '\nFor "line_items", return an array of objects with keys '
            '"description", "quantity", "unit_price", "total".'
            if has_line_items else ""
        )

        if dtype == "other":
            intro = (
                "This document does not fit a standard structure (it is not a "
                "plain invoice, contract or bill). Do NOT force it into rigid "
                "fields. Instead, populate EXACTLY the following fields, where "
                '"main_information" is a faithful summary of the actual content:'
            )
        else:
            intro = (
                f"This is a {TYPE_LABELS.get(dtype, dtype)}. "
                f"Extract EXACTLY the following fields:"
            )

        return (
            f"{BASE_RULES}\n\n"
            f"{intro}\n"
            f"{field_doc}\n"
            f"{line_item_note}\n\n"
            f"<raw_text>\n{ocr_text}\n</raw_text>\n\n"
            f"<layout_json>\n{layout_json_string}\n</layout_json>\n\n"
            f"Output ONLY valid JSON matching this exact shell (each field is an object "
            f'with "value", "confidence" and "reasoning"):\n{blueprint}'
        )

    # ------------------------------------------------------------------
    # OPEN-WEIGHTS BASELINE (QWEN 2.5)
    # ------------------------------------------------------------------
    async def _call_open_weights(
        self, document_type: str, ocr_text: str, layout_json_string: str
    ) -> Dict[str, Any]:
        full_prompt = self._build_prompt(document_type, ocr_text, layout_json_string)

        payload = {
            "model": self.model_name,
            "prompt": full_prompt,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
                "seed": 42,
            }
        }

        try:
            async with httpx.AsyncClient(timeout=self.llm_timeout_seconds) as client:
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

                # JSON EXTRACTION: grab the first '{' to the last '}' so any
                # conversational text around the JSON is ignored.
                match = re.search(r'\{.*\}', raw_json_string, re.DOTALL)
                if match:
                    raw_json_string = match.group(0)

                try:
                    return self._flatten_llm_result(json.loads(raw_json_string))
                except json.JSONDecodeError as e:
                    logger.error("Failed to parse LLM JSON: %s", e)
                    return {}
        except httpx.HTTPError as exc:
            logger.warning("LLM extraction unavailable, using baseline fallback: %s", exc)
            return {}

    # ------------------------------------------------------------------
    # transformer (FUTURE IMPLEMENTATION)
    # ------------------------------------------------------------------
    async def _cal_layoutlm_v3(self, document_id: str, ocr_text: str) -> Dict[str, Any]:
        """Placeholder for a future transformer-based extractor."""
        logger.warning("transformer is not yet implemented. Falling back to empty data.")
        return self._get_empty_result(document_id, "document").data

    # ------------------------------------------------------------------
    # UTILITIES
    # ------------------------------------------------------------------
    def _calculate_overall_confidence(
        self, parsed_data: Dict[str, Any], document_type: str = "unknown"
    ) -> float:
        """Average the per-field confidences; fall back to a presence ratio."""
        if not parsed_data:
            return 0.0

        keys = [f["key"] for f in self._fields_for(document_type)]

        scores = [
            float(conf)
            for key in keys
            if isinstance(conf := parsed_data.get(f"{key}_confidence"), (int, float))
        ]
        if scores:
            return round(sum(scores) / len(scores), 2)

        present = [key for key in keys if parsed_data.get(key) not in (None, "")]
        return round(len(present) / len(keys), 2) if keys else 0.0

    def _get_empty_result(
        self,
        document_id: str,
        document_type: str = "unknown",
        status: DocumentStatus = DocumentStatus.extracted,
    ) -> ExtractionResult:
        """Build an empty (flat) result whose keys match the type's schema."""
        dtype = self._resolve_type(document_type)
        data: Dict[str, Any] = {
            f["key"]: ("JPY" if f["key"] == "currency" else None)
            for f in FIELD_SCHEMAS[dtype]
        }
        data["document_type"] = dtype
        if dtype in LINE_ITEM_TYPES:
            data["line_items"] = []

        return ExtractionResult(
            document_id=document_id,
            data=data,
            confidence=0.0,
            status=status,
        )

    def _flatten_llm_result(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten {field: {value, confidence}} into {field: value, field_confidence: x}."""
        flat: Dict[str, Any] = {}
        for key, value in parsed_data.items():
            if isinstance(value, dict) and "value" in value:
                flat[key] = value.get("value")
                flat[f"{key}_confidence"] = value.get("confidence", 0.0)
            else:
                flat[key] = value
        return flat

    def _baseline_extract(self, ocr_text: str, document_type: str) -> Dict[str, Any]:
        """Regex fallback used only when the LLM is unavailable.

        Produces the type's flat field set; fills id/company/amount via regex
        where possible and leaves everything else null (never fabricated).
        """
        dtype = self._resolve_type(document_type)
        fields = FIELD_SCHEMAS[dtype]
        data: Dict[str, Any] = {
            f["key"]: ("JPY" if f["key"] == "currency" else None) for f in fields
        }

        id_match = re.search(
            r"(?:請求書番号|請求番号|契約番号|文書番号|お客様番号|番号|No\.?)\s*[:：]\s*([A-Za-z0-9\-]+)",
            ocr_text,
            re.IGNORECASE,
        )
        company_match = re.search(
            r"(?:取引先|請求元|相手方|発行元|会社|vendor|company)\s*[:：]\s*(.+)",
            ocr_text,
            re.IGNORECASE,
        )
        amount_match = re.search(
            r"(?:ご請求金額|請求金額|合計金額|契約金額|金額|amount)\s*[:：]\s*[¥￥]?\s*([0-9,]+)",
            ocr_text,
            re.IGNORECASE,
        )

        id_key = next((f["key"] for f in fields if f["key"].endswith("_id")), None)
        if id_key and id_match:
            data[id_key] = id_match.group(1)
        if "company" in data and company_match:
            data["company"] = company_match.group(1).strip()
        if "amount" in data and amount_match:
            data["amount"] = int(amount_match.group(1).replace(",", ""))

        data["document_type"] = dtype
        if dtype in LINE_ITEM_TYPES:
            data["line_items"] = []
        return data
