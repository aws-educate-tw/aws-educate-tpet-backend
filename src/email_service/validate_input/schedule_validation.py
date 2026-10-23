import datetime
import re
from typing import Any

from error_code_enum import ValidationErrorCode
from run_type_enum import RunType
from time_util import get_current_utc_time, parse_iso8601_to_datetime
from validation_exceptions import ValidationErrorCollector

MINIMUM_SCHEDULE_LEAD_MINUTES = 10
MINIMUM_SCHEDULE_LEAD_TIME = datetime.timedelta(minutes=MINIMUM_SCHEDULE_LEAD_MINUTES)
ISO8601_UTC_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def is_valid_iso8601_utc(value: Any) -> bool:
    """Return whether value uses the required ISO 8601 UTC format."""
    if not isinstance(value, str) or not ISO8601_UTC_PATTERN.fullmatch(value):
        return False

    try:
        parse_iso8601_to_datetime(value)
        return True
    except ValueError:
        return False


def validate_scheduled_at(
    scheduled_at: Any,
    run_type: str,
    registration_deadline: Any,
    error_collector: ValidationErrorCollector,
    current_time: datetime.datetime | None = None,
) -> None:
    """Validate an optional scheduled send time."""
    if scheduled_at is None:
        return

    details = {"scheduled_at": scheduled_at}

    if run_type == RunType.WEBHOOK.value:
        error_collector.add_error(
            message="scheduled_at is not allowed for WEBHOOK run_type",
            error_code=ValidationErrorCode.SCHEDULED_AT_NOT_ALLOWED_FOR_WEBHOOK,
            details=details,
        )
        return

    if not is_valid_iso8601_utc(scheduled_at):
        error_collector.add_error(
            message="scheduled_at must use ISO 8601 UTC format YYYY-MM-DDTHH:MM:SSZ",
            error_code=ValidationErrorCode.INVALID_SCHEDULED_AT,
            details=details,
        )
        return

    scheduled_dt = parse_iso8601_to_datetime(scheduled_at)
    now = current_time or parse_iso8601_to_datetime(get_current_utc_time())

    if scheduled_dt <= now:
        error_collector.add_error(
            message="scheduled_at must be in the future",
            error_code=ValidationErrorCode.SCHEDULED_AT_PASSED,
            details=details,
        )
        return

    if scheduled_dt < now + MINIMUM_SCHEDULE_LEAD_TIME:
        error_collector.add_error(
            message=(
                f"scheduled_at must be at least {MINIMUM_SCHEDULE_LEAD_MINUTES} "
                "minutes in the future"
            ),
            error_code=ValidationErrorCode.SCHEDULED_AT_TOO_SOON,
            details=details,
        )
        return

    if (
        run_type == RunType.RSVP.value
        and is_valid_iso8601_utc(registration_deadline)
        and scheduled_dt > parse_iso8601_to_datetime(registration_deadline)
    ):
        error_collector.add_error(
            message="scheduled_at must not be later than registration_deadline",
            error_code=ValidationErrorCode.SCHEDULED_AT_AFTER_REGISTRATION_DEADLINE,
            details={
                **details,
                "registration_deadline": registration_deadline,
            },
        )
