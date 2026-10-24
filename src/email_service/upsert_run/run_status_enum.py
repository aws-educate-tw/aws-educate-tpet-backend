from enum import Enum


class RunStatus(Enum):
    ACTIVE = "ACTIVE"
    SCHEDULED = "SCHEDULED"
    SENDING = "SENDING"
