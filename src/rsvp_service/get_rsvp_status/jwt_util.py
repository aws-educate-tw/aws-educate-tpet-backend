import os

import jwt


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
    jwt_secret = os.getenv("JWT_SECRET")
    if not jwt_secret:
        raise RuntimeError("JWT_SECRET environment variable is not set")

    token = _extract_token(headers)

    try:
        return jwt.decode(token, jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid or expired token") from exc
