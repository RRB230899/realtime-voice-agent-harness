"""Places outbound calls via Twilio REST API and downloads recordings."""
import os
import time

import httpx
from twilio.rest import Client

from . import config

TERMINAL_STATUSES = {"completed", "failed", "busy", "no-answer", "canceled"}


def get_client() -> Client:
    # API Key auth: Client(key_sid, key_secret, account_sid)
    return Client(
        config.TWILIO_API_KEY_SID,
        config.TWILIO_API_KEY_SECRET,
        config.TWILIO_ACCOUNT_SID,
    )


def place_call(scenario_key: str) -> str:
    """Start a recorded outbound call to the test line. Returns the call SID.

    The scenario travels as a query param on the TwiML URL; the server
    forwards it into the media stream as a custom parameter.
    """
    client = get_client()
    call = client.calls.create(
        to=config.TARGET_NUMBER,
        from_=config.TWILIO_FROM_NUMBER,
        url=f"{config.PUBLIC_URL}/twiml?scenario={scenario_key}",
        method="POST",
        record=True,
        recording_channels="dual",  # bot on one channel, their agent on the other
        time_limit=240,  # hard cap: keeps a runaway call from burning credit
    )
    return call.sid


def hangup(call_sid: str) -> None:
    """Force-end an in-progress call (kill switch for stuck loops)."""
    get_client().calls(call_sid).update(status="completed")


def wait_for_completion(call_sid: str, poll_s: int = 3, timeout_s: int = 360) -> str:
    """Poll until the call reaches a terminal status. Returns final status."""
    client = get_client()
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        status = client.calls(call_sid).fetch().status
        if status in TERMINAL_STATUSES:
            return status
        time.sleep(poll_s)
    return "timeout"


def download_recording(call_sid: str, retries: int = 10, delay_s: int = 3) -> str:
    """Download the call recording as MP3 (recordings appear with a short
    lag after hangup, hence the retry loop). Returns the local path."""
    client = get_client()
    recordings = []
    for _ in range(retries):
        recordings = client.recordings.list(call_sid=call_sid, limit=1)
        if recordings:
            break
        time.sleep(delay_s)
    if not recordings:
        raise RuntimeError(f"No recording found for call {call_sid}")

    url = (
        "https://api.twilio.com/2010-04-01/Accounts/"
        f"{config.TWILIO_ACCOUNT_SID}/Recordings/{recordings[0].sid}.mp3"
    )
    resp = httpx.get(
        url,
        auth=(config.TWILIO_API_KEY_SID, config.TWILIO_API_KEY_SECRET),
        follow_redirects=True,
        timeout=60,
    )
    resp.raise_for_status()

    os.makedirs(config.RECORDINGS_DIR, exist_ok=True)
    path = os.path.join(config.RECORDINGS_DIR, f"{call_sid}.mp3")
    with open(path, "wb") as f:
        f.write(resp.content)
    return path
