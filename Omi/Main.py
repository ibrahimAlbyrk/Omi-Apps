import os
import pickle
import Logger
from Logger import LoggerType, FormatterType
from email_service import GmailService
from thread_manager import thread_manager
from google_auth_oauthlib.flow import Flow
from action_service import OmiActionService
from new_emails_monitor import process_new_emails
from flask import Flask, request, redirect, session
from Database import SQLiteDatabaseManager, UserRepository
from classification_service import AIClassificationService
from Config import APP_SECRET_KEY, GOOGLE_CLIENT_SECRET, REDIRECT_URI, GMAIL_SCOPES

" -------------- SETUP -------------- "
#region setup
app = Flask(__name__)
app.secret_key = APP_SECRET_KEY

db_manager = SQLiteDatabaseManager()
user_repository = UserRepository(db_manager)
classification_service = AIClassificationService()

logger = Logger.Manager("Main", FormatterType.ADVANCED, LoggerType.CONSOLE)
#endregion

" -------------- WEBHOOK FUNCTIONS -------------- "
#region webhook
@app.route("/login")
def login():
    uid = request.args.get("uid")

    if not uid:
        return "OPS! There is no UID :(", 400

    flow = Flow.from_client_secrets_file(
        client_secrets_file=GOOGLE_CLIENT_SECRET,
        scopes=GMAIL_SCOPES,
        redirect_uri=REDIRECT_URI
    )
    auth_url, _ = flow.authorization_url(prompt="consent")
    session["uid"] = uid
    return redirect(auth_url)


@app.route("/logout", methods=["POST"])
def logout():
    uid = request.args.get("uid")
    if not uid:
        return "OPS! There is no UID :(", 400

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

    gmail_service = GmailService(credentials, thread_manager)
    gmail_service.stop_listening(uid)
    # endregion

    return "Logged out successfully."


@app.route("/gmail-callback")
def callback():
    flow = Flow.from_client_secrets_file(
        client_secrets_file=GOOGLE_CLIENT_SECRET,
        scopes=GMAIL_SCOPES,
        redirect_uri=REDIRECT_URI
    )

    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials

    uid = session.get("uid")
    if not uid:
        return "Error: There is no uid :(", 400

    start_listening_mail(uid, credentials)

    # region Update database
    if not os.path.exists("tokens"):
        os.makedirs("tokens")

    token_path = f"tokens/{uid}.pickle"
    with open(token_path, "wb") as token_file:
        pickle.dump(credentials, token_file)

    if not user_repository.has_user(uid):
        user_repository.add_user(uid, token_path)
    # endregion

    return "Login is successful!"
#endregion

def start_listening_all_users():
    users = user_repository.get_all_users()

    for user in users:
        uid = user["uid"]
        token_path = user["google_credentials"]

        with open(token_path, "rb") as token_file:
            credentials = pickle.load(token_file)

        start_listening_mail(uid, credentials)

def start_listening_mail(uid: str, credentials: str):
    gmail_service = GmailService(credentials, thread_manager)
    gmail_service.start_listening(
        uid,
        callback=lambda emails: process_new_emails(uid, emails),
        unread_only=True,
        interval=60,
        max_results=3
    )

if __name__ == '__main__':
    start_listening_all_users()
    app.run(host='127.0.0.1', port=5000, debug=False, ssl_context="adhoc")
