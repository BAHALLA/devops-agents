"""Structured audit logging for tool calls.

Provides an after_tool_callback that logs every tool invocation to a
JSON Lines file for traceability and debugging.

ADK calls after_tool_callback with keyword args:
    callback(tool=..., args=..., tool_context=..., tool_response=...)
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from google.adk.agents.context import Context
from google.adk.tools.base_tool import BaseTool

logger = logging.getLogger("ai_agents.audit")


def audit_logger(log_path: str | Path | None = None) -> Callable:
    """Create an after_tool_callback that logs every tool invocation.

    Each log entry is a JSON object written to a .jsonl file with:
    - timestamp, agent, tool name, arguments, result status, user/session IDs.

    Args:
        log_path: Path to the audit log file. Defaults to ./audit.jsonl
                  in the current working directory.

    Usage:
        create_agent(
            ...,
            after_tool_callback=audit_logger("logs/audit.jsonl"),
        )
    """
    resolved_path = Path(log_path) if log_path else Path("audit.jsonl")
    resolved_path.parent.mkdir(parents=True, exist_ok=True)

    def callback(
        *,
        tool: BaseTool,
        args: dict[str, Any],
        tool_context: Context,
        tool_response: dict,
    ) -> dict | None:
        sanitized_response = _sanitize(tool_response) if isinstance(tool_response, dict) else None

        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "agent": tool_context.agent_name if hasattr(tool_context, "agent_name") else "unknown",
            "tool": tool.name,
            "args": _sanitize(args),
            "status": sanitized_response.get("status", "unknown")
            if sanitized_response is not None
            else "ok",
            "response": sanitized_response,
            "user_id": tool_context.user_id if hasattr(tool_context, "user_id") else "unknown",
            "session_id": tool_context.session.id
            if hasattr(tool_context, "session") and tool_context.session
            else "unknown",
        }

        try:
            with open(resolved_path, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except OSError as e:
            logger.warning("Failed to write audit log: %s", e)

        return None  # don't modify the result

    return callback


_SENSITIVE_KEYS = {"password", "secret", "token", "api_key", "credential"}


def _sanitize(data: Any) -> Any:
    """Recursively redact sensitive values from dicts and lists."""
    if isinstance(data, dict):
        return {
            k: "***" if any(s in k.lower() for s in _SENSITIVE_KEYS) else _sanitize(v)
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [_sanitize(item) for item in data]
    return data


# Keep backward-compatible alias
_sanitize_args = _sanitize
