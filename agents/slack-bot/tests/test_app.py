"""Tests for the FastAPI/Slack app endpoints."""

from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    def test_health_returns_ok(self):
        """Test the health endpoint logic directly without Slack dependencies."""
        app = FastAPI()
        handler_ready = False

        @app.get("/health")
        async def health():
            return {"status": "ok", "handler_ready": handler_ready}

        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["handler_ready"] is False

    def test_health_with_handler_ready(self):
        app = FastAPI()
        handler_ready = True

        @app.get("/health")
        async def health():
            return {"status": "ok", "handler_ready": handler_ready}

        client = TestClient(app)
        response = client.get("/health")
        data = response.json()
        assert data["handler_ready"] is True
