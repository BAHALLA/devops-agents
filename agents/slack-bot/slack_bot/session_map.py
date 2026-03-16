"""Maps Slack threads to ADK sessions.

A Slack thread is uniquely identified by (channel_id, thread_ts).
Each thread maps to one ADK session for conversational continuity.
"""

from __future__ import annotations


class SessionMap:
    """In-memory mapping from Slack threads to ADK session IDs."""

    def __init__(self) -> None:
        self._map: dict[tuple[str, str], str] = {}

    def get(self, channel: str, thread_ts: str) -> str | None:
        """Look up an existing session ID for a thread."""
        return self._map.get((channel, thread_ts))

    def set(self, channel: str, thread_ts: str, session_id: str) -> None:
        """Store a session mapping for a thread."""
        self._map[(channel, thread_ts)] = session_id

    def remove(self, channel: str, thread_ts: str) -> None:
        """Remove a thread mapping (e.g., on session expiry)."""
        self._map.pop((channel, thread_ts), None)
