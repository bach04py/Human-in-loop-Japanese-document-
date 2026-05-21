from app.schemas import ValidationIssue, ValidationResult


class ValidationService:
    """Week 1 baseline validation rules for extracted fields."""

    async def validate(
        self, document_id: str, extracted_data: dict | None = None
    ) -> ValidationResult:
        issues: list[ValidationIssue] = []
        data = extracted_data or {}

        if data and not data.get("invoice_id"):
            issues.append(
                ValidationIssue(
                    field="invoice_id",
                    message="Missing invoice identifier.",
                    severity="error",
                )
            )

        return ValidationResult(
            document_id=document_id,
            valid=not any(issue.severity == "error" for issue in issues),
            confidence=0.86 if issues else 0.93,
            issues=issues,
        )
