import json
import logging
import os
import time

import requests
from jose import jwk, jwt
from jose.exceptions import JWTError
from jose.utils import base64url_decode

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")
COGNITO_CLIENT_ID = os.getenv("COGNITO_CLIENT_ID")
CURRENT_AWS_REGION = os.getenv("CURRENT_AWS_REGION")
COGNITO_ISSUER = (
    f"https://cognito-idp.{CURRENT_AWS_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}"
)
JWKS_URL = f"{COGNITO_ISSUER}/.well-known/jwks.json"

# Global variable for caching JWKS
JWKS = None


def get_jwks():
    """
    Retrieve and cache JSON Web Key Set (JWKS) from the JWKS_URL.

    Returns:
        dict: JWKS if successfully retrieved, else None.
    """
    global JWKS
    if JWKS is None:
        retries = 3
        for i in range(retries):
            try:
                response = requests.get(JWKS_URL, timeout=20)
                response.raise_for_status()
                JWKS = response.json()
                logger.info("JWKS successfully retrieved")
                return JWKS
            except requests.RequestException as e:
                logger.error(
                    "Error fetching JWKS (attempt %d/%d): %s",
                    i + 1,
                    retries,
                    e,
                    exc_info=True,
                )
                if i < retries - 1:  # If not the last attempt, wait before retrying
                    time.sleep(1)
        logger.error("Failed to retrieve JWKS after multiple attempts")
        return None
    return JWKS


def verify_jwt(token):
    """
    Verify the JWT token.

    Args:
        token (str): JWT token to be verified.

    Returns:
        dict: Decoded token if verification is successful, else False.
    """
    try:
        jwks = get_jwks()
        if not jwks or "keys" not in jwks:
            logger.error("Invalid JWKS structure")
            return False

        # Decode the header without verifying the signature
        header_data = token.split(".")[0]
        header = json.loads(
            base64url_decode(header_data.encode("utf-8")).decode("utf-8")
        )
        kid = header.get("kid")

        if not kid:
            logger.error("No 'kid' found in token headers")
            return False

        # Find the matching public key
        public_key = None
        for key in jwks["keys"]:
            if key["kid"] == kid:
                public_key = jwk.construct(key)
                break

        if not public_key:
            logger.error("Public key not found in JWKS")
            return False

        # Verify the token
        decoded_token = jwt.decode(
            token,
            public_key.to_pem().decode("utf-8"),
            algorithms=["RS256"],
            audience=COGNITO_CLIENT_ID,
            issuer=COGNITO_ISSUER,
        )
        logger.info("JWT successfully verified")
        return decoded_token
    except JWTError as e:
        logger.error("JWT verification error: %s", e)
        return False
    except Exception as e:
        logger.error("Unexpected error during JWT verification: %s", e)
        return False


def lambda_handler(event, context):
    """
    AWS Lambda handler function.

    Args:
        event (dict): Event data.
        context (dict): Context data.

    Returns:
        dict: Authorization result.
    """
    headers = event.get("headers", {})
    authorization_header = headers.get("authorization", "")

    logger.info("Received Authorization header: %s", authorization_header)

    if not authorization_header.startswith("Bearer "):
        logger.info("Authorization header missing or does not start with 'Bearer '")
        return {"isAuthorized": False}

    access_token = authorization_header[len("Bearer ") :]

    if not access_token:
        logger.info("Access token not found in Authorization header")
        return {"isAuthorized": False}

    if verify_jwt(access_token):
        return {"isAuthorized": True}
    else:
        return {"isAuthorized": False}
