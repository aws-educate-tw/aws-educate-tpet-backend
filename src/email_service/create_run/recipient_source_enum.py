"""
This module defines an enumeration for different recipient sources,
such as DIRECT and SPREADSHEET, for use in email service runs.
"""

from enum import Enum


class RecipientSource(Enum):
    """
    Enumeration of supported recipient sources.

    Attributes:
        DIRECT: Represents recipients directly specified in the request.
        SPREADSHEET: Represents recipients sourced from a spreadsheet file.
    """

    DIRECT = "DIRECT"
    SPREADSHEET = "SPREADSHEET"
