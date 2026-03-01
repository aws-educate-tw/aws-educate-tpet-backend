from enum import Enum

class CloudWatchAlarmState(str, Enum):
    ALARM = "ALARM"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    OK = "OK"


class IncidentState(str, Enum):
    ALARM = "ALARM"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
