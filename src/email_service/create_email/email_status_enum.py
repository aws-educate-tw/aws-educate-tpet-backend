from enum import StrEnum


class EmailStatus(StrEnum):
    SCHEDULED = "SCHEDULED"
    CANCELED = "CANCELED"
    SENDING = "SENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    ACTIVE = "ACTIVE"
    PENDING = "PENDING"
