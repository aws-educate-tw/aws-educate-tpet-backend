"""
This module defines an enumeration for different run types,
such as RSVP and WEBHOOK, for use in email service runs.
"""

from enum import Enum


class RunType(Enum):
    """
    Enumeration of supported run types.

    Attributes:
        RSVP: Represents a run type for RSVP email sending.
        WEBHOOK: Represents a run type for webhook-based email sending.
    """

    RSVP = "RSVP"
    WEBHOOK = "WEBHOOK"
