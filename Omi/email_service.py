import time
import base64
import Logger
import json
import hashlib
from bs4 import BeautifulSoup
from thread_manager import IThreadManager
from Logger import LoggerType, FormatterType
from datetime import timezone, datetime, timedelta
from Database import SQLiteDatabaseManager, MailRepository
from email.utils import parsedate_to_datetime
from googleapiclient.discovery import build

logger = Logger.Manager("gmail_service",
                        FormatterType.ADVANCED,
                        LoggerType.CONSOLE)

db_manager = SQLiteDatabaseManager()
gmail_repository = MailRepository(db_manager)

class IGmailAPIClient:
    def fetch_messages(self, max_results: int):
        raise NotImplementedError

    def get_message(self, message_id: str):
        raise NotImplementedError

class GmailAPIClient(IGmailAPIClient):
    def __init__(self, credentials):
        self.service = build("gmail", "v1", credentials=credentials)

    def fetch_messages_by_query(self, query: str, max_results: int = -1) -> list:
        messages = []
        page_token = None

        while True:
            fetch_count = 500 if max_results < 0 else min(max_results - len(messages), 500)

            response = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=fetch_count,
                pageToken=page_token
            ).execute()

            message_ids = response.get('messages', [])
            if not message_ids:
                break

            for msg in message_ids:
                msg_detail = self.service.users().messages().get(userId='me', id=msg['id']).execute()
                messages.append(msg_detail)

                if 0 <= max_results <= len(messages):
                    return messages

            page_token = response.get('nextPageToken')
            if not page_token:
                break

        return messages

    def fetch_messages(self, max_results: int = 100):
        messages = []
        page_token = None

        while len(messages) < max_results:
            remaining = max_results - len(messages)
            fetch_count = min(remaining, 500)

            response = self.service.users().messages().list(
                userId='me',
                maxResults=fetch_count,
                pageToken=page_token
            ).execute()

            message_ids = response.get('messages', [])
            if not message_ids:
                break

            for msg in message_ids:
                msg_detail = self.service.users().messages().get(userId='me', id=msg['id']).execute()
                messages.append(msg_detail)

                if len(messages) >= max_results:
                    break

            page_token = response.get('nextPageToken')
            if not page_token:
                break

        return messages

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
    plain_contents = []
    html_contents = []

    def decode_plain(encoded):
        try:
            return base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4)).decode("utf-8", errors="replace")
        except Exception as e:
            return f"[Plaintext decode error: {e}]"

    def decode_html(encoded):
        try:
            decoded = base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4)).decode("utf-8", errors="replace")
            soup = BeautifulSoup(decoded, "html.parser")
            paragraphs = soup.find_all("p")
            return "\n\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
        except Exception as e:
            return f"[HTML decode error: {e}]"

    def try_add(text, target_list):
        norm = " ".join(text.lower().split())
        if norm not in [" ".join(x.lower().split()) for x in target_list]:
            target_list.append(text)

    if "parts" in payload:
        for part in payload["parts"]:
            mime = part.get("mimeType")
            body_data = part.get("body", {}).get("data")
            if not body_data:
                continue

            if mime == "text/plain":
                try_add(decode_plain(body_data), plain_contents)
            elif mime == "text/html":
                try_add(decode_html(body_data), html_contents)

    if payload.get("body", {}).get("data"):
        mime = payload.get("mimeType")
        body_data = payload["body"]["data"]
        if mime == "text/plain":
            try_add(decode_plain(body_data), plain_contents)
        elif mime == "text/html":
            try_add(decode_html(body_data), html_contents)

    if plain_contents:
        return "\n\n---\n\n".join(plain_contents)
    elif html_contents:
        return "\n\n---\n\n".join(html_contents)
    else:
        return None


class GmailService:
    def __init__(self, credentials, thread_manager: IThreadManager):
        self.api_client = GmailAPIClient(credentials)
        self.thread_manager = thread_manager
        self.last_seen_email_time = None

    def fetch_all_emails(self, uid: str, max_results: int):
        messages = self.api_client.fetch_messages(max_results)

        return self._process_messages(
            uid,
            messages,
            track_latest_time=False,
            mark_as_processed=False
        )

    def fetch_emails(self, uid: str, unread_only: bool = True, max_results: int = 5):
        if unread_only:
            messages = self.api_client.fetch_unread_messages(max_results)
        else:
            messages = self.api_client.fetch_messages(max_results)

        return self._process_messages(uid, messages)

    def _process_messages(
            self,
            uid: str,
            messages: list,
            track_latest_time: bool = True,
            mark_as_processed: bool = True
    ):
        emails = []
        latest_email_time = self.last_seen_email_time

        for msg in reversed(messages):
            msg_id = msg["id"]

            if mark_as_processed and gmail_repository.is_email_processed(uid, msg_id):
                continue

            mail = self.api_client.get_message(msg_id)
            payload = mail.get("payload", {})
            headers = payload.get("headers", [])

            date = next((h["value"] for h in headers if h["name"].lower() == "date"), "No Date")
            try:
                date_obj = parsedate_to_datetime(date).astimezone(timezone.utc)
                date_iso = date_obj.isoformat()
            except Exception:
                date_obj = None
                date_iso = date

            subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "No Subject")
            from_email = next((h["value"] for h in headers if h["name"].lower() == "from"), "Unknown Sender")
            body = decode_email_body(payload)

            emails.append({
                "date": date_iso,
                "subject": subject,
                "from": from_email,
                "body": body,
            })

            if track_latest_time and date_obj and (latest_email_time is None or date_obj > latest_email_time):
                latest_email_time = date_obj

            if mark_as_processed:
                gmail_repository.add_processed_email(uid, msg_id)

        if emails and track_latest_time:
            self.last_seen_email_time = latest_email_time

        return emails

    def is_listening(self, uid: str) -> bool:
        return self.thread_manager.is_thread_running(uid)

    def start_listening(self, uid: str, callback, unread_only: bool = True, interval: int = 60, max_results: int = 5):
        self.thread_manager.start_thread(
            thread_id=f"gmail_listener_{uid}",
            target_function=self._pool_emails,
            args=(callback, uid, unread_only, interval, max_results)
        )

    def stop_listening(self, uid: str):
        self.thread_manager.stop_thread(f"gmail_listener_{uid}")

    def _pool_emails(self, stop_event, callback, uid, unread_only: bool, interval: int, max_results: int):
        while not stop_event.is_set():
            emails = self.fetch_emails(uid, unread_only, max_results)
            if emails:
                callback(emails)
            time.sleep(interval)