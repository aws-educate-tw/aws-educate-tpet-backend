"""
This module contains utility functions that are used by the trigger_webhook module.
"""

import json
from decimal import Decimal

from aws_lambda_powertools.utilities.parameters import get_secret
from config import Config
from Crypto.Cipher import AES


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle Decimal types"""

    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


def get_access_token(service_account: str) -> str:
    # force_fetch=True: access tokens are rotated by auth_service; never serve a stale cached value
    secret = get_secret(
        f"aws-educate-tpet/{Config.ENVIRONMENT}/service-accounts/{service_account}/access-token",
        transform="json",
        force_fetch=True,
    )
    return secret["access_token"]


class CryptoHandler:
    """Class to handle encryption and decryption operations"""

    @staticmethod
    def decrypt_data(encrypted_data: bytes, hash_key: str, iv_key: str) -> str:
        """Decrypt the data using AES encryption"""
        cipher = AES.new(hash_key.encode("utf-8"), AES.MODE_CBC, iv_key.encode("utf-8"))
        decrypted_data = cipher.decrypt(encrypted_data).rstrip(b"\0")
        decrypted_str = decrypted_data.decode("utf-8")

        last_brace_index = decrypted_str.rfind("}")
        if last_brace_index == -1:
            raise ValueError("Invalid JSON data")

        return decrypted_str[: last_brace_index + 1]
