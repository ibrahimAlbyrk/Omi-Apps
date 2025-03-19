import time
import base64
import Logger
from Logger import LoggerType, FormatterType
from datetime import timezone
from email.utils import parsedate_to_datetime
from googleapiclient.discovery import build

logger = Logger.Manager("gmail_service",
                        FormatterType.ADVANCED,
                        LoggerType.CONSOLE)

class IGmailAPIClient:
    def fetch_messages(self, max_results: int):
        raise NotImplementedError

    def get_message(self, message_id: str):
        raise NotImplementedError

class GmailAPIClient(IGmailAPIClient):
    def __init__(self, credentials):
        self.service = build("gmail", "v1", credentials=credentials)

    def fetch_messages(self, max_results: int = 5):
        try:
            results = self.service.users().messages().list(userId="me", maxResults=max_results).execute()
            return results.get("messages", [])
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            return []

    def fetch_unread_messages(self, max_results: int = 5):
        try:
            results = self.service.users().messages().list(userId="me", labelIds=["UNREAD"], maxResults=max_results).execute()
            return results.get("messages", [])
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            return []

    def get_message(self, message_id: str):
        return self.service.users().messages().get(userId="me", id=message_id).execute()

def decode_email_body(payload: dict) -> str:
    decoded_parts = []
    if "body" in payload and "data" in payload["body"]:
        try:
            decoded_parts.append(base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8"))
        except Exception as e:
            decoded_parts.append(f"[Error decoding body: {e}]")
    if "parts" in payload:
        for part in payload["parts"]:
            if "body" in part and "data" in part["body"]:
                try:
                    decoded_parts.append(base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8"))
                except Exception as e:
                    decoded_parts.append(f"[Error decoding part: {e}]")
    return "\n\n".join(decoded_parts) if decoded_parts else "[Content couldn't be read]"

class GmailService:
    def __init__(self, credentials, thread_manager):
        self.api_client = GmailAPIClient(credentials)
        self.thread_manager = thread_manager
        self.last_seen_email_ids = set()
        self.last_seen_email_time = None

    def fetch_emails(self, unread_only: bool = True, max_results: int = 5):
        if unread_only:
            messages = self.api_client.fetch_unread_messages(max_results)
        else:
            messages = self.api_client.fetch_messages(max_results)
        emails = []
        new_seen_ids = set()
        latest_email_time = self.last_seen_email_time
        for msg in messages:
            if msg["id"] in self.last_seen_email_ids:
                continue
            mail = self.api_client.get_message(msg["id"])
            payload = mail.get("payload", {})
            headers = payload.get("headers", [])
            date = next((header["value"] for header in headers if header["name"].lower() == "date"), "No Date")
            try:
                date_obj = parsedate_to_datetime(date).astimezone(timezone.utc)
                date_iso = date_obj.isoformat()
            except Exception:
                date_obj = None
                date_iso = date
            subject = next((header["value"] for header in headers if header["name"].lower() == "subject"), "No Subject")
            from_email = next((header["value"] for header in headers if header["name"].lower() == "from"), "Unknown Sender")
            body = decode_email_body(payload)
            emails.append({
                "date": date_iso,
                "subject": subject,
                "from": from_email,
                "body": body,
            })
            new_seen_ids.add(msg["id"])
            if date_obj and (latest_email_time is None or date_obj > latest_email_time):
                latest_email_time = date_obj
        if emails:
            self.last_seen_email_ids.update(new_seen_ids)
            self.last_seen_email_time = latest_email_time
        return emails

    def start_listening(self, listen_id: str, callback, unread_only: bool = True, interval: int = 60, max_results: int = 5):
        logger.info(f"Started listening on {listen_id}")
        self.thread_manager.start_thread(
            thread_id=f"gmail_listener_{listen_id}",
            target_function=self._pool_emails,
            args=(callback, unread_only, interval, max_results)
        )

    def stop_listening(self, listen_id: str):
        logger.info(f"Stopped listening on {listen_id}")
        self.thread_manager.stop_thread(f"gmail_listener_{listen_id}")

    def _pool_emails(self, stop_event, callback, unread_only: bool, interval: int, max_results: int):
        while not stop_event.is_set():
            emails = self.fetch_emails(unread_only, max_results)
            logger.info(f"{len(emails)} Emails fetched.")
            if emails:
                logger.info("Callback worked.")
                callback(emails)
            time.sleep(interval)