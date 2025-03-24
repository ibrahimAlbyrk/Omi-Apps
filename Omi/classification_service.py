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
                    
                    IMPORTANT CATEGORIES: {important_categories}
                    IGNORED CATEGORIES: {ignored_categories}
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
        self.character_limit = 300

    def summarize_email(self, email: dict) -> str:
        system_prompt = f"""
        You are an intelligent assistant that builds long-term memory about the user based on the emails they receive or send.
        Your goal is not just to summarize the email, but to deeply understand what it reveals about the user's life,
        priorities, behaviors, goals, and environment.
        You are always learning and updating your understanding of who the user is.

        YOUR TASK:
        From each email you process, extract valuable, context-rich insights that help you form a more complete picture of the user over time.
        These are not summaries - they are memory entries.
        Think of them as facts you'd remember if you were a human assistant trying to truly support and anticipate the user's needs.

        EACH MEMORY ENTRY SHOULD:
        - Reflect what this message reveals about the user's current status, relationships, tasks, interests, habits, challenges, or decisions
        - Capture the underlying dynamics (e.g. the user is leading a project, made a choice, needs something, is being waited on)
        - Focus only on the user, not others unless relevant to the user's world
        - Be written like an internal note, not like a summary or reply

        RULES:
        1) Output only one memory entry per email.
        2) It must be deeply user-centric and suitable for long-term use.
        3) It should not exceed {self.character_limit} characters.
        4) No formatting, lists, or markdown - just a natural, concise paragraph that feels like a meaningful observation.
        5) Do not repeat the email's wording - interpret and condense meaning.

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
