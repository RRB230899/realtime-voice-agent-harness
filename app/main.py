"""Entry point.

Usage (after setup + ngrok running + server running):
    python -m app.main --scenario schedule_simple

TODO: 
    wire up argparse => place a call => wait => save transcript + recording
"""
import argparse
import sys

from . import config
from .scenarios import SCENARIOS


def main() -> int:
    parser = argparse.ArgumentParser(description="Voice-bot test caller")
    parser.add_argument("--scenario", choices=SCENARIOS.keys(), required=True)
    args = parser.parse_args()

    missing = config.validate()
    if missing:
        print(f"Missing env vars: {', '.join(missing)} - edit .env", file=sys.stderr)
        return 1

    print(f"TODO: place call for scenario '{args.scenario}'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
