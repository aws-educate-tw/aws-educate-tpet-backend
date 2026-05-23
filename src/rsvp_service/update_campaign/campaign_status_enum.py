"""
This module defines an enumeration for different campaign statuses,
such as UPCOMING, ACTIVE, and COMPLETED, for use in the RSVP service.
"""

from enum import Enum


class CampaignStatus(Enum):
    """
    Enumeration of supported campaign statuses.

    Attributes:
        UPCOMING: Represents a campaign that has not yet started.
        ACTIVE: Represents a campaign that is currently ongoing.
        COMPLETED: Represents a campaign that has already ended.
    """

    UPCOMING = "UPCOMING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"