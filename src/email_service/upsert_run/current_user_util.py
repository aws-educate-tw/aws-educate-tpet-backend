import logging
import jwt

from auth_service import AuthService

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class CurrentUserUtil:
    def __init__(self):
        self.auth_service = AuthService()
        self._current_user_info = None
        self._current_access_token = None

    def set_current_user_by_access_token(self, access_token):
        """
        Set the current logged-in user information from the access token.

        :param access_token: JWT token for authorization
        """
        try:
            self._current_access_token = access_token
            self._current_user_info = self.auth_service.get_me(
                self._current_access_token
            )
        except Exception as e:
            logger.error("Error setting current user: %s", e)
            raise

    def get_current_user_info(self) -> dict:
        """
        Get the current logged-in user information.

        :return: Dictionary containing user information
        """
        if self._current_user_info is None:
            raise ValueError("Current user not set")
        return self._current_user_info

    def get_current_user_access_token(self) -> str:
        """
        Get the current logged-in user's access token.

        :return: Access token as a string
        """
        if self._current_access_token is None:
            raise ValueError("Current user not set")
        return self._current_access_token

    def get_user_id_from_access_token(self, access_token: str) -> str:
        """
        Decode the JWT access token and extract the user_id (sub).

        :param access_token: JWT token for authorization
        :return: User ID (sub) as a string
        """
        try:
            decoded_token = jwt.decode(
                access_token, options={"verify_signature": False}
            )
            user_id = decoded_token.get("sub")
            if not user_id:
                raise ValueError("sub not found in token")
            return user_id
        except jwt.PyJWTError as e:
            logger.error("Error decoding access token: %s", e)
            raise


# Initialize a global instance of CurrentUserUtil
current_user_util = CurrentUserUtil()
