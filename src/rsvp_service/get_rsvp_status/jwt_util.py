import os

import boto3
import jwt


class AuthenticationError(Exception):
    pass


_secretsmanager_client = boto3.client("secretsmanager")
_jwt_secret_cache = None


def _extract_token(headers):
    if not headers:
        raise AuthenticationError("Missing Authorization header")

    authorization = headers.get("authorization") or headers.get("Authorization")
    if not authorization:
        raise AuthenticationError("Missing Authorization header")

    parts = authorization.strip().split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()

    return authorization.strip()


def decode_rsvp_token(headers):
    jwt_secret = _get_jwt_secret()

    token = _extract_token(headers)

    try:
        return jwt.decode(
            token,
            jwt_secret,
            algorithms=["HS256"],
            options={"require": ["exp"]},
        )
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid or expired token") from exc


def _get_jwt_secret():
    global _jwt_secret_cache

    if _jwt_secret_cache is not None:
        return _jwt_secret_cache

    jwt_secret_arn = os.getenv("JWT_SECRET_ARN")
    if not jwt_secret_arn:
        raise RuntimeError("JWT_SECRET_ARN environment variable is not set")

    response = _secretsmanager_client.get_secret_value(SecretId=jwt_secret_arn)
    secret_string = response.get("SecretString")
    if not secret_string:
        raise RuntimeError("JWT secret is empty")

    _jwt_secret_cache = secret_string
    return _jwt_secret_cache
