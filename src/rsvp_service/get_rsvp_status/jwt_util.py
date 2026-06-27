import os

import jwt
from aws_lambda_powertools.utilities.parameters import get_secret


class AuthenticationError(Exception):
    pass


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
    jwt_secret_arn = os.getenv("JWT_SECRET_ARN")
    if not jwt_secret_arn:
        raise RuntimeError("JWT_SECRET_ARN environment variable is not set")

    secret = get_secret(jwt_secret_arn)
    if not secret:
        raise RuntimeError("JWT secret is empty")

    return secret
