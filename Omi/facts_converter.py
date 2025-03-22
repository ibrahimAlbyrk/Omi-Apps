from action_service import IActionService, OmiActionService
from email_service import GmailService
from datetime import datetime, timezone
from classification_service import ISummarizationService, AISummarizationService

summarization_service: ISummarizationService = AISummarizationService()

def convert_with_date_range(uid: str, credentials, thread_manager, start_date: str, end_date: str) -> list:
    start = _parse_and_format_date(start_date)
    end = _parse_and_format_date(end_date)

    if not start or not end:
        return []

    gmail_service = GmailService(credentials, thread_manager)
    emails = gmail_service.fetch_emails_by_date_range(uid, start, end)

    return _send_to_facts(emails)

def convert_with_email_count(credentials, thread_manager, email_count: int) -> list:
    if email_count < 1:
        return []

    gmail_service = GmailService(credentials, thread_manager)
    emails = gmail_service.fetch_all_emails(uid, email_count)

    return _send_to_facts(emails)

def _send_to_facts(facts: list) -> list:
    results = _convert(facts)

    # The language has been set to English for now.
    action_service: IActionService = OmiActionService(uid, "en")
    success = action_service.send_fact(results)

    if not success:
        return []

    return results

def _convert(emails: list) -> list:
    for email in emails:
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