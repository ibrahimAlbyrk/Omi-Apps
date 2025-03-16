import os
import requests
from datetime import datetime, timezone

OMI_API_KEY = os.getenv("OMI_API_KEY")
OMI_USER_ID = os.getenv("OMI_USER_ID")
OMI_APP_ID = os.getenv("OMI_APP_ID")


class ActionClient:
    def __init__(self, language):
        self.language = language

    def send_email_to_conversations(self, mail, classify=None):
        url = f"https://api.omi.me/v2/integrations/{OMI_APP_ID}/user/conversations?uid={OMI_USER_ID}"
        headers = {
            "Authorization": f"Bearer {OMI_API_KEY}",
            "Content-Type": "application/json"
        }

        important = classify['important']

        has_attachments = classify['has_attachment']
        has_links = classify['has_links']
        reply_required = classify['reply_required']
        suggested_actions = classify['suggested_actions']

        text = "\n\n".join([
            f"# {mail['subject']}",
            f"**From**: {mail['from']}",
            f"**Priority**: {classify['priority']}",
            "---",
            f"## Summary",
            f"{classify['summary']}",
            "---",
            f"## Content",
            f"{mail['body']}"
        ])

        data = {
            "started_at": mail['date'],
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
            return False, None
