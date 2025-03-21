import os
from enum import Enum
from dotenv import load_dotenv

load_dotenv()

BASE_URI = "https://mailmate.omi-wroom.org"

# APP
APP_SECRET_KEY = os.getenv("APP_SECRET_KEY")

# OPEN AI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OMI
OMI_API_KEY = os.getenv("OMI_API_KEY")
OMI_APP_ID = os.getenv("OMI_APP_ID")

# GOOGLE
REDIRECT_URI = "https://mailmate.omi-wroom.org/gmail-callback"
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# FILES
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")


# WEBHOOK
class ErrorResponses(Enum):
    NO_UID = ("OPS! There is no UID :(", 401)
    NO_CREDENTIALS = ("Error: No stored credentials.", 402)
    NO_VALID_CREDENTIALS = ("Error: No valid credentials found.", 403)
    SESSION_EXPIRED = ("Error:This session is over :(", 405)
    INVALID_DATA = ("Invalid data types", 406)
    MISSING_UID = ("Missing UID", 407)
