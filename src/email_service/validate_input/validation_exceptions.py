"""Validation exception classes for error handling and collection."""

from typing import Any

from error_code_enum import ValidationErrorCode


class ValidationError(Exception):
    """Custom exception for validation errors."""

    def __init__(
        self,
        message: str,
        error_code: ValidationErrorCode | str = ValidationErrorCode.VALIDATION_ERROR,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.error_code = error_code.value if isinstance(error_code, ValidationErrorCode) else error_code
        self.details = details
        super().__init__(self.message)


class ValidationErrorCollector:
    """Collects multiple validation errors before raising them all at once."""

    def __init__(self):
        self.errors: list[dict[str, Any]] = []

    def add_error(
        self,
        message: str,
        error_code: ValidationErrorCode | str = ValidationErrorCode.VALIDATION_ERROR,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Add a validation error to the collection."""
        error_entry = {
            "message": message,
            "error_code": error_code.value if isinstance(error_code, ValidationErrorCode) else error_code,
        }
        if details:
            error_entry["details"] = details
        self.errors.append(error_entry)

    def has_errors(self) -> bool:
        """Check if any errors have been collected."""
        return len(self.errors) > 0

    def raise_if_has_errors(self) -> None:
        """Raise a ValidationError if any errors have been collected."""
        if self.has_errors():
            raise ValidationError(
                message=f"Found {len(self.errors)} validation error(s)",
                error_code=ValidationErrorCode.VALIDATION_ERRORS,
                details={"errors": self.errors, "error_count": len(self.errors)},
            )