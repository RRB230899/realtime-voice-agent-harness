"""FastAPI server: serves TwiML for outbound calls and bridges
Twilio Media Streams <-> OpenAI Realtime API.

Data flow (both directions are raw g711_ulaw @ 8kHz — no transcoding):
    Twilio call audio --ws--> this server --ws--> OpenAI Realtime
    OpenAI speech     --ws--> this server --ws--> Twilio (played to callee)

TODO: 
	implement the /media websocket bridge.
"""
from fastapi import FastAPI, WebSocket
from fastapi.responses import Response

from . import config

app = FastAPI()


@app.get("/health")
async def health():
    return {"ok": True, "missing_env": config.validate()}


@app.post("/twiml")
async def twiml():
    """Twilio fetches this when the outbound call connects.
    It tells Twilio to open a media stream back to our /media websocket."""
    ws_url = config.PUBLIC_URL.replace("https://", "wss://") + "/media"
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="{ws_url}" />
  </Connect>
</Response>"""
    return Response(content=xml, media_type="text/xml")


@app.websocket("/media")
async def media(ws: WebSocket):
    """Bridge: Twilio Media Stream <-> OpenAI Realtime session."""
    await ws.accept()
    # TODO: connect to OpenAI Realtime, configure session (g711_ulaw,
    # scenario instructions, server VAD), pump audio both ways,
    # capture transcripts from conversation events.
    await ws.close()
