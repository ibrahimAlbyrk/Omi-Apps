import Logger
from Logger import FormatterType, LoggerType
from action_service import OmiActionService
from classification_service import AIClassificationService

logger = Logger.Manager("Emails Monitor",
                        FormatterType.ADVANCED,
                        LoggerType.CONSOLE)

classification_service = AIClassificationService()


def process_new_emails(uid: str, emails: []):
    count: int = 0
    for email in emails:
        classification = classification_service.classify_email(email)
        answer = classification.get("answer", False)
        language = classification.get("language", "en")
        if answer:
            action_service = OmiActionService(uid, language)
            success, status_code = action_service.send_email(email, classification)
            if not success:
                print(f"Failed to send email to Omi. HTTP Status: {status_code}")
            else:
                count += 1

    logger.info(f"Processed {count} new emails")