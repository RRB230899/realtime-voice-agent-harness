# Architecture

<!-- TODO: finalize after implementation. Draft reasoning below. -->

The bot places an outbound Twilio call to the test line with dual-channel
recording enabled. When the call connects, Twilio fetches TwiML from our
FastAPI server and opens a Media Stream websocket carrying the callee's
audio (g711_ulaw, 8kHz). The server bridges that stream to an OpenAI
Realtime API session configured with a patient persona/scenario. Because
the Realtime API natively accepts and emits g711_ulaw, audio passes
through unmodified in both directions — no transcoding, minimal latency.
Transcripts of both sides come from Realtime conversation events; audio
deliverables come from Twilio's call recording.

Key choice — Realtime API over an STT→LLM→TTS pipeline: turn-taking and
barge-in handling are the hardest parts of a natural-sounding voice bot,
and the Realtime API's server-side VAD handles them out of the box. A
pipeline is cheaper and more controllable, but the grading bar here is
conversation naturalness, which favors speech-to-speech.

<!-- TODO: tradeoffs on frameworks (Pipecat), infra (ngrok vs deploy),
cost notes -->
