import time
import requests
from datetime import datetime, timezone
from Config import OMI_API_KEY, OMI_APP_ID


class IActionService:
    def send_memories(self, memories: list) -> bool:
        raise NotImplementedError

    def send_email(self, email: dict, classification: dict) -> bool:
        raise NotImplementedError

class OmiActionService(IActionService):
    def __init__(self, uid: str, language: str, api_key: str = OMI_API_KEY, app_id: str = OMI_APP_ID):
        self.uid = uid
        self.language = language
        self.api_key = api_key
        self.app_id = app_id

    def send_memories(self, memories: list) -> bool:
        url = f"https://api.omi.me/v2/integrations/{self.app_id}/user/memories?uid={self.uid}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        memory_count = 0

        for memory in memories:
            try:
                data = {
                    "text": memory,
                    "text_source": "other",
                    "text_source_spec": f"learning from mails",
                }

                response = requests.post(url, headers=headers, json=data)
                response.raise_for_status()
                memory_count += 1
                if response.status_code != 200:
                    return False, response.status_code
            except requests.exceptions.RequestException as e:
                print(f"Error sending memory to Omi: {e}")
                return False, 500

            # Adding a little bit rate Limiting
            time.sleep(0.2)

        return True

    def send_email(self, email: dict, classification: dict) -> bool:
        url = f"https://api.omi.me/v2/integrations/{self.app_id}/user/conversations?uid={self.uid}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        text = self.compose_email_text(email, classification)

        date = email.get('date', datetime.now(timezone.utc).isoformat())
        important = classification.get('important', None)

        data = {
            "started_at": date,
            "text": text,
            "text_source": "other_text",
            "text_source_spec": f"email about {important}" if important else "email",
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
    def compose_email_text(email: dict, classification: dict) -> str:
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

        suggested_actions_text = f"**Suggested Actions**: {', '.join(suggested_actions)}" if suggested_actions else ""

        parts = [
            f"# {subject}",
            f"**From**: {sender}",
            f"**Priority**: {priority}",
            f"**Tags**: {', '.join(tags) if tags else ''}",
            f"**Sentiment**: {sentiment}",
            f"**Sender Importance**: {sender_importance}",
            suggested_actions_text,
            "---",
            "## Summary",
            summary,
            "---",
            f"{'(Reply Required)' if reply_required else ''} {('(Links)' if has_links else '')} {('(Attachments)' if has_attachments else '')}",
            "## Content",
            content
        ]

        return "\n\n".join(part for part in parts if part.strip() != "")