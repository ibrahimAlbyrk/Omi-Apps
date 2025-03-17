import os
import requests
from datetime import datetime, timezone

OMI_API_KEY = os.getenv("OMI_API_KEY")
OMI_APP_ID = os.getenv("OMI_APP_ID")


class ActionClient:
    def __init__(self, uid, language):
        self.uid = uid
        self.language = language

    def send_email_to_conversations(self, mail, classify=None):
        url = f"https://api.omi.me/v2/integrations/{OMI_APP_ID}/user/conversations?uid={self.uid}"
        headers = {
            "Authorization": f"Bearer {OMI_API_KEY}",
            "Content-Type": "application/json"
        }

        important = classify['important']
        sender_importance = classify['sender_importance']

        subject = mail['subject']
        m_from = mail['from']
        content = mail['body']
        priority = classify['priority']
        sentiment = classify['sentiment']
        tags = classify['tags']
        summary = classify['summary']

        has_attachments = classify['has_attachment']
        has_links = classify['has_links']
        suggested_actions = classify['suggested_actions']
        reply_required = classify['reply_required']

        text = "\n\n".join([
            f"# {subject}",
            f"**From**: {m_from}",
            f"**Priority**: {priority}",
            f"**Tags**: {tags}",
            f"**sentiment**: {sentiment}",
            f"**Sender Importance**: {sender_importance}",
            f"{f"**Suggested Actions**: {suggested_actions}" if len(suggested_actions) > 0 else ""}",
            "---",
            f"## Summary",
            f"{summary}",
            "---",
            f"{"(Reply Required)" if reply_required else ""}",
            f"{"(Links)" if has_links else ""} {"(Attachments)" if has_attachments else ""}",
            f"## Content",
            f"{content}"
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
