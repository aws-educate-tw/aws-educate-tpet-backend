import datetime
import logging
import os
import time
from collections.abc import Generator
from typing import Any

import pytest
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Environment variables
TESTMAIL_APP_API_KEY = os.getenv("TESTMAIL_APP_API_KEY")
TESTMAIL_APP_NAMESPACE = os.getenv("TESTMAIL_APP_NAMESPACE")
TEST_ACCOUNT = os.getenv("TEST_ACCOUNT")
TEST_PASSWORD = os.getenv("TEST_PASSWORD")
SEND_EMAIL_API_ENDPOINT = os.getenv("SEND_EMAIL_API_ENDPOINT")
LOGIN_API_ENDPOINT = os.getenv("LOGIN_API_ENDPOINT")
TEMPLATE_FILE_ID = os.getenv("TEMPLATE_FILE_ID")
ATTACHMENT_FILE_IDS = os.getenv("ATTACHMENT_FILE_IDS", "").split(",")

# Test parameters
MAX_WAIT_TIME = 120
WAIT_INTERVAL = 3
SEND_EMAIL_COUNT = 5  # Number of emails to send
TESTMAIL_APP_API_ENDPOINT = "https://api.testmail.app/api/json"
TESTMAIL_APP_TAG = "load-test-" + datetime.datetime.now(datetime.UTC).strftime(
    "%Y%m%dT%H%M%SZ"
)  # Generate a unique test tag using ISO 8601 format
RECIPIENT_EMAIL = f"{TESTMAIL_APP_NAMESPACE}.{TESTMAIL_APP_TAG}@inbox.testmail.app"


class TestSendEmails:
    def get_email_count_from_testmail_app_api(
        self, tag: str
    ) -> tuple[int, requests.Response]:
        """
        Retrieves the count of emails from testmail.app API for a specific tag.

        Args:
            tag: The tag to filter emails by.

        Returns:
            Tuple containing email count and the API response.
        """
        params = {
            "apikey": TESTMAIL_APP_API_KEY,
            "namespace": TESTMAIL_APP_NAMESPACE,
            "tag": tag,
            "timestamp_from": self.test_start_time,
        }

        response = requests.get(TESTMAIL_APP_API_ENDPOINT, params=params, timeout=30)
        if response.status_code == 200:
            count = response.json()["count"]
            return count, response
        return 0, response

    def send_email_request(self, index: int) -> dict[str, Any]:
        """
        Sends a single email request to the email service.

        Args:
            index: Current email index for logging purposes.

        Returns:
            API response data as a dictionary.

        Raises:
            AssertionError: If email sending fails.
        """
        payload = {
            "recipient_source": "DIRECT",
            "subject": "【Load Test】" + TESTMAIL_APP_TAG,
            "display_name": "Load Test - testmail app",
            "template_file_id": TEMPLATE_FILE_ID,
            "is_generate_certificate": True,
            "reply_to": RECIPIENT_EMAIL,
            "sender_local_part": TESTMAIL_APP_TAG,
            "recipients": [
                {
                    "email": RECIPIENT_EMAIL,
                    "template_variables": {
                        "Name": "John陳",
                        "Certificate Text": "In recognition of your participation in the AWS Educate Program - Certification Training on July 5, 2024.",
                    },
                },
            ],
            "attachment_file_ids": ATTACHMENT_FILE_IDS,
            "bcc": [],
            "cc": [],
        }

        response = requests.post(
            SEND_EMAIL_API_ENDPOINT, headers=self.headers, json=payload, timeout=30
        )

        if response.status_code != 202:
            logger.error(
                "Failed to send email %s. Status code: %s", index, response.status_code
            )
            raise AssertionError(
                f"Failed to send email {index}. Status code: {response.status_code}"
            )

        return response.json()

    @pytest.fixture(autouse=True)
    def setup(self) -> Generator[None, None, None]:
        """
        Setup fixture that runs before each test.
        Handles authentication and initializes test parameters.
        """
        # Initialize test attributes
        self.test_start_time = int(time.time() * 1000)  # Convert to milliseconds
        self.access_token = None
        self.headers = None

        # Authenticate and get access token
        login_data = {
            "account": TEST_ACCOUNT,
            "password": TEST_PASSWORD,
        }

        response = requests.post(LOGIN_API_ENDPOINT, json=login_data, timeout=30)

        # Check authentication success
        if response.status_code != 200:
            logger.error("Login failed with status code: %s", response.status_code)
            raise AssertionError(
                f"Login failed with status code: {response.status_code}"
            )

        self.access_token = response.json()["access_token"]
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        logger.info("Login successful, token retrieved.")
        yield

    def test_send_emails(self):
        """
        Tests the email sending functionality by:
        1. Sending multiple test emails
        2. Monitoring email delivery
        3. Verifying all emails are received.
        """
        # Track sent emails
        run_ids = []

        # Test info
        logger.info("Test tag: %s", TESTMAIL_APP_TAG)

        # Send batch of emails
        for i in range(SEND_EMAIL_COUNT):
            response = self.send_email_request(i)
            run_ids.append(response["run_id"])
            logger.info("Sent email %s of %s", i + 1, SEND_EMAIL_COUNT)

        # Monitor email delivery
        elapsed_time = 0
        while elapsed_time < MAX_WAIT_TIME:
            count, response = self.get_email_count_from_testmail_app_api(
                TESTMAIL_APP_TAG
            )

            # Verify API response
            assert response.status_code == 200, (
                "Failed to get email count from testmail.app"
            )
            logger.info("Current email count: %s", count)

            if count >= SEND_EMAIL_COUNT:
                logger.info("All emails received successfully!")
                break

            time.sleep(WAIT_INTERVAL)
            elapsed_time += WAIT_INTERVAL

        # Final verification
        final_count, response = self.get_email_count_from_testmail_app_api(
            TESTMAIL_APP_TAG
        )
        assert response.status_code == 200, "Failed to get final email count"
        assert final_count == SEND_EMAIL_COUNT, (
            f"Email delivery incomplete. Expected: {SEND_EMAIL_COUNT}, Received: {final_count}"
        )


if __name__ == "__main__":
    # Generate timestamp for the report file
    timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
    report_file = f"./pytest-report_{timestamp}.html"

    # Run tests and generate HTML report
    pytest.main([__file__, "-v", f"--html={report_file}", "--self-contained-html"])
