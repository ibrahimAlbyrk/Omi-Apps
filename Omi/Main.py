from Gmail import Gmail
from dotenv import load_dotenv
from Actions import OmiActions
from OpenAI.EmailClassifier import EmailClassifier

load_dotenv()

Gmail = Gmail.GmailClient()
OmiActions = OmiActions.ActionClient('en')
EmailClassifier = EmailClassifier()

def main():
   emails = Gmail.fetch_emails(1)

   for email in emails:
       classify = EmailClassifier.classify_email_importance(email)
       answer = classify["answer"]
       if answer:
           success, status_code = OmiActions.send_email_to_conversations(email, classify)
           if not success:
               print(f"Failed to send email to Omi. HTTP Status: {status_code}")

if __name__ == '__main__':
    main()