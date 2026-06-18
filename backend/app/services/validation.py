import re
from typing import Any
from app.schemas import ValidationIssue, ValidationResult

# Match the core fields from extraction.py
REQUIRED_FIELDS_BY_TYPE = {
    "invoice": ["invoice_id", "amount"],
    "contract": ["contract_id", "party_a", "party_b"],
    "patent": ["patent_number", "applicant"],
    "internal_form": ["form_title", "employee_name"],
    "fax": ["sender", "recipient", "fax_number"],
    "pdf_document": ["document_title", "author_or_sender"],
    "scanned_document": ["document_title"],
    "legacy_document": ["document_title"]
}

"""
MATH_CHECK_REGISTRY = {
    "invoice": {
        "total_field": "amount",
        "items_field": "line_items",
        "item_total_key": "total_amount"
    },
    "internal_form": {
        "total_field": "total_reimbursement",
        "items_field": "expenses",
        "item_total_key": "amount"
    },
    "contract": {
        "total_field": "total_value",
        "items_field": "fee_schedule",
        "item_total_key": "amount"
    }
}"""
class ValidationService:
    """Dynamic Validation Agent: Type-aware and Confidence-based checks."""

    def _extract_number(self, value: Any) -> float | None:
        """Safely extracts numbers and auto-corrects common OCR punctuation errors."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)

        val_str = str(value)

        # OCR Typo Correction: JPY doesn't use decimals.
        # Strip all periods and commas.
        if any(curr in val_str.upper() for curr in ["¥", "JPY", "円"]):
            val_str = val_str.replace('.', '').replace(',', '')
        else:
            # For weights (like 1.5kg) or USD, keep the period but strip commas
            val_str = val_str.replace(',', '')

        # Extract the remaining clean number
        numbers = re.findall(r'-?\d+(?:\.\d+)?', val_str)
        if numbers:
            return float(numbers[0])
        return None

    async def validate(
            self, document_id: str, extracted_data: dict | None = None, document_type: str = "invoice"
    ) -> ValidationResult:
        issues: list[ValidationIssue] = []
        data = extracted_data or {}
        is_valid = True

        # Normalize type key
        doc_type = document_type.strip().lower()
        required_fields = REQUIRED_FIELDS_BY_TYPE.get(doc_type, [])

        # Checks all fields, even dynamic ones
        # Flatten the dictionary to check nested fields
        all_fields = list(data.items())
        if "dynamic_extra_fields" in data:
            all_fields.extend(data["dynamic_extra_fields"].items())

        for key, field_data in all_fields:
            if isinstance(field_data, dict) and "confidence" in field_data:
                conf = field_data.get("confidence", 0.0)
                if conf < 0.8 and conf > 0.0:  # Ignore 0.0 as it usually means missing (handled below)
                    issues.append(
                        ValidationIssue(
                            field=key,
                            message=f"Low confidence ({conf}) for field '{key}'.",
                            severity="warning"
                        )
                    )

        # FIELD CHECK (Based on Document Type)
        for req_field in required_fields:
            field_dict = data.get(req_field, {})
            val = field_dict.get("value")

            if val is None or val == "":
                is_valid = False
                issues.append(
                    ValidationIssue(
                        field=req_field,
                        message=f"Critical missing field for {doc_type}: {req_field}",
                        severity="error",
                    )
                )

        # MATH CHECK
        if doc_type == "invoice" and "line_items" in data and data["line_items"]:
            amount_dict = data.get("amount", {})
            raw_grand_total = amount_dict.get("value")
            grand_total = self._extract_number(raw_grand_total)

            if grand_total is not None:
                calculated_total = 0.0
                for item in data.get("line_items", []):
                    # Check for different possible keys the LLM might use
                    item_total_raw = item.get("total_amount") or item.get("total") or item.get("price")
                    item_val = self._extract_number(item_total_raw)
                    if item_val is not None:
                        calculated_total += item_val

                if calculated_total > 0 and grand_total != calculated_total:
                    is_valid = False
                    issues.append(
                        ValidationIssue(
                            field="amount",
                            message=f"Math mismatch: Line items sum to {calculated_total}, but Grand Total is {grand_total}.",
                            severity="error"
                        )
                    )

        # Calculate final confidence penalty
        base_confidence = 1.0
        if not is_valid:
            base_confidence -= 0.4
        elif issues:
            base_confidence -= 0.15

        return ValidationResult(
            document_id=document_id,
            valid=is_valid,
            confidence=round(max(0.0, base_confidence), 2),
            issues=issues,
        )