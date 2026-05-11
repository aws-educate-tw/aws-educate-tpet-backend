from enum import Enum


class RunType(Enum):
    WEBHOOK = "WEBHOOK"
    EMAIL = "EMAIL"
    RSVP = "RSVP"

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_
