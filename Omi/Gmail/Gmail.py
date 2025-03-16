import os
import pickle
import base64
from datetime import datetime, timezone
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from email.utils import parsedate_to_datetime

SCOPES = [os.getenv("GMAIL_SCOPES")]
CLIENT_SECRET_FILE = os.getenv("CLIENT_SECRET_FILE")

class GmailClient:
    def __init__(self):
        self.service = self.authenticate_gmail()

    @staticmethod
    def authenticate_gmail():
        """Authenticates and returns a Gmail API service instance."""
        creds = None
        token_path = "token.pickle"

        if os.path.exists(token_path):
            with open(token_path, "rb") as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
                creds = flow.run_local_server(port=0)

            with open(token_path, "wb") as token:
                pickle.dump(creds, token)

        return build("gmail", "v1", credentials=creds)

    def fetch_emails(self, max_results=5):
        """Fetches the latest emails from the user's Gmail account."""
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
            from_email = next((header["value"] for header in headers if header["name"].lower() == "from"), "Unknown Sender")
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
        """Extracts and decodes the email body from the Gmail API response."""
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