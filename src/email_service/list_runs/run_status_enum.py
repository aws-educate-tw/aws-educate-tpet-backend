"""Supported statuses for email service runs."""

from enum import Enum


class RunStatus(Enum):
    """Enumeration of supported run statuses."""

    SCHEDULED = "SCHEDULED"
    CANCELED = "CANCELED"
    SENDING = "SENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    ACTIVE = "ACTIVE"
