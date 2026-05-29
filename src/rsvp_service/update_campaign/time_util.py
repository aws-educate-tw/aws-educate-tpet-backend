import datetime

TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

def get_current_utc_time() -> str:
    """
    Get the current UTC time and format it as ISO 8601.
    """
    return datetime.datetime.now(datetime.UTC).strftime(TIME_FORMAT)

if __name__ == "__main__":
    current_time = get_current_utc_time()
    print("Current UTC Time: ", current_time)