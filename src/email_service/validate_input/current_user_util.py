import logging

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


# Initialize a global instance of CurrentUserUtil
current_user_util = CurrentUserUtil()
