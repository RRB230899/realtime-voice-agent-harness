"""Unit tests for the interval logic in analysis/channel_timing.py.

These use hand-written segments, so they need neither ffmpeg nor audio.
Run with:  python -m pytest
"""
import pytest

from analysis import channel_timing
from analysis.channel_timing import (
    AGENT, BOT, build_turns, find_dead_air, find_overlaps,
    response_latencies, speech_segments,
)


def test_speech_is_the_inverse_of_silence():
    silences = [(0.0, 1.0), (2.0, 3.0)]
    assert speech_segments(silences, duration=5.0) == [(1.0, 2.0), (3.0, 5.0)]


def test_blips_shorter_than_min_speech_are_dropped():
    silences = [(0.0, 1.0), (1.05, 4.0)]  # 50 ms of "speech" at 1.0
    assert speech_segments(silences, duration=4.0, min_speech=0.15) == []


def test_recording_that_ends_in_silence():
    silences = [(2.0, float("inf"))]
    assert speech_segments(silences, duration=5.0) == [(0.0, 2.0)]


def test_overlap_is_attributed_to_whoever_spoke_second():
    agent = [(0.0, 5.0)]
    bot = [(4.0, 6.0)]  # bot starts while the agent is still talking
    [overlap] = find_overlaps(agent, bot)
    assert (overlap["start"], overlap["end"]) == (4.0, 5.0)
    assert overlap["started_by"] == BOT

    [overlap] = find_overlaps(agent=[(4.0, 6.0)], bot=[(0.0, 5.0)])
    assert overlap["started_by"] == AGENT


def test_brief_collisions_are_ignored():
    assert find_overlaps([(0.0, 5.0)], [(4.9, 6.0)], min_overlap=0.2) == []


def test_consecutive_segments_merge_into_one_turn():
    agent = [(0.0, 2.0), (2.5, 4.0)]  # one turn with a pause in it
    bot = [(5.0, 6.0)]
    turns = build_turns(agent, bot)
    assert [(t["speaker"], t["start"], t["end"]) for t in turns] == [
        (AGENT, 0.0, 4.0), (BOT, 5.0, 6.0),
    ]


def test_latency_is_keyed_by_the_side_that_responds():
    turns = build_turns(agent=[(0.0, 4.0), (7.5, 9.0)], bot=[(5.0, 6.0)])
    latency = response_latencies(turns)
    assert latency[BOT] == [1.0]    # bot answered 1.0 s after the agent
    assert latency[AGENT] == [1.5]  # agent answered 1.5 s after the bot


def test_overlapping_handoffs_are_not_counted_as_latency():
    turns = build_turns(agent=[(0.0, 5.0)], bot=[(4.0, 6.0)])
    assert response_latencies(turns) == {AGENT: [], BOT: []}


def test_dead_air_is_a_gap_where_neither_side_speaks():
    agent = [(0.0, 2.0), (9.0, 10.0)]
    bot = [(2.5, 4.0)]
    assert find_dead_air(agent, bot, min_gap=3.0) == [(4.0, 9.0)]


def test_missing_ffmpeg_is_reported_clearly(monkeypatch, capsys):
    monkeypatch.setattr(channel_timing.shutil, "which", lambda tool: None)
    monkeypatch.setattr("sys.argv", ["channel_timing"])
    with pytest.raises(SystemExit):
        channel_timing.main()
    assert "ffmpeg and ffprobe not found" in capsys.readouterr().err
