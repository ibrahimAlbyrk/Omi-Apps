import os
import json
import openai
from Config import OPENAI_API_KEY
from action_service import OmiActionService


class IClassificationService:
    def classify_email(self, email: dict, important_categories: list, ignored_categories: list) -> dict:
        raise NotImplementedError


class ISummarizationService:
    def summarize_email(self, email: dict, classification: dict) -> str:
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

    def classify_email(self, email: dict, important_categories=None, ignored_categories=None) -> dict:
        if ignored_categories is None:
            ignored_categories = DEFAULT_IGNORED_CATEGORIES
        if important_categories is None:
            important_categories = DEFAULT_IMPORTANT_CATEGORIES

        prompt = (
            f"Mail Title: {email.get('subject', '')}\n"
            f"From: {email.get('from', '')}\n"
            f"Content: {email.get('body', '')[:1000]}"
        )
        system_prompt = f"""
                You are an advanced email classifier. Analyze the given email thoroughly based on:

                IMPORTANT CATEGORIES (exactly match the main purpose or intent): {', '.join(important_categories)}
                IGNORED CATEGORIES (emails that are promotional, generic, or low priority): {', '.join(ignored_categories)}

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
