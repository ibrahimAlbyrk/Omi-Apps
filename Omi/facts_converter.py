from Main import user_repository
from email_service import GmailService
from datetime import datetime, timezone
from Database import SQLiteDatabaseManager, UserRepository
from action_service import OmiActionService
from classification_service import ISummarizationService, AISummarizationService, IClassificationService, AIClassificationService

summarization_service: ISummarizationService = AISummarizationService()
classification_service: IClassificationService = AIClassificationService()


def convert_with_email_count(uid: str, credentials, thread_manager, email_count: int) -> list:
    if email_count < 1:
        return []

    gmail_service = GmailService(credentials, thread_manager)
    emails = gmail_service.fetch_all_emails(uid, email_count)

    return _send_to_facts(uid, emails)

def _send_to_facts(uid: str, facts: list) -> list:
    settings = user_repository.get_user_settings(uid)

    important_categories = settings.get("important_categories", AIClassificationService.DEFAULT_IMPORTANT_CATEGORIES)
    ignored_categories = settings.get("ignored_categories", AIClassificationService.DEFAULT_IGNORED_CATEGORIES)

    results = _convert(facts, important_categories, ignored_categories)

    # The language has been set to English for now.
    action_service = OmiActionService(uid, "en")
    success = action_service.send_facts(results)

    if not success:
        return []

    return results

def _convert(emails, important_category: list, ignored_category: list) -> list:
    results = []
    classifications = classification_service.classify_emails(emails, important_category, ignored_category)
    for index in range(len(emails)):
        email = emails[index]
        classification = classifications[index]
        result = summarization_service.summarize_email(email, classification)
        results.append(result)

    print(len(results))
    for result in results:
        print(result)

    return results


def _parse_and_format_date(date_str: str) -> str:
    try:
        parsed = datetime.strptime(date_str, "%Y-%m-%d")
        return parsed.replace(tzinfo=timezone.utc).isoformat()
    except (ValueError, TypeError):
        return None