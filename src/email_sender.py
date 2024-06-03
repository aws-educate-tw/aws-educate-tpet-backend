import datetime
import io
import json
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import boto3
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


def google_service(api, version):
    SCOPES = [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/spreadsheets",
    ]
    creds = None
    with open("google-cred.json", "r") as creds_file:
        creds_json = json.load(creds_file)
        creds = service_account.Credentials.from_service_account_info(
            creds_json, scopes=SCOPES
        )
    return build(api, version, credentials=creds)


service = google_service("drive", "v3")
sheet_service = google_service("sheets", "v4")


class EmailSender:
    def __init__(self, spreadsheet_id, template_file_id, email_title):
        self.spreadsheet_id = spreadsheet_id
        self.range_name = os.environ["RANGE_NAME"]
        self.template_file_id = template_file_id
        self.email_title = email_title
        self.service = service
        self.sheet_service = sheet_service

    def get_template(self):
        request = self.service.files().get_media(fileId=self.template_file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        fh.seek(0)
        return fh.read().decode("utf-8")

    def read_sheet_data(self):
        result = (
            self.sheet_service.spreadsheets()
            .values()
            .get(spreadsheetId=self.spreadsheet_id, range=self.range_name)
            .execute()
        )
        rows = result.get("values", [])
        if not rows:
            return [], 0
        header = rows[0]
        data = [dict(zip(header, row)) for row in rows[1:]]
        num_columns = len(header)
        return data, num_columns, "Send Status" not in header

    def send_emails(self):
        client = boto3.client("ses", region_name="ap-northeast-1")
        template_content = self.get_template()
        data, num_columns, header_missing = self.read_sheet_data()
        send_times = []
        if header_missing:
            self.update_header(num_columns + 1)

        for index, row in enumerate(data, start=2):
            receiver_email = row.get("Email")
            if not receiver_email:
                print(
                    f"No email address provided for {row.get('Name', 'Unknown')}. Skipping..."
                )
                send_times.append(["Failed"])
                continue

            try:
                response = client.send_email(
                    Source='"AWS Educate 證照陪跑計畫" <awseducate.cloudambassador@gmail.com>',
                    Destination={"ToAddresses": [receiver_email]},
                    Message={
                        "Subject": {"Data": self.email_title},
                        "Body": {
                            "Html": {
                                "Data": template_content.format(
                                    name=row.get("Name", "Unknown")
                                )
                            }
                        },
                    },
                )
                send_time = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
                formatted_send_time = send_time.strftime("%Y-%m-%d %H:%M:%S")
                send_times.append([formatted_send_time])
                print(
                    f"Email sent to {row.get('Name', 'Unknown')} at {formatted_send_time}"
                )
            except Exception as e:
                print(f"Failed to send email to {row.get('Name', 'Unknown')}: {e}")
                send_times.append(["Failed"])

        self.update_send_times(send_times, num_columns + 1)

    def update_header(self, column_index):
        column_letter = chr(65 + column_index - 1)
        update_range = f"{self.range_name.split('!')[0]}!{column_letter}1"
        self.sheet_service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range=update_range,
            valueInputOption="USER_ENTERED",
            body={"values": [["Send Status"]]},
        ).execute()

    def update_send_times(self, send_times, column_index):
        column_letter = chr(65 + column_index - 1)
        update_range = f"{self.range_name.split('!')[0]}!{column_letter}2:{column_letter}{len(send_times)+1}"
        self.sheet_service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range=update_range,
            valueInputOption="USER_ENTERED",
            body={"values": send_times},
        ).execute()


def lambda_handler(event, context):
    try:
        query_params = event.get("queryStringParameters", {})
        template_file_id = query_params.get("template_file_id")
        spreadsheet_id = query_params.get("spreadsheet_id")
        email_title = query_params.get("email_title")
        print("template_file_id: ", template_file_id)
        print("spreadsheet_id: ", spreadsheet_id)

        if not template_file_id or not spreadsheet_id or not email_title:
            return {
                "statusCode": 400,
                "body": json.dumps(
                    "Missing template_file_id or spreadsheet_id or email_title"
                ),
            }

        sender = EmailSender(
            spreadsheet_id=spreadsheet_id,
            template_file_id=template_file_id,
            email_title=email_title,
        )
        sender.send_emails()
        return {"statusCode": 200, "body": json.dumps("Email sent successfully!")}
    except Exception as e:
        print(f"Error processing the Lambda function: {str(e)}")
        return {"statusCode": 500, "body": json.dumps("Internal server error")}
