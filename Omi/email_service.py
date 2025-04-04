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
    def __init__(self, credentials, thread_manager: IThreadManager):
        self.credentials = credentials
        self.api_client = GmailAPIClient(credentials)
        self.thread_manager = thread_manager
        self.last_seen_email_time = None

    def fetch_email_subjects_paginated(self, offset: int, limit: int) -> list:
        from googleapiclient.discovery import build
        service = build('gmail', 'v1', credentials=self.credentials)

        result = service.users().messages().list(userId='me', maxResults=offset + limit, q="").execute()
        messages = result.get('messages', [])

        subjects = []
        for i in range(offset, offset + limit):
            if i >= len(messages):
                break

            msg_id = messages[i]['id']
            msg = service.users().messages().get(userId='me', id=msg_id, format='metadata',
                                                 metadataHeaders=["Subject"]).execute()

            subject = "No Subject"
            headers = msg.get("payload", {}).get("headers", [])
            for h in headers:
                if h.get("name", "").lower() == "subject":
                    subject = h["value"]
                    break

            subjects.append({
                "id": msg_id,
                "subject": subject
            })

        return subjects

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