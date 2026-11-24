import pytest
import requests

from backend import render_service


class FakeResponse:
    def __init__(self, data=None, status_code=200, content=True):
        self.data = data or {}
        self.status_code = status_code
        self.ok = 200 <= status_code < 400
        self.content = b"response" if content else b""

    def json(self):
        return self.data


def configure_render(monkeypatch):
    monkeypatch.setenv("RENDER_API_KEY", "fake-render-token")
    monkeypatch.setenv("RENDER_SERVICE_ID", "srv-test-123")


def test_missing_render_credentials(monkeypatch):
    monkeypatch.delenv("RENDER_API_KEY", raising=False)
    monkeypatch.delenv("RENDER_SERVICE_ID", raising=False)

    with pytest.raises(render_service.RenderAPIError):
        render_service._get_config()


def test_request_uses_bearer_authentication_and_timeout(monkeypatch):
    configure_render(monkeypatch)
    captured = {}

    def fake_request(method, url, headers, timeout, **kwargs):
        captured.update({
            "method": method,
            "url": url,
            "headers": headers,
            "timeout": timeout
        })
        return FakeResponse({"status": "live"})

    monkeypatch.setattr(
        render_service.requests,
        "request",
        fake_request
    )

    result = render_service._request("GET", "/test")

    assert result == {"status": "live"}
    assert captured["headers"]["Authorization"] == "Bearer fake-render-token"
    assert captured["headers"]["Accept"] == "application/json"
    assert captured["timeout"] == 20


def test_list_service_deploys_parses_response(monkeypatch):
    configure_render(monkeypatch)
    captured = {}

    def fake_request(method, url, **kwargs):
        captured["url"] = url
        captured["params"] = kwargs.get("params")
        return FakeResponse([
            {"deploy": {"id": "dep-1", "status": "live"}},
            {"id": "dep-2", "status": "deactivated"}
        ])

    monkeypatch.setattr(render_service.requests, "request", fake_request)

    result = render_service.list_service_deploys()

    assert result == [
        {"id": "dep-1", "status": "live"},
        {"id": "dep-2", "status": "deactivated"}
    ]
    assert captured["params"] == {"limit": 100}
    assert "/services/srv-test-123/deploys" in captured["url"]


def test_get_service_deploy(monkeypatch):
    configure_render(monkeypatch)
    monkeypatch.setattr(
        render_service.requests,
        "request",
        lambda *args, **kwargs: FakeResponse({
            "id": "dep-123",
            "status": "live"
        })
    )

    result = render_service.get_service_deploy("dep-123")

    assert result["id"] == "dep-123"
    assert result["status"] == "live"


def test_rollback_render_deploy(monkeypatch):
    configure_render(monkeypatch)
    captured = {}

    def fake_request(method, url, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["json"] = kwargs.get("json")
        return FakeResponse({"id": "rollback-123"})

    monkeypatch.setattr(render_service.requests, "request", fake_request)

    result = render_service.rollback_render_deploy("dep-123")

    assert result["id"] == "rollback-123"
    assert captured["method"] == "POST"
    assert captured["json"] == {"deployId": "dep-123"}
    assert captured["url"].endswith("/services/srv-test-123/rollback")


def test_http_error_raises_render_api_error(monkeypatch):
    configure_render(monkeypatch)

    monkeypatch.setattr(
        render_service.requests,
        "request",
        lambda *args, **kwargs: FakeResponse(
            {"error": "Unauthorized"},
            status_code=401
        )
    )

    with pytest.raises(
        render_service.RenderAPIError,
        match="HTTP 401"
    ):
        render_service._request("GET", "/test")


def test_network_error_raises_render_api_error(monkeypatch):
    configure_render(monkeypatch)

    def raise_network_error(*args, **kwargs):
        raise requests.ConnectionError("Connection unavailable")

    monkeypatch.setattr(
        render_service.requests,
        "request",
        raise_network_error
    )

    with pytest.raises(
        render_service.RenderAPIError,
        match="Could not connect to Render"
    ):
        render_service._request("GET", "/test")
