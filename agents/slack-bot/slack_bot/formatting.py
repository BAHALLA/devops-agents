"""Convert Markdown to Slack mrkdwn format."""

from __future__ import annotations

import re

# Slack messages have a practical limit for readability.
MAX_MESSAGE_LENGTH = 3000


def md_to_mrkdwn(text: str) -> str:
    """Convert common Markdown to Slack mrkdwn.

    Handles bold, italic, headings, and links.
    Code blocks (```) are left as-is since Slack supports them.
    """
    # Headings: ## Heading → *Heading*
    text = re.sub(r"^#{1,6}\s+(.+)$", r"*\1*", text, flags=re.MULTILINE)

    # Bold: **text** → *text*  (but skip inside code blocks)
    text = _replace_outside_code(text, r"\*\*(.+?)\*\*", r"*\1*")

    return text


def chunk_message(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> list[str]:
    """Split a long message into chunks that fit Slack's limits.

    Splits on paragraph boundaries (double newline) when possible.
    """
    if len(text) <= max_length:
        return [text]

    chunks: list[str] = []
    current = ""

    for paragraph in text.split("\n\n"):
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) > max_length:
            if current:
                chunks.append(current.strip())
            # If a single paragraph exceeds max_length, hard-split it
            while len(paragraph) > max_length:
                chunks.append(paragraph[:max_length])
                paragraph = paragraph[max_length:]
            current = paragraph
        else:
            current = candidate

    if current.strip():
        chunks.append(current.strip())

    return chunks


def _replace_outside_code(text: str, pattern: str, replacement: str) -> str:
    """Apply regex replacement only outside of code blocks."""
    parts = text.split("```")
    for i in range(0, len(parts), 2):  # even indices are outside code blocks
        parts[i] = re.sub(pattern, replacement, parts[i])
    return "```".join(parts)
