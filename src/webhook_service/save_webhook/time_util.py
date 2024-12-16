import datetime

TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def get_current_utc_time() -> str:
    """
    Get the current UTC time and format it as ISO 8601.

    :return: Current UTC time in ISO 8601 format.
    """
    return datetime.datetime.now(datetime.timezone.utc).strftime(TIME_FORMAT)


def format_time_to_iso8601(dt: datetime.datetime) -> str:
    """
    Format a datetime object as ISO 8601.

    :param dt: Datetime object.
    :return: Formatted time as ISO 8601 string.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.strftime(TIME_FORMAT)


def parse_iso8601_to_datetime(iso8601_str: str) -> datetime.datetime:
    """
    Parse an ISO 8601 string to a datetime object.

    :param iso8601_str: ISO 8601 formatted string.
    :return: Datetime object.
    """
    return datetime.datetime.strptime(iso8601_str, TIME_FORMAT).replace(
        tzinfo=datetime.timezone.utc
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


def get_previous_month(current_month: str) -> str:
    """
    Get the previous month in ISO 8601 format (YYYY-MM).

    :param current_month: The current month in ISO 8601 format (YYYY-MM).
    :return: The previous month in ISO 8601 format (YYYY-MM).
    """
    year, month = map(int, current_month.split("-"))
    if month == 1:
        year -= 1
        month = 12
    else:
        month -= 1
    return f"{year:04d}-{month:02d}"


def get_previous_year(current_year: str) -> str:
    """
    Get the previous year in ISO 8601 format (YYYY).

    :param current_year: The current year in ISO 8601 format (YYYY).
    :return: The previous year in ISO 8601 format (YYYY).
    """
    year = int(current_year)
    return f"{year - 1:04d}"
