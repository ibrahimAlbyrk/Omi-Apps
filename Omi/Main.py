import json
import os
import pickle
import logging
import Logger
import memory_converter
from Logger import LoggerType, FormatterType
from email_service import GmailService
from thread_manager import thread_manager
from google_auth_oauthlib.flow import Flow
from action_service import OmiActionService
from new_emails_monitor import process_new_emails
from flask import Flask, request, redirect, session, render_template, jsonify
from Database import SQLiteDatabaseManager, UserRepository
from classification_service import AIClassificationService
from Config import APP_SECRET_KEY, GOOGLE_CLIENT_SECRET, REDIRECT_URI, GMAIL_SCOPES, BASE_URI, ERROR_RESPONSES

" -------------- SETUP -------------- "
#region setup
app = Flask(__name__)
app.secret_key = APP_SECRET_KEY

flaskLogger = logging.getLogger('werkzeug')
flaskLogger.setLevel(logging.ERROR)

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
        return ERROR_RESPONSES["NO_UID"]

    session["uid"] = uid

    has_user = user_repository.has_user(uid)
    is_logged_in = user_repository.is_logged_in(uid)

    if has_user and is_logged_in:
        return redirect(f"/logged-in?uid={uid}")

    return render_template("index.html")


@app.route("/privacy-policy")
def privacy_policy():
    return render_template("index.html")


@app.route("/terms-of-service")
def terms_of_service():
    return render_template("index.html")


@app.route("/login", methods=["POST"])
def login():
    uid = session["uid"]

    if not uid:
        return ERROR_RESPONSES["NO_UID"]

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

    if not uid:
        return ERROR_RESPONSES["NO_UID"]

    logger.info(f"User logged in: {uid}")

    session["uid"] = uid
    return render_template("index.html", uid=uid)

@app.route("/logout", methods=["POST"])
def logout():
    uid = session["uid"]
    if not uid:
        return ERROR_RESPONSES["NO_UID"]

    # region Get Credentials
    token_path = user_repository.get_credentials(uid)
    if not token_path:
        return ERROR_RESPONSES["NO_CREDENTIALS"]

    with open(token_path, "rb") as token_file:
        credentials = pickle.load(token_file)

    if not credentials:
        os.remove(token_path)
        return ERROR_RESPONSES["NO_VALID_CREDENTIALS"]
    # endregion

    gmail_service = GmailService(credentials, thread_manager)
    gmail_service.stop_listening(uid)
    # endregion

    user_repository.set_logged_in(uid, False)

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

    if not session:
        return ERROR_RESPONSES["SESSION_EXPIRED"]
    uid = session.get("uid")
    if not uid:
        return ERROR_RESPONSES["NO_UID"]

    start_listening_mail(uid, credentials)

    # region Update database
    if not os.path.exists("tokens"):
        os.makedirs("tokens")

    token_path = f"tokens/{uid}.pickle"
    with open(token_path, "wb") as token_file:
        pickle.dump(credentials, token_file)

    if not user_repository.has_user(uid):
        user_repository.add_user(uid, token_path)
    else:
        user_repository.update_credentials(uid, token_path)

    user_repository.set_logged_in(uid, True)
    # endregion

    return redirect(f"/logged-in?uid={uid}")


@app.route("/get-settings", methods=["GET"])
def get_settings():
    uid = request.args.get("uid")
    if not uid:
        return ERROR_RESPONSES["MISSING_UID"]

    settings = user_repository.get_user_settings(uid)
    if not settings:
        return jsonify(
            {
                "mail_check_interval": 60,
                "mail_count": 3,
                "important_categories" : AIClassificationService.DEFAULT_IMPORTANT_CATEGORIES,
                "ignored_categories" : AIClassificationService.DEFAULT_IGNORED_CATEGORIES,
             })

    return jsonify({
        "mail_check_interval": settings["mail_check_interval"],
        "mail_count": settings["mail_count"],
        "important_categories": settings["important_categories"],
        "ignored_categories": settings["ignored_categories"],
    })


@app.route("/update-settings", methods=["POST"])
def update_settings():
    uid = request.args.get("uid")
    if not uid:
        return ERROR_RESPONSES["MISSING_UID"]

    data = request.get_json()
    mail_interval = data.get("mail_check_interval")
    mail_count = data.get("mail_count")
    important_categories = data.get("important_categories")
    ignored_categories = data.get("ignored_categories")

    if not isinstance(mail_interval, int) or not isinstance(mail_count, int):
        return ErrorResponses.INVALID_DATA

    user = user_repository.get_user(uid)

    token_path = user["google_credentials"]

    with open(token_path, "rb") as token_file:
        credentials = pickle.load(token_file)

    gmail_service = GmailService(credentials, thread_manager)
    gmail_service.stop_listening(uid)

    user_repository.update_user_settings(uid, mail_interval, mail_count, important_categories, ignored_categories)

    start_listening_mail(uid, credentials)

    return jsonify({"status": "success"})

@app.route("/get-email-subjects", methods=["GET"])
def get_email_subjects():
    uid = request.args.get("uid")
    offset = int(request.args.get("offset"))
    limit = int(request.args.get("limit"))

    if not uid:
        return ERROR_RESPONSES["MISSING_UID"]

    user = user_repository.get_user(uid)

    token_path = user.get("google_credentials", None)

    if not token_path:
        return ERROR_RESPONSES["WENT_WRONG"]

    with open(token_path, "rb") as token_file:
        credentials = pickle.load(token_file)

    gmail_service = GmailService(credentials, thread_manager)
    subjects = gmail_service.fetch_email_subjects_paginated(offset, limit)

    return jsonify({"subjects": subjects})

@app.route("/convert-to-memory", methods=["POST"])
def convert_to_memories():
    uid = request.args.get("uid")
    if not uid:
        return ERROR_RESPONSES["NO_UID"]

    logger.info(f"User created memory: {uid}")

    data = request.get_json()

    user = user_repository.get_user(uid)
    token_path = user["google_credentials"]

    with open(token_path, "rb") as token_file:
        credentials = pickle.load(token_file)

    mode = data.get("mode", "count")

    if mode == "count":
        mail_count = int(data.get("count", None))
        if not mail_count:
            return ERROR_RESPONSES["INVALID_MAIL_COUNT"]
        memories = memory_converter.convert_with_email_count(uid, credentials, thread_manager, mail_count)
        return jsonify({"memories": memories})

    elif mode == "selection":
        selected_emails = data.get("selectedSubjects", [])
        selected_ids = [item["id"] for item in selected_emails]
        if not selected_ids:
            return ERROR_RESPONSES["INVALID_DATA"]

        memories = memory_converter.convert_with_selected_ids(uid, credentials, thread_manager, selected_ids)
        return jsonify({"memories": memories})

    return ERROR_RESPONSES["INVALID_DATA"]


@app.route("/setup-complete")
def is_setup_completed():
    uid = request.args.get("uid")
    if not uid:
        return ERROR_RESPONSES["NO_UID"]

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
    important_categories = settings["important_categories"]
    ignored_categories = settings["ignored_categories"]

    gmail_service.start_listening(
        uid,
        callback=lambda emails: process_new_emails(uid, emails, important_categories, ignored_categories),
        unread_only=False,
        interval=interval,
        max_results=max_results
    )


if __name__ == '__main__':
    start_listening_all_users()
    app.run(host='127.0.0.1', port=5000, debug=False, ssl_context="adhoc")
