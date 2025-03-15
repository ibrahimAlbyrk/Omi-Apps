import os
import openai

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class EmailClassifier:
    def __init__(self):
        self.client = openai.Client(api_key=OPENAI_API_KEY)
        self.IMPORTANT_CATEGORIES = [
        "urgent",
        "meeting",
        "invoice",
        "payment due",
        "project update",
        "Github",
        "security alert",
        "password reset",
    ]

    def classify_email_importance(self, mail):
        """Uses OpenAI to classify if an email is important based on predefined criteria."""
        prompt =(
            f"""
            Mail Title: {mail['subject']}
            From: {mail['from']}
            Content: {mail['body'][:500]}

            Identify if this email belongs to any of the following important categories: {self.IMPORTANT_CATEGORIES}.
            Respond only with 'yes' or 'no'.
            """.strip()
        )

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Just answer 'yes' or 'no'."},
                {"role": "user", "content": prompt}
            ]
        )

        return response.choices[0].message.content.strip().lower() == "yes"