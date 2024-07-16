import json
import logging
import os

import requests
from jose import jwt
from jose.exceptions import JWTError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

COGNITO_POOL_ID = "us-west-2_bDwjqc0Gv"
COGNITO_CLIENT_ID = "4hu6irac6o43n9ug67o6a9vahk"
AWS_REGION = "us-west-2"
COGNITO_ISSUER = f"https://cognito-idp.{AWS_REGION}.amazonaws.com/{COGNITO_POOL_ID}"

# Cache the JWKS keys
JWKS_URL = f"{COGNITO_ISSUER}/.well-known/jwks.json"
JWKS = requests.get(JWKS_URL).json()


def get_access_token_from_cookies(cookies_list):
    for cookie in cookies_list:
        if cookie.startswith("accessToken="):
            return cookie.split("accessToken=")[1]
    return None


def verify_jwt(token):
    try:
        headers = jwt.get_unverified_headers(token)
        kid = headers.get("kid")

        key_index = None
        for i, key in enumerate(JWKS["keys"]):
            if key["kid"] == kid:
                key_index = i
                break

        if key_index is None:
            logger.error("Public key not found in JWKS")
            return False

        public_key = JWKS["keys"][key_index]

        decoded_token = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=COGNITO_CLIENT_ID,
            issuer=COGNITO_ISSUER,
        )
        return decoded_token
    except JWTError as e:
        logger.error(f"JWT verification error: {e}")
        return False


def lambda_handler(event, context):
    if "cookies" not in event or not event["cookies"]:
        logger.info("No cookies found")
        return {"isAuthorized": False}

    cookies_list = event["cookies"]
    access_token = get_access_token_from_cookies(cookies_list)
    if access_token is None:
        logger.info("Access token not found in cookies")
        return {"isAuthorized": False}

    if verify_jwt(access_token):
        return {"isAuthorized": True}
    else:
        return {"isAuthorized": False}
