import requests
from config import OMI_API_KEY, OMI_APP_ID


class IActionService:
    def send_email(self, email: dict, classification: dict) -> bool:
        raise NotImplementedError

class OmiActionService(IActionService):
    def __init__(self, uid: str, language: str, api_key: str = OMI_API_KEY, app_id: str = OMI_APP_ID):
        self.uid = uid
        self.language = language
        self.api_key = api_key
        self.app_id = app_id

    def send_email(self, email: dict, classification: dict) -> bool:
        url = f"https://api.omi.me/v2/integrations/{self.app_id}/user/conversations?uid={self.uid}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        text = self._compose_email_text(email, classification)
        data = {
            "started_at": email.get('date'),
            "text": text,
            "text_source": "other_text",
            "text_source_spec": f"email about {classification.get('important')}" if classification.get(
                'important') else "email",
            "language": self.language
        }
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            return True, response.status_code
        except requests.exceptions.RequestException as e:
            print(f"Error sending email to Omi: {e}")
            return False, 500

    @staticmethod
    def _compose_email_text(email: dict, classification: dict) -> str:
        subject = email.get('subject', '')
        sender = email.get('from', '')
        content = email.get('body', '')
        important = classification.get('important', None)
        sender_importance = classification.get('sender_importance', '')
        priority = classification.get('priority', '')
        sentiment = classification.get('sentiment', '')
        tags = classification.get('tags', [])
        summary = classification.get('summary', '')
        has_attachments = classification.get('has_attachment', False)
        has_links = classification.get('has_links', False)
        suggested_actions = classification.get('suggested_actions', [])
        reply_required = classification.get('reply_required', False)

        parts = [
            f"# {subject}",
            f"**From**: {sender}",
            f"**Priority**: {priority}",
            f"**Tags**: {', '.join(tags) if tags else ''}",
            f"**Sentiment**: {sentiment}",
            f"**Sender Importance**: {sender_importance}",
            f"{f'**Suggested Actions**: {', '.join(suggested_actions)}' if suggested_actions else ''}",
            "---",
            "## Summary",
            summary,
            "---",
            f"{'(Reply Required)' if reply_required else ''} {('(Links)' if has_links else '')} {('(Attachments)' if has_attachments else '')}",
            "## Content",
            content
        ]

        return "\n\n".join(part for part in parts if part.strip() != "")