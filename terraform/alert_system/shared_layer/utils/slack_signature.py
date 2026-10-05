import hashlib
import hmac
import time

DEFAULT_MAX_REQUEST_AGE_SECONDS = 60 * 5


def get_header_case_insensitive(headers, header_name):
    """Get a header value from a dict without assuming key case."""
    if not headers:
        return None

    for key, value in headers.items():
        if key.lower() == header_name.lower():
            return value

    return None


def verify_slack_request_signature(
    headers,
    raw_body,
    signing_secret,
    logger,
    max_request_age_seconds=DEFAULT_MAX_REQUEST_AGE_SECONDS,
):
    """Validate Slack request signature and timestamp."""
    timestamp = get_header_case_insensitive(headers, "X-Slack-Request-Timestamp")
    slack_signature = get_header_case_insensitive(headers, "X-Slack-Signature")

    if not timestamp or not slack_signature:
        logger.warning("Missing Slack signature headers")
        return False

    try:
        timestamp_int = int(timestamp)
    except ValueError:
        logger.warning("Invalid Slack timestamp header")
        return False

    if abs(int(time.time()) - timestamp_int) > max_request_age_seconds:
        logger.warning("Slack request timestamp is too old or too far in the future")
        return False

    sig_basestring = f"v0:{timestamp}:{raw_body}"
    computed_signature = (
        "v0="
        + hmac.new(
            signing_secret.encode("utf-8"),
            sig_basestring.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
    )

    return hmac.compare_digest(computed_signature, slack_signature)
