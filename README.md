# Voice Bot Tester — [vendor] Challenge

An automated "patient" that calls [vendor]'s test line,
role-plays realistic scenarios against their AI phone agent, records and
transcribes both sides of every call, and documents the bugs it finds.

Built with Twilio (outbound calls + Media Streams) bridged to the OpenAI
Realtime API (speech-to-speech). See [ARCHITECTURE.md](ARCHITECTURE.md) for
design decisions and [BUG_REPORT.md](BUG_REPORT.md) for findings.

## Prerequisites

- Python 3.11+
- A Twilio account with a purchased phone number
- An OpenAI API key (Realtime API access, prepaid credits)
- [ngrok](https://ngrok.com) (free account) — exposes the local websocket
  server so Twilio can stream call audio to it

## Setup (one time)

```bash
./setup.sh          # creates .venv, installs deps, creates .env
```

Fill in `.env` (template documents every variable — see `.env.example`):

| Variable | Where to get it |
|---|---|
| `TWILIO_ACCOUNT_SID` | Twilio Console → Account Info |
| `TWILIO_API_KEY_SID` / `TWILIO_API_KEY_SECRET` | Console → API keys & tokens → Create API key (Standard) |
| `TWILIO_FROM_NUMBER` | Your purchased Twilio number, E.164 |
| `OPENAI_API_KEY` | platform.openai.com → API keys |
| `PUBLIC_URL` | Your ngrok forwarding URL (below) |

Start the tunnel (keep it running; a free static domain avoids re-editing .env):

```bash
ngrok http --url=<your-static-domain>.ngrok-free.app 8080
```

## Run

One command per test call:

```bash
./run.sh schedule_simple
```

This starts the bridge server if needed, dials the test line, streams the
conversation (live transcript in the server log / terminal), then downloads
the MP3 recording when the call completes.

Scenario keys (personas + goals defined in `app/scenarios.py`):
`schedule_simple`, `reschedule`, `cancel_appointment`, `refill_request`,
`office_info`, `weekend_booking`, `vague_patient`, `contradictor`,
`impatient_patient`, `emergency_mention`, `double_identity`,
`insurance_verification`, `workers_comp_injury`, `post_op_concern`,
`off_topic_medical_advice`.

Utilities:

```bash
python -m app.main --hangup   <CALL_SID>   # force-end a stuck call
python -m app.main --download <CALL_SID>   # (re)download a recording
```

## Outputs

- `output/transcripts/call-<timestamp>-<scenario>.txt` — timestamped
  transcript of both sides (`AGENT` / `PATIENT-BOT`)
- `output/recordings/<CallSid>.mp3` — dual-channel audio (agent left,
  bot right — which enables the channel-level timing analysis cited in
  the bug report)
- `BUG_REPORT.md` — all findings with severity, call references, and
  timestamps

## Project layout

```
app/
  main.py           CLI entry — places calls, downloads recordings
  server.py         FastAPI: TwiML endpoint + Twilio<->OpenAI websocket bridge
  call_manager.py   Twilio REST: place/hangup/poll calls, fetch recordings
  scenarios.py      15 patient personas/goals + session instruction builder
  transcripts.py    per-call transcript writer
  config.py         env loading + validation
```
