import Logger
from Logger import FormatterType, LoggerType
from action_service import OmiActionService
from classification_service import AIClassificationService

logger = Logger.Manager("Emails Monitor",
                        FormatterType.ADVANCED,
                        LoggerType.CONSOLE)

classification_service = AIClassificationService()


def process_new_emails(uid: str, emails: [], important_categories: [] = None, ignored_categories: [] = None):
    classifications = classification_service.classify_emails(emails, important_categories, ignored_categories)
    for index in range(len(classifications)):
        email = emails[index]
        classification = classifications[index]

        answer = classification.get("answer", False)
        language = classification.get("language", "en")

        if not answer:
            continue

        action_service = OmiActionService(uid, language)
        success, status_code = action_service.send_email(email, classification)
        if not success:
            print(f"Failed to send email to Omi. HTTP Status: {status_code}")
