# Fetch .env vars
import os
from dotenv import load_dotenv

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_API_KEY_SID = os.getenv("TWILIO_API_KEY_SID", "")
TWILIO_API_KEY_SECRET = os.getenv("TWILIO_API_KEY_SECRET", "")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")
TARGET_NUMBER = os.getenv("TARGET_NUMBER", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
PUBLIC_URL = os.getenv("PUBLIC_URL", "").rstrip("/")
PORT = int(os.getenv("PORT", "8080"))

OPENAI_REALTIME_MODEL = os.getenv("OPENAI_REALTIME_MODEL", "gpt-realtime")
OPENAI_REALTIME_URL = f"wss://api.openai.com/v1/realtime?model={OPENAI_REALTIME_MODEL}"
BOT_VOICE = os.getenv("BOT_VOICE", "marin")

# Output locations (committed to the repo)
TRANSCRIPTS_DIR = "output/transcripts"
RECORDINGS_DIR = "output/recordings"


def validate() -> list[str]:
    """Return a list of missing required env vars (empty = OK)."""
    required = {
        "TWILIO_ACCOUNT_SID": TWILIO_ACCOUNT_SID,
        "TWILIO_API_KEY_SID": TWILIO_API_KEY_SID,
        "TWILIO_API_KEY_SECRET": TWILIO_API_KEY_SECRET,
        "TWILIO_FROM_NUMBER": TWILIO_FROM_NUMBER,
        "TARGET_NUMBER": TARGET_NUMBER,
        "OPENAI_API_KEY": OPENAI_API_KEY,
        "PUBLIC_URL": PUBLIC_URL,
    }
    return [k for k, v in required.items() if not v]
