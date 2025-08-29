"""
This module defines an enumeration for different run types,
such as WEBHOOK and EMAIL, for use in email service runs.
"""

from enum import Enum


class RunType(Enum):
    """
    Enumeration of supported run types.

    Attributes:
        WEBHOOK: Represents a run type for webhook-based email sending.
        EMAIL: Represents a run type for direct email sending.
    """

    WEBHOOK = "WEBHOOK"
    EMAIL = "EMAIL"
