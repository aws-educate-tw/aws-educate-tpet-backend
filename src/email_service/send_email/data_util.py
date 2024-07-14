import math
from decimal import Decimal


def convert_float_to_decimal(data):
    if isinstance(data, list):
        return [convert_float_to_decimal(item) for item in data]
    elif isinstance(data, dict):
        return {key: convert_float_to_decimal(value) for key, value in data.items()}
    elif isinstance(data, float):
        if math.isinf(data) or math.isnan(data):
            return None
        return Decimal(str(data))
    return data
