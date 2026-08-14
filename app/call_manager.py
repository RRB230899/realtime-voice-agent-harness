"""Places outbound calls via Twilio REST API and downloads recordings.

TODO:
    place_call(scenario_key): create call with record=True (dual-channel),
    TwiML url = {PUBLIC_URL}/twiml
    download_recording(call_sid): fetch MP3 into output/recordings/
"""
from twilio.rest import Client

from . import config


def get_client() -> Client:
    # API Key auth: Client(key_sid, key_secret, account_sid)
    return Client(
        config.TWILIO_API_KEY_SID,
        config.TWILIO_API_KEY_SECRET,
        config.TWILIO_ACCOUNT_SID,
    )


def place_call(scenario_key: str) -> str:
    """Start an outbound call to the test line. Returns the call SID."""
    raise NotImplementedError  # TODO


def download_recording(call_sid: str) -> str:
    """Download the call recording as MP3. Returns the local path."""
    raise NotImplementedError  # TODO
