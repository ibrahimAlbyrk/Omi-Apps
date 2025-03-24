import email_service
from email_service import GmailService
from datetime import datetime, timezone
from action_service import OmiActionService
from email.utils import parsedate_to_datetime
from classification_service import ISummarizationService, AISummarizationService

summarization_service: ISummarizationService = AISummarizationService()


def convert_with_selected_ids(uid: str, credentials, thread_manager, selected_ids: list) -> list:
    gmail_service = GmailService(credentials, thread_manager)

    emails = []
    for message_id in selected_ids:
        mail = gmail_service.api_client.get_message(message_id)

        payload = mail.get("payload", {})
        headers = payload.get("headers", [])

        date = next((h["value"] for h in headers if h["name"].lower() == "date"), "No Date")
        subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "No Subject")
        from_email = next((h["value"] for h in headers if h["name"].lower() == "from"), "Unknown Sender")
        body = email_service.decode_email_body(payload)

        emails.append({
            "date":  parsedate_to_datetime(date).astimezone(timezone.utc).isoformat(),
            "subject": subject,
            "from": from_email,
            "body": body
        })

    return _send_to_memories(uid, emails)

def convert_with_email_count(uid: str, credentials, thread_manager, email_count: int) -> list:
    if email_count < 1:
        return []

    gmail_service = GmailService(credentials, thread_manager)
    emails = gmail_service.fetch_all_emails(uid, email_count)

    return _send_to_memories(uid, emails)

def _send_to_memories(uid: str, memories: list) -> list:
    results = _convert(memories)

    # The language has been set to English for now.
    action_service = OmiActionService(uid, "en")
    success = action_service.send_memories(results)

    if not success:
        return []

    return results

def _convert(emails) -> list:
    results = []
    for index in range(len(emails)):
        email = emails[index]
        result = summarization_service.summarize_email(email)
        if not result:
            continue
        results.append(result)

    return results


def _parse_and_format_date(date_str: str) -> str:
    try:
        parsed = datetime.strptime(date_str, "%Y-%m-%d")
        return parsed.replace(tzinfo=timezone.utc).isoformat()
    except (ValueError, TypeError):
        return None