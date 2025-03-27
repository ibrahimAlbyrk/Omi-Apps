import os
import json
import openai
from Config import OPENAI_API_KEY
from action_service import OmiActionService
import email_service


GPT_MODEL = "gpt-4o-mini"


class IClassificationService:
    def classify_emails(self, emails: list, important_categories: list, ignored_categories: list) -> list:
        raise NotImplementedError


class ISummarizationService:
    def summarize_email(self, email: dict) -> list:
        raise NotImplementedError


class AIClassificationService(IClassificationService):
    DEFAULT_IMPORTANT_CATEGORIES = [
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

    DEFAULT_IGNORED_CATEGORIES = [
        "newsletter",
        "promotion",
        "social media",
        "spam",
        "survey",
        "event invitation",
        "job alert",
        "greetings",
    ]

    def __init__(self):
        self.client = openai.Client(api_key=OPENAI_API_KEY)
        self.always_important = False

    def classify_emails(self, emails: list, important_categories=None, ignored_categories=None) -> list:
        if ignored_categories is None:
            ignored_categories = DEFAULT_IGNORED_CATEGORIES
        if important_categories is None:
            important_categories = DEFAULT_IMPORTANT_CATEGORIES

        classify_function = {
            "type": "function",
            "function": {
                "name": "classify_email",
                "description": (
                    f"""

                    You are an advanced email classifier. Analyze the given email thoroughly based on:

                    IMPORTANT CATEGORIES (exactly match the main purpose or intent): {', '.join(important_categories)}
                    IGNORED CATEGORIES (emails that are promotional, generic, or low priority): {', '.join(ignored_categories)}
                    
                    If both important and ignored categories seem applicable, always prioritize {"IMPORTANT" if self.always_important else "IGNORED"}.
                    Return language using ISO 639-1 format
                    Determine priority and sender importance based on urgency, deadlines, or identity.
                    Make sure sentiment, tags, and suggested actions are accurate based on content.
                    """
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "answer": {"type": "boolean", "description": "Set true if email clearly matches an IMPORTANT CATEGORY; otherwise false"},

                        "important": {"type": ["string", "null"],
                                      "description": "Identify exactly one matched IMPORTANT CATEGORY or Null if none match clearly."},

                        "priority": {"type": ["string", "null"], "description": """Determine based on urgency, sender's importance, deadlines, and the potential impact:
                        "high": Immediate action required, urgent issues, critical deadlines, security alerts.
                        "medium": Moderate urgency, needs attention soon (e.g., meetings, project updates).
                        "low": Minor urgency, informational updates, invoices with distant due dates.
                        null: If no clear priority."""},

                        "sender_importance": {"type": "string", "description": """Based on sender identity and context:
                        "critical": Important clients, management, executives, known critical contacts.
                        "regular": Known contacts, standard business emails.
                        "unknown": Unrecognized or new sender."""},

                        "summary": {"type": "string",
                                    "description": "Provide a concise, single-sentence summary clearly capturing the core intent or action required."},

                        "sentiment": {"type": ["string", "null"], "description": """Analyze overall tone:
                        "positive": Clearly good news, approval, confirmations.
                        "neutral": Informational, factual, balanced.
                        "negative": Complaints, problems, urgent warnings or negative issues."""},

                        "has_attachment": {"type": "boolean",
                                           "description": "Set true if the email explicitly mentions or clearly indicates attachments; otherwise false."},

                        "has_links": {"type": "boolean", "description": "Set true if email clearly contains clickable URLs or mentions external links explicitly; otherwise false."},

                        "suggested_actions": {"type": "array", "items": {"type": "string"},
                                              "description": "Suggest relevant actions explicitly based on email content. Examples: [reply, schedule_meeting, pay_invoice, reset_password, review_document, follow_up, verify_account, check_security, track_shipping]"},

                        "tags": {"type": "array", "items": {"type": "string",
                                                            "description": "Include precise tags reflecting email context, content, industry, and keywords clearly relevant to help categorize effectively."}},

                        "reply_required": {"type": "boolean", "description": "Set true only if email explicitly requests a reply, confirmation, or clearly needs response; otherwise false."},

                        "language": {"type": "string",
                                     "description": "Use ISO 639-1 codes like 'tr' for Turkish, 'en' for English."},

                        "ignored": {"type": ["string", "null"],
                                    "description": "Clearly identify exactly one IGNORED CATEGORY if the email matches any. If it also matches an IMPORTANT CATEGORY, IGNORED takes precedence."}
                    },
                    "required": ["answer", "important", "priority", "sender_importance", "summary", "sentiment",
                                 "has_attachment", "has_links", "suggested_actions", "tags", "reply_required",
                                 "language", "ignored"]
                }
            }
        }

        results = []

        for email in emails:
            subject = email.get('subject', '')
            fromm = email.get('from', '')
            content = email.get('body', '')

            prompt = (
                f"Mail Title: {subject}\n"
                f"From: {fromm}\n"
                f"Content: {content[:1000]}"
            )

            response = self.client.chat.completions.create(
                model=GPT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                tools=[classify_function],
                tool_choice={"type": "function", "function": {"name": "classify_email"}}
            )

            tool_call = response.choices[0].message.tool_calls[0]
            arguments = tool_call.function.arguments
            result = json.loads(arguments)

            results.append(result)

        return results


class AISummarizationService(ISummarizationService):
    def __init__(self):
        self.client = openai.Client(api_key=OPENAI_API_KEY)
        self.always_important = False
        self.character_limit = 200

    def summarize_email(self, email: dict) -> str:
        system_prompt = f"""
        You are building long-term memory about the user from emails.
        Focus on what the email reveals about their behavior, relationships, or decisions.
        Output one paragraph of max {self.character_limit} chars, deeply user-centric.
        Avoid summaries. Be concise and insightful.
        Always act like you're building an evolving, personal profile to better serve and understand the user over time.
        """

        subject = email.get('subject', None)
        content = email.get('body', None)

        if not subject or not content:
            return []

        prompt = f"""
            "Title": {subject},
            "Content": {content}
        """

        response = self.client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )

        summary = response.choices[0].message.content.strip()

        if len(summary) > self.character_limit:
            summary = summary[:self.character_limit] + "..."

        return summary
