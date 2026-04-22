"""
JWT token utility for generating RSVP participant tokens.
"""

import logging
import os
from datetime import UTC, datetime

import jwt

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Get JWT secret from environment variable
JWT_SECRET = os.getenv("JWT_SECRET")


def generate_rsvp_token(
    run_id: str,
    participant_id: str,
    email_id: str,
    campaign_id: str,
    name: str,
    expiration_datetime: str | None = None,
) -> str:
    """
    Generate a JWT token for RSVP participant.

    Args:
        run_id: Run ID (Partition Key)
        participant_id: Participant ID (Sort Key / Primary Key)
        email_id: Original email/spreadsheet row ID
        campaign_id: Campaign ID
        name: Participant name
        expiration_datetime: Token expiration datetime (ISO 8601 format)

    Returns:
        JWT token string
    """
    try:
        # Get current timestamp
        now = datetime.now(UTC)
        iat = int(now.timestamp())

        if not expiration_datetime:
            raise ValueError("expiration_datetime is required for RSVP token generation")

        exp_dt = datetime.fromisoformat(
            expiration_datetime.replace("Z", "+00:00")
        )
        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=UTC)
        else:
            exp_dt = exp_dt.astimezone(UTC)
        exp = int(exp_dt.timestamp())

        payload = {
            "run_id": run_id,
            "participant_id": participant_id,
            "email_id": email_id,
            "campaign_id": campaign_id,
            "name": name,
            "iat": iat,
            "exp": exp,
        }

        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

        logger.info(
            "Generated JWT token for participant_id=%s, run_id=%s",
            participant_id,
            run_id,
        )

        return token

    except Exception as e:
        logger.error(
            "Error generating JWT token for participant_id=%s: %s", participant_id, e
        )
        raise
