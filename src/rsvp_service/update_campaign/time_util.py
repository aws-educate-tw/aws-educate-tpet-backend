import datetime

TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def get_current_utc_time() -> str:
    """
    Get the current UTC time and format it as ISO 8601.

    :return: Current UTC time in ISO 8601 format.
    """
    return datetime.datetime.now(datetime.UTC).strftime(TIME_FORMAT)


def format_time_to_iso8601(dt: datetime.datetime) -> str:
    """
    Format a datetime object as ISO 8601.

    :param dt: Datetime object.
    :return: Formatted time as ISO 8601 string.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.UTC)
    return dt.strftime(TIME_FORMAT)


def parse_iso8601_to_datetime(iso8601_str: str) -> datetime.datetime:
    """
    Parse an ISO 8601 string to a datetime object.

    :param iso8601_str: ISO 8601 formatted string.
    :return: Datetime object.
    """
    return datetime.datetime.strptime(iso8601_str, TIME_FORMAT).replace(
        tzinfo=datetime.UTC
    )


def add_hours_to_time(iso8601_str: str, hours: int) -> str:
    """
    Add a specified number of hours to an ISO 8601 time string.

    :param iso8601_str: ISO 8601 formatted string.
    :param hours: Number of hours to add.
    :return: New ISO 8601 formatted time string.
    """
    dt = parse_iso8601_to_datetime(iso8601_str)
    new_dt = dt + datetime.timedelta(hours=hours)
    return format_time_to_iso8601(new_dt)


# Example usage
if __name__ == "__main__":
    current_time = get_current_utc_time()
    print("Current UTC Time: ", current_time)

    formatted_time = format_time_to_iso8601(datetime.datetime.now(datetime.UTC))
    print("Formatted Time: ", formatted_time)

    parsed_time = parse_iso8601_to_datetime("2024-07-11T12:00:00Z")
    print("Parsed Time: ", parsed_time)

    new_time = add_hours_to_time("2024-07-11T12:00:00Z", 3)
    print("New Time: ", new_time)
