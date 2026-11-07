import httpx
import pytest
from fastapi.testclient import TestClient

from app import main
from app.checker import Checker


def fake_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "up.example":
            return httpx.Response(200)
        if request.url.host == "error.example":
            return httpx.Response(503)
        raise httpx.ConnectError("unreachable", request=request)

    return httpx.MockTransport(handler)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, "checker", Checker(transport=fake_transport()))
    with TestClient(main.app) as c:
        yield c


def test_health_and_ready(client):
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").status_code == 200


def test_add_list_delete_target(client):
    r = client.post("/targets", json={"url": "https://up.example/"})
    assert r.status_code == 201
    assert [t["url"] for t in client.get("/targets").json()] == ["https://up.example/"]
    assert client.delete("/targets", params={"url": "https://up.example/"}).status_code == 204
    assert client.delete("/targets", params={"url": "https://up.example/"}).status_code == 404


def test_rejects_invalid_url(client):
    assert client.post("/targets", json={"url": "not-a-url"}).status_code == 422


def test_check_marks_up_and_down(client):
    for url in ("https://up.example/", "https://error.example/", "https://down.example/"):
        client.post("/targets", json={"url": url})
    results = {r["url"]: r for r in client.post("/targets/check").json()}
    assert results["https://up.example/"]["up"] is True
    assert results["https://error.example/"]["up"] is False
    assert results["https://error.example/"]["status_code"] == 503
    assert results["https://down.example/"]["error"] == "ConnectError"


def test_metrics_exposed(client):
    client.post("/targets", json={"url": "https://up.example/"})
    client.post("/targets/check")
    body = client.get("/metrics").text
    assert 'probe_target_up{target="https://up.example/"} 1.0' in body
    assert "probe_target_latency_seconds_bucket" in body
