import os
import pickle
from Database import UserRepository
from email_service import GmailService
from action_service import OmiActionService
from thread_manager import thread_manager
from google_auth_oauthlib.flow import Flow
from new_emails_monitor import process_new_emails
from flask import Flask, request, redirect, session
from classification_service import AIClassificationService
from Config import APP_SECRET_KEY, GOOGLE_CLIENT_SECRET, REDIRECT_URI, GMAIL_SCOPES

""" ⬇️ -------------- SETUP -------------- ⬇️ """
#region setup
app = Flask(__name__)
app.secret_key = APP_SECRET_KEY

db_manager = SQLiteDatabaseManager()
user_repository = UserRepository(db_manager)
classification_service = AIClassificationService()
#endregion

""" ⬇️ -------------- WEBHOOK FUNCTIONS -------------- ⬇️ """
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

    gmail_service = GmailService(credentials, thread_manager)
    gmail_service.start_listening(uid, lambda emails: process_new_emails(uid, emails))

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


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True, ssl_context="adhoc")
