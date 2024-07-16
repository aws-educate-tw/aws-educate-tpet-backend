import json
import logging
import os
import time

import requests
from jose import jwt
from jose.exceptions import JWTError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

COGNITO_POOL_ID = "us-west-2_cvOUHeHKh"
COGNITO_CLIENT_ID = "4hu6irac6o43n9ug67o6a9vahk"
AWS_REGION = "us-west-2"
COGNITO_ISSUER = f"https://cognito-idp.{AWS_REGION}.amazonaws.com/{COGNITO_POOL_ID}"
JWKS_URL = f"{COGNITO_ISSUER}/.well-known/jwks.json"

# 全局變量，用於緩存 JWKS
JWKS = None


def get_jwks():
    global JWKS
    if JWKS is None:
        retries = 3
        for i in range(retries):
            try:
                response = requests.get(JWKS_URL)
                response.raise_for_status()
                JWKS = response.json()
                logger.info("JWKS successfully retrieved")
                return JWKS
            except requests.RequestException as e:
                logger.error(f"Error fetching JWKS (attempt {i+1}/{retries}): {e}")
                if i < retries - 1:  # 如果不是最後一次嘗試，則等待後重試
                    time.sleep(1)
        logger.error("Failed to retrieve JWKS after multiple attempts")
        return None
    return JWKS


def get_access_token_from_cookies(cookies_list):
    for cookie in cookies_list:
        if cookie.startswith("accessToken="):
            return cookie.split("accessToken=")[1]
    return None


def verify_jwt(token):
    try:
        jwks = get_jwks()
        if not jwks or "keys" not in jwks:
            logger.error("Invalid JWKS structure")
            return False

        headers = jwt.get_unverified_headers(token)
        kid = headers.get("kid")

        key_index = None
        for i, key in enumerate(jwks["keys"]):
            if key["kid"] == kid:
                key_index = i
                break

        if key_index is None:
            logger.error("Public key not found in JWKS")
            return False

        public_key = jwks["keys"][key_index]

        decoded_token = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=COGNITO_CLIENT_ID,
            issuer=COGNITO_ISSUER,
        )
        logger.info("JWT successfully verified")
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
