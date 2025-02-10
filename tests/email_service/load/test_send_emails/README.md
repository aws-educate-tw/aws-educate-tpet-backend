# Load Testing for sending emails

This repository provides a **load testing script** for the **Email Service** using `pytest` and `pytest-html`. The script sends multiple emails and verifies their successful delivery.

## Prerequisites

- **Python 3.11+**
- **Poetry** (for dependency management)
- **Environment variables** stored in a `.env` file (to avoid hardcoding sensitive information)

## 1. Install Dependencies

This project uses `poetry` for dependency management. If you haven't installed `poetry`, follow the instructions [here](https://python-poetry.org/docs/#installation).

### 1.1 Install Poetry

```sh
pip install poetry
```

### 1.2 Install Dependencies

Run the following command in the project directory:

```sh
poetry install
```

This will install all required dependencies including:

- `pytest`
- `pytest-html`
- `requests`
- `python-dotenv`

---

## 2. Configure Environment Variables

To ensure security, sensitive information such as API keys should not be hardcoded. Instead, store them in a `.env` file.

### 2.1 Create a `.env` file

In the root directory, create a file named `.env` and add the following content:

```plaintext
TESTMAIL_APP_NAMESPACE=your_namespace
TESTMAIL_APP_API_KEY=your_api_key
TEST_ACCOUNT=your_tpet_account
TEST_PASSWORD=your_tpet_password
SEND_EMAIL_API_ENDPOINT=https://your-email-service-api.com/send-email
LOGIN_API_ENDPOINT=https://your-auth-service-api.com/login
TEMPLATE_FILE_ID=your_template_file_id
ATTACHMENT_FILE_IDS=file_id1
```

> [!IMPORTANT]
> Do **not** commit the `.env` file to version control. Add it to `.gitignore`:

---

## 3. Running the Tests

The script will:

1. **Authenticate with the email service**
2. **Send multiple emails**
3. **Monitor email delivery**
4. **Verify the expected number of emails are received**

### 3.1 Activate the Virtual Environment

Poetry creates a virtual environment. To activate it, run:

```sh
poetry shell
```

### 3.2 Execute the Tests

Run the following command:

```sh
pytest --html=report_$(date -u +'%Y%m%dT%H%M%SZ').html --self-contained-html
```

**Windows (PowerShell) version:**

```powershell
pytest --html="report_$(Get-Date -Format 'yyyy-MM-ddTHH-mm-ssZ').html" --self-contained-html
```

The script will generate an **HTML report** with a timestamped filename, e.g.:

```plaintext
report_20250209T192300Z.html
```

You can open this file in a browser to view test results.

---

## 4. Logging and Debugging

The script logs important actions using Python’s built-in `logging` module.

- Logs include:
  - Email sending attempts
  - API response statuses
  - Verification steps
- Log format:

  ```plaintext
  2024-02-10 12:34:56,789 - INFO - Sent email 1 of 5
  2024-02-10 12:34:57,001 - ERROR - Login failed with status code: 401
  ```

- If something goes wrong, check the **logs** to debug the issue.
