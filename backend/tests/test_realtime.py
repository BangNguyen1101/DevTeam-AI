import pytest
from starlette.websockets import WebSocketDisconnect


def test_project_created_event_is_pushed(client):
    with client.websocket_connect("/ws?topics=projects") as ws:
        assert ws.receive_json() == {"type": "subscribed", "topics": ["projects"]}
        created = client.post("/api/v1/projects", json={"name": "Realtime"}).json()

        event = ws.receive_json()
        assert event["topic"] == "projects"
        assert event["type"] == "project.created"
        assert event["data"]["id"] == created["id"]


def test_ping_pong(client):
    with client.websocket_connect("/ws?topics=projects") as ws:
        ws.receive_json()
        ws.send_text("ping")
        assert ws.receive_json() == {"type": "pong"}


def test_invalid_topic_is_refused(client):
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/ws?topics=secrets") as ws:
            ws.receive_json()
    assert exc.value.code == 1008
