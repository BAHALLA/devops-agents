"""Tests for Markdown → Slack mrkdwn conversion."""

from slack_bot.formatting import chunk_message, md_to_mrkdwn


class TestMdToMrkdwn:
    def test_bold_conversion(self):
        assert md_to_mrkdwn("This is **bold** text") == "This is *bold* text"

    def test_heading_conversion(self):
        assert md_to_mrkdwn("## Status Report") == "*Status Report*"

    def test_h1_conversion(self):
        assert md_to_mrkdwn("# Title") == "*Title*"

    def test_code_block_preserved(self):
        text = "Before\n```\n**not bold**\n```\nAfter **bold**"
        result = md_to_mrkdwn(text)
        assert "**not bold**" in result  # inside code block, not converted
        assert "*bold*" in result  # outside code block, converted

    def test_plain_text_unchanged(self):
        assert md_to_mrkdwn("Just plain text") == "Just plain text"

    def test_multiple_headings(self):
        text = "## First\nSome text\n### Second"
        result = md_to_mrkdwn(text)
        assert "*First*" in result
        assert "*Second*" in result


class TestChunkMessage:
    def test_short_message_single_chunk(self):
        assert chunk_message("Hello", max_length=100) == ["Hello"]

    def test_long_message_split_on_paragraphs(self):
        text = "Para one.\n\nPara two.\n\nPara three."
        chunks = chunk_message(text, max_length=25)
        assert len(chunks) > 1
        # All original content should be in the chunks
        joined = "\n\n".join(chunks)
        assert "Para one." in joined
        assert "Para three." in joined

    def test_single_long_paragraph_hard_split(self):
        text = "A" * 200
        chunks = chunk_message(text, max_length=50)
        assert all(len(c) <= 50 for c in chunks)
        assert "".join(chunks) == text

    def test_empty_string(self):
        assert chunk_message("") == [""]
