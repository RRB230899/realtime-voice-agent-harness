"""Tests for the TwiML endpoint. No Twilio or OpenAI calls are made."""
import xml.etree.ElementTree as ET

import pytest
from fastapi.testclient import TestClient

from app import config, server


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(config, "PUBLIC_URL", "https://example.ngrok-free.app")
    return TestClient(server.app)


def test_twiml_opens_a_stream_for_a_known_scenario(client):
    response = client.post("/twiml", params={"scenario": "refill_request"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/xml")

    stream = ET.fromstring(response.text).find("./Connect/Stream")
    assert stream.get("url") == "wss://example.ngrok-free.app/media"
    assert stream.find("Parameter").get("value") == "refill_request"


def test_twiml_defaults_to_the_simple_scheduling_scenario(client):
    response = client.post("/twiml")
    parameter = ET.fromstring(response.text).find("./Connect/Stream/Parameter")
    assert parameter.get("value") == "schedule_simple"


@pytest.mark.parametrize("scenario", [
    "not_a_scenario",
    '"/><Dial>+15555550100</Dial><x a="',  # attempt to inject TwiML
])
def test_twiml_rejects_unknown_scenarios(client, scenario):
    response = client.post("/twiml", params={"scenario": scenario})
    assert response.status_code == 400
    assert "Dial" not in response.text


def test_health_reports_missing_settings(client):
    body = client.get("/health").json()
    assert body["ok"] is True
    assert isinstance(body["missing_env"], list)
