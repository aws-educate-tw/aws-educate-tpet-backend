from enum import Enum


class RecipientSource(Enum):
    DIRECT = "DIRECT"
    SPREADSHEET = "SPREADSHEET"

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_
