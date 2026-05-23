import datetime

TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def get_current_utc_time() -> str:
    """
    Get the current UTC time and format it as ISO 8601.

    :return: Current UTC time in ISO 8601 format.
    """
    return datetime.datetime.now(datetime.UTC).strftime(TIME_FORMAT)


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

if __name__ == "__main__":
    current_time = get_current_utc_time()
    print("Current UTC Time: ", current_time)

    formatted_time = format_time_to_iso8601(datetime.datetime.now(datetime.UTC))
    print("Formatted Time: ", formatted_time)

    parsed_time = parse_iso8601_to_datetime("2024-07-11T12:00:00Z")
    print("Parsed Time: ", parsed_time)

    new_time = add_hours_to_time("2024-07-11T12:00:00Z", 3)
    print("New Time: ", new_time)
