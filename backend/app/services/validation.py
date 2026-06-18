from app.schemas import ValidationIssue, ValidationResult

# Friendly names for the per-type identifier field.
ID_LABELS = {
    "invoice_id": "invoice number",
    "contract_id": "contract number",
    "bill_id": "account / bill number",
    "document_id": "document number",
}


class ValidationService:
    """Validation Agent: type-aware mathematical and logical checks."""

    async def validate(
            self, document_id: str, extracted_data: dict | None = None
    ) -> ValidationResult:
        issues: list[ValidationIssue] = []
        data = extracted_data or {}
        is_valid = True

        def field_value(key):
            # Extraction may emit a flat value (baseline / flattened LLM output)
            # or a nested {"value": ...} dict (empty-result blueprint). Accept both.
            raw = data.get(key)
            if isinstance(raw, dict):
                return raw.get("value")
            return raw

        # Identifier Check (type-aware: invoice_id / contract_id / bill_id / document_id)
        id_key = next((k for k in data if k.endswith("_id")), None)
        if id_key and not field_value(id_key):
            issues.append(
                ValidationIssue(
                    field=id_key,
                    message=f"Missing {ID_LABELS.get(id_key, 'identifier')}.",
                    severity="warning",
                )
            )

        # Amount / math checks apply only to types that carry an amount field
        # (invoice, contract, bill). General documents skip this entirely.
        if "amount" not in data:
            grand_total = None
        else:
            grand_total = field_value("amount")

        if "amount" in data and grand_total is None:
            is_valid = False
            issues.append(
                ValidationIssue(
                    field="amount",
                    message="Grand total amount is missing. Cannot verify document math.",
                    severity="error",
                )
            )
        elif grand_total is not None:
            # Mathematical Check: Line Items == Grand Total
            line_items = data.get("line_items", [])
            calculated_total = 0.0

            for item in line_items:
                item_total = item.get("total")
                if item_total is not None:
                    try:
                        calculated_total += float(item_total)
                    except ValueError:
                        pass  # Ignore if LLM returned a weird string instead of a number

            # Only run the math check if there are actually line items to sum
            if calculated_total > 0:
                try:
                    if float(grand_total) != calculated_total:
                        is_valid = False
                        issues.append(
                            ValidationIssue(
                                field="amount",
                                message=f"Math mismatch: Line items sum to {calculated_total}, but Grand Total is {grand_total}.",
                                severity="error"
                            )
                        )
                except ValueError:
                    is_valid = False
                    issues.append(
                        ValidationIssue(
                            field="amount",
                            message="Grand total is not a valid number.",
                            severity="error"
                        )
                    )

        # Dynamic Confidence Penalty
        base_confidence = 1.0
        if not is_valid:
            base_confidence -= 0.4  # Huge penalty for failing math/missing total
        elif issues:
            base_confidence -= 0.1  # Small penalty for warnings

        return ValidationResult(
            document_id=document_id,
            valid=is_valid,
            confidence=round(max(0.0, base_confidence), 2),  # Prevent negative confidence
            issues=issues,
        )