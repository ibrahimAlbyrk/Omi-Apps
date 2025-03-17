import os
import pickle
import base64
import threading
from datetime import datetime, timezone
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.utils import parsedate_to_datetime
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

from Omi.Thread.ThreadManager import thread_manager

SCOPES = [os.getenv("GMAIL_SCOPES")]
CLIENT_SECRET_FILE = os.getenv("CLIENT_SECRET_FILE")


class GmailClient:
    def __init__(self, _id, credentials):
        self.id = _id
        self.credentials = credentials
        self.service = self.authenticate_gmail()

    def authenticate_gmail(self):
        return build("gmail", "v1", credentials=self.credentials)

    def fetch_emails(self, max_results=5):
        try:
            results = self.service.users().messages().list(userId="me", maxResults=max_results).execute()
            messages = results.get("messages", [])
        except Exception as e:
            print(f"Error fetching emails: {e}")
            return []

        emails = []

        for msg in messages:
            mail = self.service.users().messages().get(userId="me", id=msg["id"]).execute()
            payload = mail.get("payload", {})
            headers = payload.get("headers", [])

            date = next((header["value"] for header in headers if header["name"].lower() == "date"), "No Subject")
            date = parsedate_to_datetime(date).astimezone(timezone.utc).isoformat()

            subject = next((header["value"] for header in headers if header["name"].lower() == "subject"), "No Subject")
            from_email = next((header["value"] for header in headers if header["name"].lower() == "from"),
                              "Unknown Sender")
            body = self.decode_email_body(payload)

            emails.append({
                "date": date,
                "subject": subject,
                "from": from_email,
                "body": body,
            })

        return emails

    @staticmethod
    def decode_email_body(payload):
        decoded_parts = []

        if "body" in payload and "data" in payload["body"]:
            decoded_parts.append(base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8"))

        if "parts" in payload:
            for part in payload["parts"]:
                if "body" in part and "data" in part["body"]:
                    try:
                        decoded_text = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                        decoded_parts.append(decoded_text)
                    except Exception as e:
                        decoded_parts.append(f"[Error decoding part: {str(e)}]")

        return "\n\n".join(decoded_parts) if decoded_parts else "[Content couldn't be read]"

    def start_gmail_listening(self, callback: function):
        thread_manager.start_thread(_id=self.id, target_function=self.gmail_check_pool, args= (callback, 60, 3))

    def stop_gmail_listening(self):
        if thread_manager.is_running(self.id):
            thread_manager.stop_thread(self.id)

    def gmail_check_pool(self, callback: function, interval=60, max_results=5):
        while True:
            emails = self.fetch_emails(max_results)
            callback(emails)
            time.sleep(interval)
