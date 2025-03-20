import os
import json
import openai
from Config import OPENAI_API_KEY


class IClassificationService:
    def classify_email(self, email: dict) -> dict:
        raise NotImplementedError


class AIClassificationService(IClassificationService):
    def __init__(self):
        self.client = openai.Client(api_key=OPENAI_API_KEY)
        self.always_important = False
        self.IMPORTANT_CATEGORIES = [
            "urgent",
            "meeting",
            "invoice",
            "payment due",
            "project update",
            "Github",
            "security alert",
            "password reset",
            "account verification",
            "legal notice",
            "deadline reminder",
            "contract",
            "shipping"
        ]

        self.IGNORED_CATEGORIES = [
            "newsletter",
            "promotion",
            "social media",
            "spam",
            "survey",
            "event invitation",
            "job alert",
            "greetings",
        ]

    def classify_email(self, email: dict) -> dict:
        prompt = (
            f"Mail Title: {email.get('subject', '')}\n"
            f"From: {email.get('from', '')}\n"
            f"Content: {email.get('body', '')[:1000]}"
        )
        system_prompt = f"""
                You are an advanced email classifier. Analyze the given email thoroughly based on:

                IMPORTANT CATEGORIES (exactly match the main purpose or intent): {', '.join(self.IMPORTANT_CATEGORIES)}
                IGNORED CATEGORIES (emails that are promotional, generic, or low priority): {', '.join(self.IGNORED_CATEGORIES)}

                Classify the email with precision according to these instructions:
                - "answer": Set true if email clearly matches an IMPORTANT CATEGORY; otherwise false.
                - "important": Identify exactly one matched IMPORTANT CATEGORY or None if none match clearly.
                - "priority": Determine based on urgency, sender's importance, deadlines, and the potential impact:
                    - "high": Immediate action required, urgent issues, critical deadlines, security alerts.
                    - "medium": Moderate urgency, needs attention soon (e.g., meetings, project updates).
                    - "low": Minor urgency, informational updates, invoices with distant due dates.
                    - null: If no clear priority.
                - "sender_importance": Based on sender identity and context:
                    - "critical": Important clients, management, executives, known critical contacts.
                    - "regular": Known contacts, standard business emails.
                    - "unknown": Unrecognized or new sender.
                - "summary": Provide a concise, single-sentence summary clearly capturing the core intent or action required.
                - "sentiment": Analyze overall tone:
                    - "positive": Clearly good news, approval, confirmations.
                    - "neutral": Informational, factual, balanced.
                    - "negative": Complaints, problems, urgent warnings or negative issues.
                - "has_attachment": Set true if the email explicitly mentions or clearly indicates attachments; otherwise false.
                - "has_links": Set true if email clearly contains clickable URLs or mentions external links explicitly; otherwise false.
                - "suggested_actions": Suggest relevant actions explicitly based on email content:
                    Examples: ["reply", "schedule_meeting", "pay_invoice", "reset_password", "review_document", "follow_up", "verify_account", "check_security", "track_shipping"]
                    - Use logical inference based on content.
                - "tags": Include precise tags reflecting email context, content, industry, and keywords clearly relevant to help categorize effectively.
                    Examples: ["finance", "HR", "development", "security", "marketing", "logistics", "urgent", "payment"]
                - "reply_required": Set true only if email explicitly requests a reply, confirmation, or clearly needs response; otherwise false.
                - "language": Identify and return the primary language clearly used in the email. Write languages in abbreviated form using ISO 639-1 codes.
                - "ignored": Clearly identify exactly one IGNORED CATEGORY matched or None if none clearly match.

                If both important and ignored categories seem applicable, always prioritize {"IMPORTANT" if self.always_important else "IGNORED"}.
                If no category clearly matches, set both categories to None and answer to false.

                Provide the classification strictly in the exact JSON format without additional text or explanations:
                {{
                    "answer": true or false,
                    "important": matched important category or None,
                    "priority": "high", "medium", "low" or unclear,
                    "sender_importance": "critical", "regular", "unknown",
                    "summary": short summary sentence,
                    "sentiment": "positive", "neutral", "negative" or unclear,
                    "has_attachment": true or false,
                    "has_links": true or false,
                    "suggested_actions": array of suggested actions or empty [],
                    "tags": array of relevant tags or empty [],
                    "reply_required": true or false,
                    "language": detected email language,
                    "ignored": matched ignored category or None
                }}
                """

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )

        content = response.choices[0].message.content.strip()
        classification = json.loads(content)
        return classification
