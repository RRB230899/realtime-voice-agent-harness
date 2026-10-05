# Architecture

## How it works

`main.py` asks Twilio's REST API to place a recorded, dual-channel outbound
call to the test line. When the call connects, Twilio fetches TwiML from our
FastAPI server (`/twiml`) which tells it to open a Media Stream websocket
back to `/media`, carrying the callee's audio as g711_ulaw at 8kHz and a
custom parameter naming the scenario. The bridge then opens a second
websocket to the OpenAI Realtime API, configures the session with the
scenario's persona instructions, voice, and server-side VAD, and pumps audio
in both directions. Because the Realtime API natively accepts and emits
g711_ulaw, audio passes through untouched — no transcoding step, no added
latency, and no resampling artifacts on an 8kHz phone line. Transcripts of
both sides come from Realtime conversation events (input-audio transcription
for their agent, output transcripts for our bot) and are written live to a
timestamped file per call; the audio deliverable is Twilio's own dual-channel
recording, fetched after hangup.

## Why these choices

**Speech-to-speech Realtime API over an STT→LLM→TTS pipeline.** The graded
bar is a natural conversation, and the hardest parts of that are turn-taking
and barge-in recovery. A pipeline (e.g. Deepgram → GPT → ElevenLabs) is
cheaper and gives finer control, but you own the VAD, interruption logic,
and latency budget across three vendors; getting that to sound human in a
6-hour project is the risk. The Realtime API handles voice activity
detection, turn-taking, and mid-utterance cancellation natively, at ~$0.40-0.50
per call — well within the budget. Frameworks like Pipecat solve the same
problem but add a dependency to learn and debug; with only one transport
(Twilio) and one model, a direct ~150-line bridge was simpler than the
framework would have been.

**Local server + ngrok over a cloud deploy.** Twilio needs a public wss URL,
but nothing else about the problem needs infrastructure. A tunnel to a local
FastAPI process gives sub-second iteration (edit scenario → hot reload →
call again), which mattered more than uptime for a test harness; a static
ngrok domain keeps the URL stable across restarts.

**Dual-channel recording was a deliberate choice**, not a default: with the
agent on the left channel and our bot on the right, ffmpeg silence-detection
per channel yields each side's speech segments, which is how the bug report
quantifies overlaps, response latencies, and dead air without guessing from 
a mixed track. `analysis/channel_timing.py` runs this on every recording
and writes per-call results to `output/metrics/`.

## What we iterated on after hearing early calls

- **Turn-taking:** VAD silence threshold 600ms → 900ms after call 1, where
  the bot barged into a natural mid-greeting pause and caused ~12s of
  overlap reconciliation. Channel analysis (`output/metrics/summary.md`)
  shows the bot talking over the agent once in call 1 and not at all in
  10 of the 11 later calls. The exception is the insurance call, where a
  1.4s pause inside one of the agent's answers beat the 900ms threshold
  and the two sides collided four times in ten seconds (Bug 4).
- **Language handling:** the agent's Spanish IVR menu trapped an early call
  in a Spanish loop; personas now insist on English and have an explicit
  anti-repetition rule.
- **Caller-ID collisions:** the test system binds our number to the first
  registered profile ("Am I speaking with Margaret?"); personas answer the
  mix-up in one line and move on instead of burning a minute.
- **Persona voices:** each scenario now pins a gender/age-appropriate
  Realtime voice after a male persona shipped with a female voice.
- **The record wall:** once we learned new identities can't book (Bug 7),
  record-dependent scenarios pivoted to run as the one registered profile,
  which is what finally exercised the real scheduling, cancellation, and
  refill logic.
- **Recording races:** Twilio lists a recording before its media is
  encoded; the downloader now waits for `status=completed` and retries the
  media fetch on 404.

## Known limitations

True barge-in (our bot interrupting the agent mid-sentence) is limited by
server-VAD turn gating — the bot yields when the agent speaks, so
"interruption" scenarios test rapid turn exchange rather than sustained
overlap. Transcript line ordering is by event arrival, so a fast reply can
occasionally print before the utterance it answers (timestamps remain
correct). And all calls originate from one number, so the test system's
caller-ID profile binding shapes every conversation after the first — a
constraint we turned into test coverage rather than an obstacle.

A fixed silence threshold cannot tell a pause from a finished turn. Raising
it from 600ms to 900ms removed the barge-in on short pauses, but an agent
that pauses for more than 900ms mid-answer still gets interrupted, and
because both sides then yield and retry on similar timers they can collide
repeatedly (Bug 4). Semantic turn detection, or a randomized backoff after a
collision, would address this; neither is implemented.

Transcripts are speech-recognition output over 8kHz phone audio, so uncommon
proper nouns vary between calls (one provider's name appears four different
ways). Any finding that depends on exact wording should be checked against
the recording.
