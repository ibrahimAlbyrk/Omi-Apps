import os
import pickle
import Logger
from Logger import LoggerType, FormatterType
from email_service import GmailService
from thread_manager import thread_manager
from google_auth_oauthlib.flow import Flow
from action_service import OmiActionService
from new_emails_monitor import process_new_emails
from flask import Flask, request, redirect, session, render_template, jsonify
from Database import SQLiteDatabaseManager, UserRepository
from classification_service import AIClassificationService
from Config import APP_SECRET_KEY, GOOGLE_CLIENT_SECRET, REDIRECT_URI, GMAIL_SCOPES, BASE_URI

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
@app.route("/")
def index():
    uid = request.args.get("uid")

    if not uid:
        return "OPS! There is no UID :(", 400

    session["uid"] = uid

    if user_repository.has_user(uid):
        return redirect(f"/logged-in?uid={uid}")

    return render_template("index.html")

@app.route("/login", methods=["POST"])
def login():
    uid = session["uid"]

    if not uid:
        return "OPS! There is no UID :(", 400

    flow = Flow.from_client_secrets_file(
        client_secrets_file=GOOGLE_CLIENT_SECRET,
        scopes=GMAIL_SCOPES,
        redirect_uri=REDIRECT_URI
    )
    auth_url, _ = flow.authorization_url(prompt="consent")
    response = jsonify({
        "auth_url": auth_url,
        "uid": uid
    })
    return response

@app.route("/logged-in")
def logged_in():
    uid = request.args.get("uid")
    session["uid"] = uid
    return render_template("index.html", uid=uid)

@app.route("/logout", methods=["POST"])
def logout():
    uid = session["uid"]
    print(uid)
    if not uid:
        return "OPS! There is no UID :(", 401

    # region Get Credentials
    token_path = user_repository.get_credentials(uid)
    if not token_path:
        return "Error: No stored credentials.", 402

    with open(token_path, "rb") as token_file:
        credentials = pickle.load(token_file)

    if not credentials or not credentials.valid:
        return "Error: No stored credentials.", 403
    # endregion

    # region core logout
    session.pop("uid", None)
    user_repository.delete_user(uid)

    gmail_service = GmailService(credentials, thread_manager)
    gmail_service.stop_listening(uid)
    # endregion

    url = f"{BASE_URI}/?uid={uid}"

    return jsonify({"url": url})


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

    return redirect("/logged-in")


@app.route("/get-settings", methods=["GET"])
def get_settings():
    uid = session.get("uid")
    if not uid:
        return "Missing UID", 400

    user = user_repository.get_user_settings(uid)
    if not user:
        return jsonify({"mail_check_interval": 60, "mail_count": 3})

    return jsonify({
        "mail_check_interval": user["mail_check_interval"],
        "mail_count": user["mail_count"]
    })


@app.route("/update-settings", methods=["POST"])
def update_settings():
    uid = session.get("uid")
    if not uid:
        return "Missing UID", 400

    data = request.get_json()
    mail_interval = data.get("mail_check_interval")
    mail_count = data.get("mail_count")

    if not isinstance(mail_interval, int) or not isinstance(mail_count, int):
        return "Invalid data types", 400

    user = user_repository.get_user(uid)

    token_path = user["google_credentials"]

    with open(token_path, "rb") as token_file:
        credentials = pickle.load(token_file)

    gmail_service = GmailService(credentials, thread_manager)
    gmail_service.stop_listening(uid)

    user_repository.update_user_settings(uid, mail_interval, mail_count)

    start_listening_mail(uid, credentials)

    return jsonify({"status": "success"})


@app.route("/setup-complete")
def is_setup_completed():
    uid = request.args.get("uid")

    if not uid:
        return "OPS! There is no UID :(", 400

    has_user = user_repository.has_user(uid)

    return {'is_setup_completed': has_user}
#endregion


def start_listening_all_users():
    users = user_repository.get_all_users()

    for user in users:
        start_listening_user(user)


def start_listening_user(user):
    if not user:
        return

    uid = user["uid"]
    token_path = user["google_credentials"]

    with open(token_path, "rb") as token_file:
        credentials = pickle.load(token_file)

    start_listening_mail(uid, credentials)


def start_listening_mail(uid: str, credentials: str):
    gmail_service = GmailService(credentials, thread_manager)

    if gmail_service.is_listening(uid):
        return

    settings = user_repository.get_user_settings(uid)

    interval = settings["mail_check_interval"]
    max_results = settings["mail_count"]

    gmail_service.start_listening(
        uid,
        callback=lambda emails: process_new_emails(uid, emails),
        unread_only=False,
        interval=interval,
        max_results=max_results
    )


if __name__ == '__main__':
    start_listening_all_users()
    app.run(host='127.0.0.1', port=5000, debug=False, ssl_context="adhoc")
