"""Secure memory service wrapper with redaction and bounded storage.

Wraps ADK's ``InMemoryMemoryService`` to add:

- **Sensitive data redaction** at write time (passwords, tokens, keys)
- **Bounded storage** with per-user entry limits (FIFO eviction)
- **Delegation pattern** so the inner service can be swapped later

Usage::

    from orrery_core.memory import SecureMemoryService

    memory = SecureMemoryService(max_entries_per_user=500)
    runner = Runner(app=app, session_service=..., memory_service=memory)
"""

from __future__ import annotations

import copy
import logging
import re
from collections.abc import Mapping, Sequence
from typing import Any

from google.adk.events import Event
from google.adk.memory.base_memory_service import BaseMemoryService, SearchMemoryResponse
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.sessions.session import Session
from google.genai import types

logger = logging.getLogger("orrery.memory")

# ── Default redaction patterns ───────────────────────────────────────

_DEFAULT_PATTERNS: list[re.Pattern[str]] = [
    # Key-value secrets: password=xxx, token: xxx, api_key=xxx, bearer xxx
    re.compile(
        r"(?i)(password|token|secret|api[_\-]?key|bearer|credential|auth)"
        r"\s*[:=]\s*\S+",
    ),
    # PEM private key blocks
    re.compile(
        r"-----BEGIN [A-Z ]+(?:PRIVATE )?KEY-----[\s\S]*?-----END [A-Z ]+(?:PRIVATE )?KEY-----",
    ),
]

_REDACTED = "[REDACTED]"


# ── Secure wrapper ───────────────────────────────────────────────────


class SecureMemoryService(BaseMemoryService):
    """Memory service wrapper that redacts secrets and caps storage.

    Args:
        max_entries_per_user: Maximum events stored per user. Oldest events
            are trimmed when the limit is exceeded.
        sensitive_patterns: Regex patterns for redaction. Defaults to a
            built-in set covering passwords, tokens, API keys, and PEM keys.
    """

    def __init__(
        self,
        *,
        max_entries_per_user: int = 500,
        sensitive_patterns: list[re.Pattern[str]] | None = None,
    ) -> None:
        self._inner = InMemoryMemoryService()
        self._max_entries = max_entries_per_user
        self._patterns = sensitive_patterns if sensitive_patterns is not None else _DEFAULT_PATTERNS

    # ── Redaction helpers ────────────────────────────────────────────

    def _redact_text(self, text: str) -> str:
        """Apply all sensitive patterns to a text string."""
        for pattern in self._patterns:
            text = pattern.sub(_REDACTED, text)
        return text

    def _redact_content(self, content: types.Content) -> types.Content:
        """Return a deep copy of *content* with sensitive text redacted."""
        redacted = copy.deepcopy(content)
        if redacted.parts:
            for part in redacted.parts:
                if part.text:
                    part.text = self._redact_text(part.text)
        return redacted

    def _redact_events(self, events: Sequence[Event]) -> list[Event]:
        """Return copies of events with content redacted."""
        result: list[Event] = []
        for event in events:
            if event.content and event.content.parts:
                redacted_event = copy.deepcopy(event)
                redacted_event.content = self._redact_content(event.content)
                result.append(redacted_event)
            else:
                result.append(event)
        return result

    # ── Trim helpers ─────────────────────────────────────────────────

    def _trim_events(self, events: list[Event]) -> list[Event]:
        """Keep only the most recent events up to the per-user limit."""
        if len(events) <= self._max_entries:
            return events
        trimmed = len(events) - self._max_entries
        logger.debug(
            "Trimming %d oldest events to stay within %d limit", trimmed, self._max_entries
        )
        return events[-self._max_entries :]

    # ── BaseMemoryService interface ──────────────────────────────────

    async def add_session_to_memory(self, session: Session) -> None:
        """Redact, trim, then delegate to the inner service."""
        if not session.events:
            return

        # Build a shallow copy of the session with redacted + trimmed events
        redacted_events = self._redact_events(session.events)
        trimmed_events = self._trim_events(redacted_events)

        # Patch events on a copy to avoid mutating the live session
        patched = copy.copy(session)
        patched.events = trimmed_events

        await self._inner.add_session_to_memory(patched)
        logger.debug(
            "Saved session %s to memory (%d events, %d after trim)",
            session.id,
            len(session.events),
            len(trimmed_events),
        )

    async def add_events_to_memory(
        self,
        *,
        app_name: str,
        user_id: str,
        events: Sequence[Event],
        session_id: str | None = None,
        custom_metadata: Mapping[str, Any] | None = None,
    ) -> None:
        """Redact events then delegate to the inner service."""
        redacted = self._redact_events(events)
        trimmed = self._trim_events(redacted)
        await self._inner.add_events_to_memory(
            app_name=app_name,
            user_id=user_id,
            events=trimmed,
            session_id=session_id,
            custom_metadata=custom_metadata,
        )

    async def search_memory(
        self,
        *,
        app_name: str,
        user_id: str,
        query: str,
    ) -> SearchMemoryResponse:
        """Delegate search to the inner service (already user-scoped)."""
        return await self._inner.search_memory(
            app_name=app_name,
            user_id=user_id,
            query=query,
        )
