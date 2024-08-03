import base64
import json
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def decode_key(encoded_key: str) -> dict[str, str]:
    """Decode a base64 encoded key into a dictionary."""
    try:
        decoded_key = json.loads(base64.b64decode(encoded_key).decode("utf-8"))
        return decoded_key
    except (json.JSONDecodeError, base64.binascii.Error) as e:
        logger.error("Invalid key format: %s", e)
        raise ValueError(
            "Invalid key format. It must be a valid base64 encoded JSON string."
        ) from e


def encode_key(decoded_key: dict[str, str]) -> str:
    """Encode a dictionary into a base64 encoded string."""
    encoded_key = base64.b64encode(json.dumps(decoded_key).encode("utf-8")).decode(
        "utf-8"
    )
    return encoded_key
