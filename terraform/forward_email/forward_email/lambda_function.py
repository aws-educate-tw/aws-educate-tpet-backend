import json
import logging
import os
import urllib.parse
from email import policy
from email.header import decode_header
from email.parser import BytesParser
from email.utils import formataddr, parseaddr

import boto3
from botocore.exceptions import ClientError

# 設置日誌
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 設置 AWS 客戶端
s3_client = boto3.client("s3")
ses_client = boto3.client("ses")

CHARSET = "utf-8"
SENDER_EMAIL_DOMAIN = "aws-educate.tw"
DEFAULT_RECIPIENTS = ["awseducate.cloudambassador@gmail.com"]


def load_forwarding_rules():
    config_path = os.path.join(os.path.dirname(__file__), "forward_config.json")
    with open(config_path) as f:
        return json.load(f)


FORWARDING_RULES = load_forwarding_rules()


def lambda_handler(event, context):
    # 環境變量
    bucket_name = os.environ["BUCKET_NAME"]

    # 打印完整的事件日誌
    logger.info(f"Received event: {event}")

    # 解析 S3 事件並解碼 key
    encoded_key = event["Records"][0]["s3"]["object"]["key"]
    decoded_key = urllib.parse.unquote_plus(encoded_key)

    logger.info(f"Decoded key: {decoded_key}")
    logger.info(f"Encoded key: {encoded_key}")

    try:
        # 從 S3 讀取郵件內容
        response = s3_client.get_object(Bucket=bucket_name, Key=decoded_key)
        raw_email = response["Body"].read()

        # 解析 .eml 文件
        msg = BytesParser(policy=policy.default).parsebytes(raw_email)

        # 提取原始寄件者
        original_sender_header = msg["From"]
        original_sender_name, original_sender_email = parseaddr(original_sender_header)

        logger.info(f"Original sender name: {original_sender_name}")
        logger.info(f"Original sender email: {original_sender_email}")

        if not original_sender_name:
            display_name = original_sender_email
        else:
            display_name = original_sender_name

        # 提取收件地址
        to_address = msg["To"]
        if isinstance(to_address, str):
            to_address = to_address.lower().strip()
        else:
            decoded_to_address = decode_header(str(to_address))
            to_address = ""
            for header in decoded_to_address:
                if isinstance(header[0], bytes):
                    to_address += header[0].decode(header[1] or "utf-8")
                else:
                    to_address += header[0]
            to_address = to_address.lower().strip()

        # 確定轉發規則
        forwarding_rule = FORWARDING_RULES.get(to_address, None)

        if forwarding_rule:
            recipient_emails = forwarding_rule["recipients"]
            sender_local_part = forwarding_rule["sender_local_part"]
        else:
            recipient_emails = DEFAULT_RECIPIENTS
            sender_local_part = to_address.split("@")[0]  # 使用地址的 local part

        sender_email = f"{sender_local_part}@{SENDER_EMAIL_DOMAIN}"

        # 確保 From 使用我們的 domain
        from_address = sender_email

        # 修改原始郵件的 From 和 To 標頭
        if msg.get("From"):
            msg.replace_header("From", formataddr((display_name, from_address)))
        else:
            msg["From"] = formataddr((display_name, from_address))

        if msg.get("To"):
            msg.replace_header("To", ", ".join(recipient_emails))
        else:
            msg["To"] = ", ".join(recipient_emails)

        # 只有在原信件沒有 Reply-To 時才補上
        if not msg.get("Reply-To"):
            msg.add_header("Reply-To", original_sender_email)

        # 移除不必要的標頭
        if msg.get("Return-Path"):
            del msg["Return-Path"]
        if msg.get("Sender"):
            del msg["Sender"]
        if msg.get("Message-ID"):
            del msg["Message-ID"]
        while msg.get("DKIM-Signature"):
            del msg["DKIM-Signature"]

        # 構建新的原始郵件內容
        raw_email = msg.as_bytes()

        # 使用 SES 轉發郵件
        logger.info("Attempting to send email via SES...")
        response = ses_client.send_raw_email(
            Source=from_address,
            Destinations=recipient_emails,
            RawMessage={"Data": raw_email},
        )
        logger.info(f"SES response: {response}")

        logger.info("Email forwarded successfully")
        return {"statusCode": 200, "body": "Email forwarded successfully"}

    except s3_client.exceptions.NoSuchKey as e:
        logger.error(
            f"NoSuchKey error: The specified key {decoded_key} does not exist."
        )
        logger.error(f"Exception: {str(e)}")
        return {
            "statusCode": 404,
            "body": f"Failed to retrieve the object {decoded_key} from bucket {bucket_name}.",
        }

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]
        logger.error(f"ClientError: {error_code} - {error_message}")
        return {
            "statusCode": 500,
            "body": f"Client error occurred: {error_code} - {error_message}",
        }

    except Exception as e:
        logger.error(f"General error: {str(e)}")
        return {
            "statusCode": 500,
            "body": "An error occurred while processing the email.",
        }
