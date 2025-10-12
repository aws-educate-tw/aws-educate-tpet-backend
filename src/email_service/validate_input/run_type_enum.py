from enum import Enum


class RunType(Enum):
    WEBHOOK = "WEBHOOK"
    EMAIL = "EMAIL"

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_
