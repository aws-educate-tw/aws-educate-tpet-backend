from enum import StrEnum


class EmailStatus(StrEnum):
    PENDING = "PENDING"
    SCHEDULED = "SCHEDULED"
    CANCELED = "CANCELED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
