"""Slack bot configuration."""

from __future__ import annotations

from ai_agents_core import AgentConfig


class SlackBotConfig(AgentConfig):
    """Configuration for the Slack bot integration.

    All values can be set via environment variables or a .env file.
    """

    slack_bot_token: str = ""
    slack_signing_secret: str = ""
    slack_app_token: str = ""  # only needed for Socket Mode
    slack_bot_port: int = 3000
    slack_db_url: str = "sqlite+aiosqlite:///slack_devops.db"
