"""
This module defines an enumeration for different webhook types,
such as SurveyCake and Slack, for use in integrations.
"""

from enum import Enum


class WebhookType(Enum):
    """
    Enumeration of supported webhook types.

    Attributes:
        SURVEYCAKE: Represents a webhook for SurveyCake.
        SLACK: Represents a webhook for Slack.
    """
    SURVEYCAKE = "surveycake"
    SLACK = "slack"
