import os
import requests
from datetime import datetime, timezone

OMI_API_KEY = os.getenv("OMI_API_KEY")
OMI_USER_ID = os.getenv("OMI_USER_ID")
OMI_APP_ID = os.getenv("OMI_APP_ID")

class ActionClient:
    def __init__(self, language):
        self.language = language

    def send_email_to_conversations(self, mail):
        url = f"https://api.omi.me/v2/integrations/{OMI_APP_ID}/user/conversations?uid={OMI_USER_ID}"
        headers = {
            "Authorization": f"Bearer {OMI_API_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "text": f"Title: {mail['subject']}\n\nFrom: {mail['from']}\n\nContent: {mail['body'][:500]}",
            "text_source": "other_text",
            "text_source_spec": "email",
            "language": self.language
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            return True, response.status_code
        except requests.exceptions.RequestException as e:
            print(f"Error sending email to Omi: {e}")
            return False, None