import os
import json
import openai
from Config import OPENAI_API_KEY
from action_service import OmiActionService

GPT_MODEL = "gpt-3.5-turbo-0125"


class IClassificationService:
    def classify_emails(self, emails: list, important_categories: list, ignored_categories: list) -> list:
        raise NotImplementedError


class ISummarizationService:
    def summarize_email(self, email: dict, classification: dict) -> list:
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
                    Classifies an email and extracts relevant metadata.
                    f"IMPORTANT CATEGORIES: {important_categories}
                    IGNORED CATEGORIES: {ignored_categories}
                    If both important and ignored categories apply, {"IMPORTANT" if self.always_important else "IGNORED"} should be prioritized.
                    Return language using ISO 639-1 format (e.g., 'tr' not 'Turkish').
                    Determine priority and sender importance based on urgency, deadlines, or identity.
                    Make sure sentiment, tags, and suggested actions are accurate based on content.
                    """
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "answer": {"type": "boolean", "description": "Set true if email clearly matches an IMPORTANT CATEGORY; otherwise false."},

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
                                    "description": " Clearly identify exactly one IGNORED CATEGORY matched or Null if none clearly match"}
                    },
                    "required": ["answer", "important", "priority", "sender_importance", "summary", "sentiment",
                                 "has_attachment", "has_links", "suggested_actions", "tags", "reply_required",
                                 "language", "ignored"]
                }
            }
        }

        results = []

        for email in emails:
            prompt = (
                f"Mail Title: {email.get('subject', '')}\n"
                f"From: {email.get('from', '')}\n"
                f"Content: {email.get('body', '')[:1000]}"
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

    def summarize_email(self, email: dict, classification: dict) -> str:
        system_prompt = f"""
                You will be given the content of an email.
                Your task is not just to summarize it, but to extract meaningful, memory-worthy facts 
                about the user based on the message content. These facts should be context-rich, personal, 
                and useful for understanding the user's goals, responsibilities, relationships, preferences, 
                or current engagements.

                YOUR OBJECTIVE:
                Analyze the email and output a single paragraph that:
                - Identifies what the email reveals about the user (e.g. their role, projects, interests, or tasks)
                - Extracts key facts that should be remembered about the user's current state or environment
                - Embeds tags or context indicators (e.g. SDK, PR, deadline, client, payment, request, etc.) where helpful
                - Highlights important dynamics (e.g. user made a decision, received a request, is awaiting something)
                - Is suitable for long-term memory (i.e. something a smart assistant would want to recall later)

                RULES:
                1. Focus only on user-relevant insights and facts - not just message intent or general info.
                2. Avoid greetings, signatures, or irrelevant fluff.
                3. Do not restate the entire message - infer and translate its implications about the user.
                4. Only output a single paragraph (max 5 lines), no formatting, no headings, no bullet points, no JSON.
                5. Output should feel like a meaningful note about the user - something Omi should remember forever.

                EXAMPLE OF GOOD OUTPUT:
                User has agreed to review the new PR for the mobile SDK before Friday and is working closely with Alex on the integration.
                They've taken ownership of the testing phase and will push the final patch after internal QA.
                This shows their active involvement in mobile development tasks and their coordination with team leads.
                A clear deadline and dependency chain exists, which may affect other deliverables.
                The user's focus is currently on resolving SDK-related issues efficiently and collaboratively.

                Final output should be clear, highly contextual, and framed as memory for a personal assistant.
                """

        prompt = OmiActionService.compose_email_text(email, classification)

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )

        summary = response.choices[0].message.content.strip()
        return summary
