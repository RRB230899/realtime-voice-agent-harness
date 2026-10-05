"""Per-channel timing analysis of dual-channel call recordings.

Twilio records every call in stereo: the agent under test on the left
channel and the caller bot on the right. Running ffmpeg's `silencedetect`
on each channel separately yields each party's speech segments with no
diarization step, and from those segments:

  - overlapping speech, and which side started talking over the other
  - turn-taking latency in both directions
  - dead air (stretches where neither side speaks)

Usage:
    python -m analysis.channel_timing              # every recording -> output/metrics/
    python -m analysis.channel_timing <CALL_SID>   # one call, print its events

Requires the `ffmpeg` and `ffprobe` binaries on PATH. No Python dependencies.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import statistics
import subprocess
from pathlib import Path

RECORDINGS_DIR = Path("output/recordings")
TRANSCRIPTS_DIR = Path("output/transcripts")
METRICS_DIR = Path("output/metrics")

AGENT, BOT = "agent", "bot"
CHANNEL = {AGENT: 0, BOT: 1}  # left = agent under test, right = caller bot

# Detection thresholds. Phone audio is 8 kHz mu-law with a quiet noise floor,
# so -35 dB separates speech from line noise; 0.35 s is shorter than a
# conversational pause but longer than the gaps between words.
NOISE_DB = -35
MIN_SILENCE_S = 0.35
MIN_SPEECH_S = 0.15   # ignore clicks and breaths shorter than this
MIN_OVERLAP_S = 0.20  # ignore sub-200 ms collisions at turn boundaries
DEAD_AIR_S = 3.0      # a gap this long with nobody speaking counts as dead air

Segment = tuple[float, float]  # (start, end) in seconds


# --- ffmpeg ---------------------------------------------------------------

def probe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    return float(out.strip())


def detect_silences(path: Path, channel: int) -> list[Segment]:
    """Run silencedetect on one channel; return its silent intervals."""
    log = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af",
         f"pan=mono|c0=c{channel},"
         f"silencedetect=noise={NOISE_DB}dB:d={MIN_SILENCE_S}",
         "-f", "null", "-"],
        capture_output=True, text=True, check=True,
    ).stderr
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", log)]
    ends = [float(x) for x in re.findall(r"silence_end: (-?[\d.]+)", log)]
    # a recording that ends in silence has a start with no matching end
    ends += [float("inf")] * (len(starts) - len(ends))
    return [(max(s, 0.0), e) for s, e in zip(starts, ends)]


# --- pure interval logic (unit-tested in tests/test_channel_timing.py) -----

def speech_segments(silences: list[Segment], duration: float,
                    min_speech: float = MIN_SPEECH_S) -> list[Segment]:
    """Invert silent intervals into speech segments."""
    segments, cursor = [], 0.0
    for start, end in sorted(silences):
        if start - cursor >= min_speech:
            segments.append((cursor, start))
        cursor = max(cursor, min(end, duration))
    if duration - cursor >= min_speech:
        segments.append((cursor, duration))
    return segments


def find_overlaps(agent: list[Segment], bot: list[Segment],
                  min_overlap: float = MIN_OVERLAP_S) -> list[dict]:
    """Stretches where both sides speak. `started_by` is whoever began
    talking second, i.e. the side that talked over the other."""
    found = []
    for a_start, a_end in agent:
        for b_start, b_end in bot:
            start, end = max(a_start, b_start), min(a_end, b_end)
            if end - start >= min_overlap:
                found.append({
                    "start": start, "end": end,
                    "started_by": BOT if b_start > a_start else AGENT,
                })
    return sorted(found, key=lambda o: o["start"])


def build_turns(agent: list[Segment], bot: list[Segment]) -> list[dict]:
    """Merge both sides' segments into alternating speaker turns."""
    tagged = sorted([(s, e, AGENT) for s, e in agent] +
                    [(s, e, BOT) for s, e in bot])
    turns: list[dict] = []
    for start, end, speaker in tagged:
        if turns and turns[-1]["speaker"] == speaker:
            turns[-1]["end"] = max(turns[-1]["end"], end)
        else:
            turns.append({"speaker": speaker, "start": start, "end": end})
    return turns


def response_latencies(turns: list[dict]) -> dict[str, list[float]]:
    """Gap between one side finishing and the other starting, keyed by the
    side that responds. Overlapping hand-offs are counted as overlaps, not
    as zero-latency responses, so they are skipped here."""
    gaps: dict[str, list[float]] = {AGENT: [], BOT: []}
    for prev, nxt in zip(turns, turns[1:]):
        gap = nxt["start"] - prev["end"]
        if gap >= 0:
            gaps[nxt["speaker"]].append(gap)
    return gaps


def find_dead_air(agent: list[Segment], bot: list[Segment],
                  min_gap: float = DEAD_AIR_S) -> list[Segment]:
    """Gaps between the first and last speech where neither side speaks."""
    merged: list[list[float]] = []
    for start, end in sorted(agent + bot):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(a[1], b[0]) for a, b in zip(merged, merged[1:])
            if b[0] - a[1] >= min_gap]


# --- per-call analysis ------------------------------------------------------

def analyze(path: Path) -> dict:
    duration = probe_duration(path)
    segments = {
        side: speech_segments(detect_silences(path, ch), duration)
        for side, ch in CHANNEL.items()
    }
    agent, bot = segments[AGENT], segments[BOT]
    overlaps = find_overlaps(agent, bot)
    turns = build_turns(agent, bot)
    latency = response_latencies(turns)
    dead_air = find_dead_air(agent, bot)

    def total(spans):
        return sum(end - start for start, end in spans)

    def median(values):
        return statistics.median(values) if values else None

    return {
        "call_sid": path.stem,
        "duration_s": duration,
        "agent_talk_s": total(agent),
        "bot_talk_s": total(bot),
        "overlap_s": float(sum(o["end"] - o["start"] for o in overlaps)),
        "overlaps_started_by_bot": sum(o["started_by"] == BOT for o in overlaps),
        "overlaps_started_by_agent": sum(o["started_by"] == AGENT for o in overlaps),
        "bot_latency_median_s": median(latency[BOT]),
        "agent_latency_median_s": median(latency[AGENT]),
        "agent_latency_max_s": max(latency[AGENT], default=None),
        "dead_air_count": len(dead_air),
        "dead_air_longest_s": max((e - s for s, e in dead_air), default=0.0),
        "segments": segments,
        "overlaps": overlaps,
        "dead_air": dead_air,
    }


# --- reporting ---------------------------------------------------------------

def scenario_by_call_sid() -> dict[str, str]:
    """Map call SID -> transcript label, read from the transcript headers."""
    labels = {}
    for transcript in sorted(TRANSCRIPTS_DIR.glob("call-*.txt")):
        match = re.search(r"# Call SID: (\S+)", transcript.read_text())
        if match:
            labels[match.group(1)] = transcript.stem.removeprefix("call-")
    return labels


def clock(seconds: float) -> str:
    return f"{int(seconds // 60)}:{seconds % 60:04.1f}"


def fmt(value, digits: int = 1) -> str:
    return "-" if value is None else f"{value:.{digits}f}"


SUMMARY_COLUMNS = [
    ("call", "Call"), ("duration_s", "Length (s)"),
    ("agent_talk_s", "Agent talk (s)"), ("bot_talk_s", "Bot talk (s)"),
    ("overlap_s", "Overlap (s)"),
    ("overlaps_started_by_bot", "Bot talked over agent"),
    ("overlaps_started_by_agent", "Agent talked over bot"),
    ("bot_latency_median_s", "Bot latency, median (s)"),
    ("agent_latency_median_s", "Agent latency, median (s)"),
    ("agent_latency_max_s", "Agent latency, max (s)"),
    ("dead_air_count", f"Dead air >= {DEAD_AIR_S:g}s"),
    ("dead_air_longest_s", "Longest dead air (s)"),
]


def write_outputs(results: list[dict]) -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    for result in results:
        rounded = json.loads(json.dumps(result), parse_float=lambda x: round(float(x), 2))
        (METRICS_DIR / f"{result['call_sid']}.json").write_text(
            json.dumps(rounded, indent=2) + "\n")

    keys = [key for key, _ in SUMMARY_COLUMNS]
    rows = [[r[k] if isinstance(r[k], (str, int)) else fmt(r[k]) for k in keys]
            for r in results]
    with open(METRICS_DIR / "summary.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(keys)
        writer.writerows(rows)

    header = [title for _, title in SUMMARY_COLUMNS]
    lines = ["| " + " | ".join(header) + " |",
             "|" + "|".join(["---"] + ["---:"] * (len(header) - 1)) + "|"]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    (METRICS_DIR / "summary.md").write_text(
        "# Channel timing summary\n\n"
        f"Generated by `python -m analysis.channel_timing` "
        f"(silencedetect noise={NOISE_DB}dB, d={MIN_SILENCE_S}s).\n\n"
        + "\n".join(lines) + "\n")


def print_events(result: dict) -> None:
    print(f"{result['call']}  ({result['call_sid']}, {clock(result['duration_s'])})")
    for o in result["overlaps"]:
        print(f"  overlap  {clock(o['start'])}-{clock(o['end'])}  "
              f"{o['end'] - o['start']:.1f}s  started by {o['started_by']}")
    for start, end in result["dead_air"]:
        print(f"  dead air {clock(start)}-{clock(end)}  {end - start:.1f}s")
    for side in (AGENT, BOT):
        spans = "  ".join(f"{clock(s)}+{e - s:.1f}" for s, e in result["segments"][side])
        print(f"  {side:5s} speech: {spans}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("call_sid", nargs="?",
                        help="analyze one call and print its events")
    args = parser.parse_args()

    missing = [tool for tool in ("ffmpeg", "ffprobe") if shutil.which(tool) is None]
    if missing:
        parser.error(f"{' and '.join(missing)} not found on PATH. "
                     "Install ffmpeg, e.g. `brew install ffmpeg`.")

    labels = scenario_by_call_sid()
    paths = sorted(RECORDINGS_DIR.glob("*.mp3"),
                   key=lambda p: labels.get(p.stem, p.stem))
    if args.call_sid:
        paths = [p for p in paths if p.stem == args.call_sid]
        if not paths:
            parser.error(f"no recording for {args.call_sid} in {RECORDINGS_DIR}")

    results = []
    for path in paths:
        result = analyze(path)
        result["call"] = labels.get(path.stem, path.stem)
        results.append(result)

    if args.call_sid:
        print_events(results[0])
        return

    write_outputs(results)
    print((METRICS_DIR / "summary.md").read_text())


if __name__ == "__main__":
    main()
