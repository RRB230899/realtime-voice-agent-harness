"""Per-call transcript files: both sides of the conversation with
elapsed-time markers (used by the bug report to reference moments)."""
import os
import time
from datetime import datetime

from . import config


class TranscriptWriter:
    def __init__(self, scenario_key: str, call_sid: str):
        os.makedirs(config.TRANSCRIPTS_DIR, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.path = os.path.join(
            config.TRANSCRIPTS_DIR, f"call-{stamp}-{scenario_key}.txt"
        )
        self._t0 = time.monotonic()
        with open(self.path, "w") as f:
            f.write(
                f"# Scenario: {scenario_key}\n"
                f"# Call SID: {call_sid}\n"
                f"# Started: {datetime.now().isoformat(timespec='seconds')}\n\n"
            )

    def add(self, speaker: str, text: str) -> None:
        """Append one utterance, e.g. `[1:23] AGENT: ...`"""
        text = (text or "").strip()
        if not text:
            return
        elapsed = int(time.monotonic() - self._t0)
        line = f"[{elapsed // 60}:{elapsed % 60:02d}] {speaker}: {text}\n"
        with open(self.path, "a") as f:
            f.write(line)
        print(line, end="", flush=True)

    def close(self, note: str = "") -> None:
        with open(self.path, "a") as f:
            f.write(f"\n# Ended: {datetime.now().isoformat(timespec='seconds')}")
            if note:
                f.write(f" ({note})")
            f.write("\n")
