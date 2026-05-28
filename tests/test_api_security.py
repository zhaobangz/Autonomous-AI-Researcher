"""Security regression tests for API authentication helpers."""

from __future__ import annotations

import importlib
from types import SimpleNamespace

import pytest
from fastapi import WebSocketException, status
from starlette.datastructures import Headers

from config import get_settings


def _reload_api_server(monkeypatch, internal_api_key: str):
    monkeypatch.setenv("INTERNAL_API_KEY", internal_api_key)
    get_settings.cache_clear()
    import api.server as server

    return importlib.reload(server)


def test_websocket_stream_rejects_missing_internal_api_key(monkeypatch):
    server = _reload_api_server(monkeypatch, "a" * 32)
    websocket = SimpleNamespace(headers=Headers({}))

    with pytest.raises(WebSocketException) as exc:
        server._verify_websocket_api_key(websocket)

    assert exc.value.code == status.WS_1008_POLICY_VIOLATION


def test_websocket_stream_accepts_matching_internal_api_key(monkeypatch):
    key = "b" * 32
    server = _reload_api_server(monkeypatch, key)
    websocket = SimpleNamespace(headers=Headers({"x-api-key": key}))

    server._verify_websocket_api_key(websocket)
