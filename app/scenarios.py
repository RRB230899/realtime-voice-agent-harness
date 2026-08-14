"""Patient scenarios the bot role-plays on each call.

Each scenario is a persona + goal that gets injected into the Realtime API
session instructions. TODO: flesh out to 10+ diverse scenarios covering
scheduling, rescheduling/cancel, refills, hours/location/insurance questions,
and edge cases (interruptions, vague requests, contradictions).
"""

SCENARIOS: dict[str, dict] = {
    "schedule_simple": {
        "persona": "Margaret Chen, 58, polite, slightly hard of hearing",
        "goal": "Book a routine check-up for next week, prefers mornings.",
        "edge": None,
    },
    "reschedule": {
        "persona": "TODO",
        "goal": "TODO",
        "edge": None,
    },
    "refill_request": {
        "persona": "TODO",
        "goal": "TODO",
        "edge": None,
    },
    "weekend_booking": {
        "persona": "TODO",
        "goal": "Try to book Sunday 10am — office should be closed weekends.",
        "edge": "invalid_time",
    },
    # TODO: add ~6 more (insurance question, interruption test, unclear
    # mumbling patient, contradiction mid-call, off-topic request, etc.
}


def build_instructions(scenario_key: str) -> str:
    """Render a scenario into system instructions for the Realtime session."""
    s = SCENARIOS[scenario_key]
    return (
        "You are role-playing a patient calling a medical office's AI phone "
        f"agent. Persona: {s['persona']}. Your goal: {s['goal']} "
        "Speak ONLY English at all times, even if the agent speaks another "
        "language or offers a language menu — say you'd like to continue in "
        "English. Never repeat the same sentence twice in a row; if the "
        "conversation loops, break the loop by rephrasing or moving to your "
        "goal directly. Speak naturally with brief, conversational turns. "
        "Never reveal you are an AI. Let the agent lead when appropriate, "
        "but steer toward your goal. End the call politely once your goal "
        "is resolved or clearly cannot be."
    )
