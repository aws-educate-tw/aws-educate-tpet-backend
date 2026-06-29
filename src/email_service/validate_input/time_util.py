import datetime

TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
RDS_DATA_API_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


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
    Safely parse an ISO 8601 string into a timezone-aware UTC datetime object.

    Accepts strings ending in "Z", strings with an explicit numeric offset
    (e.g. "+08:00"), and strings with no offset at all. A string with no
    offset is assumed to represent UTC (it is NOT interpreted as local time).

    :param iso8601_str: ISO 8601 formatted string.
    :return: Timezone-aware datetime object in UTC.
    :raises ValueError: If the string is not a valid ISO 8601 datetime.
    :raises AttributeError: If iso8601_str is not a string (e.g. None).
    """
    dt = datetime.datetime.fromisoformat(iso8601_str.replace("Z", "+00:00"))

    if dt.tzinfo is None:
        # No offset present in the original string — assume UTC explicitly,
        # rather than letting astimezone() silently use the server's local tz.
        dt = dt.replace(tzinfo=datetime.UTC)
    else:
        dt = dt.astimezone(datetime.UTC)

    return dt


def format_datetime_for_rds(dt: datetime.datetime) -> str:
    """
    Format a datetime object for RDS Data API (YYYY-MM-DD HH:MM:SS).

    :param dt: Datetime object.
    :return: Formatted time as string.
    """
    # RDS Data API expects timestamp without timezone information in the string,
    # but it should represent UTC.
    return dt.strftime(RDS_DATA_API_TIMESTAMP_FORMAT)


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
