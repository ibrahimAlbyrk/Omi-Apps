import os
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