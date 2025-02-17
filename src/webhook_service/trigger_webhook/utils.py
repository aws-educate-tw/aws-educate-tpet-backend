import json
from decimal import Decimal

import boto3
from config import Config
from Crypto.Cipher import AES


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


class SecretsManager:
    def __init__(self):
        self.client = boto3.client("secretsmanager")

    def get_secret_path(self, service_account: str, secret_type: str) -> str:
        return f"aws-educate-tpet/{Config.ENVIRONMENT}/service-accounts/{service_account}/{secret_type}"

    def get_access_token(self, service_account: str) -> str:
        try:
            response = self.client.get_secret_value(
                SecretId=self.get_secret_path(service_account, "access-token")
            )
            return json.loads(response["SecretString"])["access_token"]
        except Exception as e:
            print(f"Failed to retrieve access token: {str(e)}")
            raise


class CryptoHandler:
    @staticmethod
    def decrypt_data(encrypted_data: bytes, hash_key: str, iv_key: str) -> str:
        cipher = AES.new(hash_key.encode("utf-8"), AES.MODE_CBC, iv_key.encode("utf-8"))
        decrypted_data = cipher.decrypt(encrypted_data).rstrip(b"\0")
        decrypted_str = decrypted_data.decode("utf-8")

        last_brace_index = decrypted_str.rfind("}")
        if last_brace_index == -1:
            raise ValueError("Invalid JSON data")

        return decrypted_str[: last_brace_index + 1]
