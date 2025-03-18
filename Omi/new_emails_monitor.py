from classification_service import ClassificationService
from action_service import OmiActionService

classification_service = ClassificationService()


def process_new_emails(uid: str, emails: []):
    for email in emails:
        classification = classification_service.classify_email(email)
        answer = classification.get("answer", False)
        language = classification.get("language", "en")
        if answer:
            action_service = OmiActionService(uid, language)
            success, status_code = action_service.send_email(email, classification)
            if not success:
                print(f"Failed to send email to Omi. HTTP Status: {status_code}")
