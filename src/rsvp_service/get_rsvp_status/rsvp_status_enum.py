from enum import StrEnum


class RsvpStatus(StrEnum):
    PENDING = "PENDING"
    ATTEND = "ATTEND"
    NOT_ATTEND = "NOT_ATTEND"
