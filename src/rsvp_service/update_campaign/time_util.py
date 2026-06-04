import datetime

TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

def get_current_utc_time() -> str:
    """
    Get the current UTC time and format it as ISO 8601.
    """
    return datetime.datetime.now(datetime.UTC).strftime(TIME_FORMAT)

def parse_iso8601_to_datetime(iso_str: str) -> datetime.datetime:
    """
    Parse an ISO 8601 string to a datetime object.
    """
    try:
        return datetime.datetime.strptime(iso_str, TIME_FORMAT).replace(tzinfo=datetime.UTC)
    except ValueError:
        return datetime.datetime.fromisoformat(iso_str.replace('Z', '+00:00'))


if __name__ == "__main__":
    current_time = get_current_utc_time()
    print("Current UTC Time: ", current_time)