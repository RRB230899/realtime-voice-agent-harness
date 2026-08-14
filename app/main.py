"""Entry point.

Usage (ngrok + server must be running):
    python -m app.main --scenario schedule_simple

Flow: place a recorded call => wait for it to finish => download the MP3.
The transcript is written live by the server into output/transcripts/.
"""
import argparse
import sys

from . import call_manager, config
from .scenarios import SCENARIOS


def main() -> int:
    parser = argparse.ArgumentParser(description="Voice-bot test caller")
    parser.add_argument("--scenario", choices=SCENARIOS.keys())
    parser.add_argument("--hangup", metavar="CALL_SID",
                        help="force-end a stuck call and exit")
    args = parser.parse_args()

    if args.hangup:
        call_manager.hangup(args.hangup)
        print(f"Hung up {args.hangup}")
        return 0
    if not args.scenario:
        parser.error("--scenario is required (unless using --hangup)")

    missing = config.validate()
    if missing:
        print(f"Missing env vars: {', '.join(missing)} - edit .env", file=sys.stderr)
        return 1

    sid = call_manager.place_call(args.scenario)
    print(f"Dialing {config.TARGET_NUMBER} (call {sid}, scenario '{args.scenario}')")
    print("Live transcript appears in the server terminal...")

    status = call_manager.wait_for_completion(sid)
    print(f"Call ended: {status}")
    if status != "completed":
        print("Call did not complete normally; check server logs.", file=sys.stderr)
        return 1

    path = call_manager.download_recording(sid)
    print(f"Recording: {path}")
    print("Transcript: output/transcripts/ (latest file)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
