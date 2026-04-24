"""Tests for the Google Chat REST client."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest
from google_chat_bot.chat_client import ChatClient


@pytest.fixture
def credentials():
    creds = MagicMock()
    creds.valid = True
    creds.token = "fake-token"
    return creds


@pytest.fixture
def client(credentials):
    return ChatClient(credentials=credentials)


def _install_mock_transport(monkeypatch, handler):
    """Patch ``httpx.AsyncClient`` so calls use a MockTransport.

    Bind the real class before patching so we can still instantiate it
    inside the factory closure without recursing.
    """
    real_cls = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs.pop("transport", None)
        return real_cls(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)


@pytest.mark.asyncio
async def test_create_message_posts_text_and_cards(client, monkeypatch):
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["json"] = json.loads(request.content)
        return httpx.Response(200, json={"name": "spaces/AAA/messages/BBB"})

    _install_mock_transport(monkeypatch, handler)

    response = await client.create_message(
        "spaces/AAA", text="hello", cards_v2=[{"cardId": "x", "card": {}}]
    )
    assert response == {"name": "spaces/AAA/messages/BBB"}
    assert captured["method"] == "POST"
    assert captured["url"].startswith("https://chat.googleapis.com/v1/spaces/AAA/messages")
    body = captured["json"]
    assert body["text"] == "hello"
    assert body["cardsV2"] == [{"cardId": "x", "card": {}}]


@pytest.mark.asyncio
async def test_update_message_requires_text_or_cards(client):
    with pytest.raises(ValueError):
        await client.update_message("spaces/AAA/messages/BBB")


@pytest.mark.asyncio
async def test_update_message_patches_with_update_mask(client, monkeypatch):
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["params"] = dict(request.url.params)
        captured["json"] = json.loads(request.content)
        return httpx.Response(200, json={"name": "spaces/AAA/messages/BBB"})

    _install_mock_transport(monkeypatch, handler)

    await client.update_message(
        "spaces/AAA/messages/BBB",
        text="updated",
        cards_v2=[{"cardId": "p", "card": {}}],
    )
    assert captured["method"] == "PATCH"
    assert captured["url"].startswith("https://chat.googleapis.com/v1/spaces/AAA/messages/BBB")
    assert captured["params"]["updateMask"] == "text,cardsV2"
    body = captured["json"]
    assert body["text"] == "updated"
    assert body["cardsV2"] == [{"cardId": "p", "card": {}}]


@pytest.mark.asyncio
async def test_update_message_cards_only_mask(client, monkeypatch):
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["params"] = dict(request.url.params)
        captured["json"] = json.loads(request.content)
        return httpx.Response(200, json={})

    _install_mock_transport(monkeypatch, handler)

    await client.update_message("spaces/AAA/messages/BBB", cards_v2=[{"cardId": "p", "card": {}}])
    assert captured["params"]["updateMask"] == "cardsV2"
    assert "text" not in captured["json"]


@pytest.mark.asyncio
async def test_update_message_404_returns_none(client, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "gone"})

    _install_mock_transport(monkeypatch, handler)

    result = await client.update_message("spaces/AAA/messages/BBB", text="x")
    assert result is None


@pytest.mark.asyncio
async def test_update_message_500_raises(client, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    _install_mock_transport(monkeypatch, handler)

    with pytest.raises(httpx.HTTPStatusError):
        await client.update_message("spaces/AAA/messages/BBB", text="x")
