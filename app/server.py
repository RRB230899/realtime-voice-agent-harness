"""FastAPI server: serves TwiML for outbound calls and bridges
Twilio Media Streams <-> OpenAI Realtime API.

Data flow (both directions are raw g711_ulaw @ 8kHz — no transcoding):
    Twilio call audio --ws--> this server --ws--> OpenAI Realtime
    OpenAI speech     --ws--> this server --ws--> Twilio (played to callee)

Transcripts come from Realtime events: input-audio transcription for the
callee (their agent) and output transcripts for our bot.
"""
import asyncio
import json

import websockets
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response

from . import config
from .scenarios import build_instructions, get_voice
from .transcripts import TranscriptWriter

app = FastAPI()


@app.get("/health")
async def health():
    return {"ok": True, "missing_env": config.validate()}


@app.post("/twiml")
async def twiml(request: Request):
    """Twilio fetches this when the outbound call connects. It opens a
    media stream to /media, carrying the scenario as a custom parameter."""
    scenario = request.query_params.get("scenario", "schedule_simple")
    ws_url = config.PUBLIC_URL.replace("https://", "wss://") + "/media"
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="{ws_url}">
      <Parameter name="scenario" value="{scenario}" />
    </Stream>
  </Connect>
</Response>"""
    return Response(content=xml, media_type="text/xml")


@app.websocket("/media")
async def media(twilio_ws: WebSocket):
    await twilio_ws.accept()
    bridge = Bridge(twilio_ws)
    await bridge.run()


class Bridge:
    """One instance per call: pumps audio Twilio<->OpenAI, captures transcript."""

    def __init__(self, twilio_ws: WebSocket):
        self.twilio_ws = twilio_ws
        self.openai_ws = None
        self.stream_sid = None
        self.call_sid = "unknown"
        self.scenario_key = "schedule_simple"
        self.transcript = None
        self.response_active = False

    async def run(self):
        try:
            await self._await_start()
            self.transcript = TranscriptWriter(self.scenario_key, self.call_sid)
            await self._connect_openai()

            pump_up = asyncio.create_task(self._twilio_to_openai())
            pump_down = asyncio.create_task(self._openai_to_twilio())
            done, pending = await asyncio.wait(
                {pump_up, pump_down}, return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
            for task in done:
                exc = task.exception()
                if exc and not isinstance(exc, (WebSocketDisconnect,
                                                websockets.ConnectionClosed)):
                    print(f"[bridge] pump error: {exc!r}")
        except Exception as e:
            print(f"[bridge] fatal: {e!r}")
        finally:
            if self.transcript:
                self.transcript.close()
            if self.openai_ws:
                await self.openai_ws.close()
            try:
                await self.twilio_ws.close()
            except Exception:
                pass
            print(f"[bridge] call {self.call_sid} closed")

    async def _await_start(self):
        """Consume Twilio's opening events until `start` (has stream/call SIDs)."""
        while True:
            data = json.loads(await self.twilio_ws.receive_text())
            if data.get("event") == "start":
                start = data["start"]
                self.stream_sid = start["streamSid"]
                self.call_sid = start.get("callSid", "unknown")
                self.scenario_key = start.get("customParameters", {}).get(
                    "scenario", self.scenario_key
                )
                print(f"[bridge] call {self.call_sid} scenario={self.scenario_key}")
                return

    async def _connect_openai(self):
        self.openai_ws = await websockets.connect(
            config.OPENAI_REALTIME_URL,
            additional_headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
            max_size=1 << 24,
        )
        session_update = {
            "type": "session.update",
            "session": {
                "type": "realtime",
                "model": config.OPENAI_REALTIME_MODEL,
                "output_modalities": ["audio"],
                "instructions": build_instructions(self.scenario_key),
                "audio": {
                    "input": {
                        "format": {"type": "audio/pcmu"},
                        "transcription": {"model": "gpt-4o-mini-transcribe"},
                        "turn_detection": {
                            "type": "server_vad",
                            "silence_duration_ms": 900,
                        },
                    },
                    "output": {
                        "format": {"type": "audio/pcmu"},
                        "voice": get_voice(self.scenario_key, config.BOT_VOICE),
                    },
                },
            },
        }
        await self.openai_ws.send(json.dumps(session_update))

    async def _twilio_to_openai(self):
        """Callee audio -> Realtime input buffer. Server VAD handles turns."""
        while True:
            data = json.loads(await self.twilio_ws.receive_text())
            event = data.get("event")
            if event == "media":
                await self.openai_ws.send(json.dumps({
                    "type": "input_audio_buffer.append",
                    "audio": data["media"]["payload"],
                }))
            elif event == "stop":
                return

    async def _openai_to_twilio(self):
        """Realtime events -> Twilio audio frames + transcript capture.

        Handles both GA and beta event names so a model swap via
        OPENAI_REALTIME_MODEL doesn't break the bridge.
        """
        async for raw in self.openai_ws:
            evt = json.loads(raw)
            etype = evt.get("type")

            if etype in ("response.output_audio.delta", "response.audio.delta"):
                await self.twilio_ws.send_text(json.dumps({
                    "event": "media",
                    "streamSid": self.stream_sid,
                    "media": {"payload": evt["delta"]},
                }))

            elif etype == "input_audio_buffer.speech_started":
                # Their agent started talking. If we're mid-utterance, this is
                # barge-in: flush our queued audio and cancel the response so
                # the bot yields the floor naturally.
                await self.twilio_ws.send_text(json.dumps({
                    "event": "clear", "streamSid": self.stream_sid,
                }))
                if self.response_active:
                    await self.openai_ws.send(json.dumps({"type": "response.cancel"}))

            elif etype == "response.created":
                self.response_active = True
            elif etype == "response.done":
                self.response_active = False

            elif etype == "conversation.item.input_audio_transcription.completed":
                self.transcript.add("AGENT", evt.get("transcript", ""))
            elif etype in ("response.output_audio_transcript.done",
                           "response.audio_transcript.done"):
                self.transcript.add("PATIENT-BOT", evt.get("transcript", ""))

            elif etype == "error":
                err = evt.get("error", {})
                # benign race: we cancelled just as the response finished
                if err.get("code") != "response_cancel_not_active":
                    print(f"[openai] error: {err or evt}")
