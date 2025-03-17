import os
import json
import base64
import pickle
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from DB.Database import DatabaseManager, UserRepository
from flask import Flask, request, redirect, session, abort

from Gmail import Gmail

""" \/ -------------- SETUP -------------- \/ """
#region setup
app = Flask(__name__)
app.secret_key = "mailmate.omi-wroom.org"

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("CLIENT_SECRET_FILE")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.metadata",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid"]

REDIRECT_URI = "https://mailmate.omi-wroom.org/gmail-callback"

db = DatabaseManager()
user_repository = UserRepository(db)

flow = Flow.from_client_secrets_file(
    GOOGLE_CLIENT_SECRET,
    scopes=SCOPES,
    redirect_uri=REDIRECT_URI
)
#endregion

""" \/ -------------- WEBHOOK FUNCTIONS -------------- \/ """
#region webhook
@app.route("/login")
def login():
    uid = request.args.get("uid")

    if not uid:
        return "OPS! There is no UID :(", 400

    session["uid"] = uid

    auth_url, _ = flow.authorization_url(prompt="consent")
    return redirect(auth_url)


@app.route("/logout", methods=["POST"])
def logout():
    uid = session.get("uid")
    if not uid:
        return "Error: No user session found.", 400

    # region Get Credentials
    token_path = user_repository.get_credentials(uid)
    if not token_path:
        return "Error: No stored credentials.", 400

    with open(token_path, "rb") as token_file:
        credentials = pickle.load(token_file)

    if not credentials or not credentials.valid:
        return "Error: No stored credentials.", 400
    # endregion

    # region core logout
    session.pop("uid", None)
    user_repository.delete_user(uid)

    gmail_client = Gmail.GmailClient(uid, credentials=credentials)
    gmail_client.stop_gmail_listening()
    # endregion


@app.route("/gmail-callback")
def callback():
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials

    uid = session.get("uid")
    if not uid:
        return "Error: There is no uid :(", 400

    gmail_client = Gmail.GmailClient(uid, credentials=credentials)
    gmail_client.start_gmail_listening(new_emails_arrived)

    # region Update database
    if not os.path.exists("tokens"):
        os.makedirs("tokens")

    token_path = f"tokens/{uid}.pickle"
    with open(token_path, "wb") as token_file:
        pickle.dump(credentials, token_file)

    if user_repository.has_user(uid):
        user_repository.update_credentials(uid, token_path)
    else:
        user_repository.add_user(uid, token_path)
    # endregion

    return "Login is successful, infos are saved!"
#endregion

""" \/ -------------- EMAIL FUNCTIONS -------------- \/ """
#region mail
def new_emails_arrived(emails: []):
   for email in emails:
       classify = EmailClassifier.classify_email(email)
       answer = classify["answer"]
       if answer:
           success, status_code = OmiActions.send_email_to_conversations(email, classify)
           if not success:
               print(f"Failed to send email to Omi. HTTP Status: {status_code}")

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True, ssl_context="adhoc")
