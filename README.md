# Voice Bot Tester — [vendor] Challenge

Automated "patient" voice bot that calls [vendor]'s test line
(+1-XXX-XXX-XXXX), holds realistic conversations with their AI agent,
records/transcribes every call, and logs bugs.

## Stack

Twilio (outbound calls + Media Streams) ↔ FastAPI websocket bridge ↔
OpenAI Realtime API (speech-to-speech). Audio stays g711_ulaw end-to-end.

## Setup

1. `./setup.sh` — creates `.venv`, installs deps, creates `.env`
2. Fill in `.env` (see `.env.example` for required keys)
3. Start ngrok: `ngrok http 8080` → put the https URL in `.env` as `PUBLIC_URL`

## Run

```bash
source .venv/bin/activate
uvicorn app.server:app --port 8080          # terminal 1
python -m app.main --scenario schedule_simple  # terminal 2
```

<!-- TODO: single-command runner, scenario list, outputs description -->

## Outputs

- `output/transcripts/` — per-call transcripts (both sides)
- `output/recordings/` — MP3 recordings
- `BUG_REPORT.md` — issues found in the agent

## Docs

- [ARCHITECTURE.md](ARCHITECTURE.md) — design and tradeoffs
