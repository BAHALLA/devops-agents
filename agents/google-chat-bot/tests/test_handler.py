"""Tests for the Google Chat bot handler."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from google.genai import types
from google_chat_bot.config import GoogleChatBotConfig
from google_chat_bot.confirmation import (
    ConfirmationStore,
    PendingConfirmation,
    end_request_buffer,
    google_chat_confirmation,
    start_request_buffer,
)
from google_chat_bot.handler import GoogleChatHandler


@pytest.fixture
def config():
    return GoogleChatBotConfig(
        google_chat_admin_emails="admin@example.com",
        google_chat_operator_emails="ops@example.com",
    )


@pytest.fixture
def mock_runner():
    runner = MagicMock()

    async def async_gen(*args, **kwargs):
        event = MagicMock()
        event.content = types.Content(
            role="model", parts=[types.Part.from_text(text="Hello from agent")]
        )
        yield event

    runner.run_async.side_effect = async_gen
    return runner


@pytest.fixture
def store():
    return ConfirmationStore()


@pytest.fixture
def handler(mock_runner, config, store):
    return GoogleChatHandler(runner=mock_runner, config=config, store=store)


class TestResolveRole:
    def test_admin(self, handler):
        assert handler.resolve_role("admin@example.com") == "admin"

    def test_operator(self, handler):
        assert handler.resolve_role("ops@example.com") == "operator"

    def test_viewer(self, handler):
        assert handler.resolve_role("other@example.com") == "viewer"

    def test_case_insensitive(self, handler):
        assert handler.resolve_role("Admin@Example.COM") == "admin"

    def test_empty(self, handler):
        assert handler.resolve_role("") == "viewer"


class TestHandleEvent:
    @pytest.mark.asyncio
    async def test_added_to_space(self, handler):
        event = {"type": "ADDED_TO_SPACE"}
        response = await handler.handle_event(event)
        # Verify Workspace Add-on DataAction structure
        message = response["hostAppDataAction"]["chatDataAction"]["createMessageAction"]["message"]
        assert "Thanks for adding me" in message["text"]

    @pytest.mark.asyncio
    async def test_unknown_event_type(self, handler):
        response = await handler.handle_event({"type": "WIDGET_UPDATED"})
        message = response["hostAppDataAction"]["chatDataAction"]["createMessageAction"]["message"]
        assert "not sure how to handle" in message["text"]

    @pytest.mark.asyncio
    async def test_message_empty(self, handler):
        event = {
            "type": "MESSAGE",
            "message": {"argumentText": ""},
            "user": {"email": "user@example.com"},
            "space": {"name": "spaces/abc"},
        }
        response = await handler.handle_event(event)
        message = response["hostAppDataAction"]["chatDataAction"]["createMessageAction"]["message"]
        assert "How can I help" in message["text"]

    @pytest.mark.asyncio
    async def test_message_runs_agent(self, handler, mock_runner):
        event = {
            "type": "MESSAGE",
            "message": {"argumentText": "hello", "thread": {"name": "threads/123"}},
            "user": {"email": "user@example.com"},
            "space": {"name": "spaces/abc"},
        }
        response = await handler.handle_event(event)
        message = response["hostAppDataAction"]["chatDataAction"]["createMessageAction"]["message"]
        assert "Hello from agent" in message["text"]
        mock_runner.run_async.assert_called_once()
        call_kwargs = mock_runner.run_async.call_args.kwargs
        assert call_kwargs["user_id"] == "user@example.com"
        assert call_kwargs["session_id"] == "gchat:threads/123"
        assert call_kwargs["state_delta"]["user_role"] == "viewer"
        # Server-trusted lock flag must be set so ensure_default_role()
        # doesn't reset the role on before_agent_callback.
        assert call_kwargs["state_delta"]["_role_set_by_server"] is True
        assert call_kwargs["state_delta"]["gchat_space"] == "spaces/abc"

    @pytest.mark.asyncio
    async def test_admin_email_is_marked_server_trusted(self, handler, mock_runner):
        """Regression: admin role must survive ensure_default_role()."""
        event = {
            "type": "MESSAGE",
            "message": {"argumentText": "restart it"},
            "user": {"email": "admin@example.com"},
            "space": {"name": "spaces/abc"},
        }
        await handler.handle_event(event)
        call_kwargs = mock_runner.run_async.call_args.kwargs
        state_delta = call_kwargs["state_delta"]
        assert state_delta["user_role"] == "admin"
        assert state_delta["_role_set_by_server"] is True

        # End-to-end: simulate ensure_default_role() running on the
        # resulting state. With the lock flag set, it must be a no-op.
        from orrery_core import ensure_default_role

        callback = ensure_default_role()
        fake_ctx = MagicMock()
        fake_ctx.state = dict(state_delta)
        callback(fake_ctx)
        assert fake_ctx.state["user_role"] == "admin"  # not downgraded to viewer

    @pytest.mark.asyncio
    async def test_message_session_id_fallback_to_space(self, handler, mock_runner):
        event = {
            "type": "MESSAGE",
            "message": {"argumentText": "hi"},  # no thread
            "user": {"email": "user@example.com"},
            "space": {"name": "spaces/abc"},
        }
        await handler.handle_event(event)
        call_kwargs = mock_runner.run_async.call_args.kwargs
        assert call_kwargs["session_id"] == "gchat:spaces/abc"


class TestHandleCardClick:
    @pytest.mark.asyncio
    async def test_unknown_action_id(self, handler):
        event = {
            "type": "CARD_CLICKED",
            "common": {
                "invokedFunction": "confirm_action",
                "parameters": [{"key": "action_id", "value": "nonexistent"}],
            },
            "user": {"email": "user@example.com"},
        }
        response = await handler.handle_event(event)
        message = response["hostAppDataAction"]["chatDataAction"]["createMessageAction"]["message"]
        assert "expired or was already processed" in message["text"]

    @pytest.mark.asyncio
    async def test_missing_action_id(self, handler):
        event = {
            "type": "CARD_CLICKED",
            "common": {"invokedFunction": "confirm_action", "parameters": []},
            "user": {"email": "user@example.com"},
        }
        response = await handler.handle_event(event)
        message = response["hostAppDataAction"]["chatDataAction"]["createMessageAction"]["message"]
        assert "not recognized" in message["text"]

    @pytest.mark.asyncio
    async def test_confirm_action_runs_agent(self, handler, store, mock_runner):
        store.add(
            PendingConfirmation(
                action_id="abc123",
                tool_name="restart_deployment",
                user_id="user@example.com",
                session_id="gchat:threads/1",
                space_name="spaces/xyz",
                thread_name="threads/1",
                level="destructive",
            )
        )
        event = {
            "type": "CARD_CLICKED",
            "common": {
                "invokedFunction": "confirm_action",
                "parameters": [{"key": "action_id", "value": "abc123"}],
            },
            "user": {"email": "ops@example.com", "displayName": "Ops User"},
        }
        response = await handler.handle_event(event)

        message = response["hostAppDataAction"]["chatDataAction"]["createMessageAction"]["message"]
        text = message["text"]
        assert "Approved" in text
        assert "Hello from agent" in text

        call_kwargs = mock_runner.run_async.call_args.kwargs
        assert call_kwargs["user_id"] == "user@example.com"  # original requester
        assert call_kwargs["session_id"] == "gchat:threads/1"
        # Synthetic message replays the approval.
        new_msg = call_kwargs["new_message"]
        assert "Yes, proceed" in new_msg.parts[0].text

    @pytest.mark.asyncio
    async def test_deny_action_clears_pending(self, handler, store, mock_runner):
        store.add(
            PendingConfirmation(
                action_id="xyz",
                tool_name="drop_topic",
                user_id="user@example.com",
                session_id="gchat:threads/2",
                space_name="spaces/xyz",
                thread_name="threads/2",
                level="destructive",
            )
        )
        event = {
            "type": "CARD_CLICKED",
            "common": {
                "invokedFunction": "deny_action",
                "parameters": [{"key": "action_id", "value": "xyz"}],
            },
            "user": {"email": "ops@example.com", "displayName": "Ops User"},
        }
        response = await handler.handle_event(event)

        message = response["hostAppDataAction"]["chatDataAction"]["createMessageAction"]["message"]
        text = message["text"]
        assert "Denied" in text
        assert "Hello from agent" in text

        call_kwargs = mock_runner.run_async.call_args.kwargs
        # Deny should clear the pending flag in state_delta to prevent a
        # silent bypass if the LLM retries the same tool.
        assert call_kwargs["state_delta"]["_gchat_pending_drop_topic"] is False

    @pytest.mark.asyncio
    async def test_addons_card_click_without_top_level_type(self, handler, store):
        """Add-ons payloads omit top-level 'type' — detection must still fire."""
        store.add(
            PendingConfirmation(
                action_id="addon1",
                tool_name="scale_deployment",
                user_id="user@example.com",
                session_id="gchat:spaces/abc",
                space_name="spaces/abc",
                thread_name=None,
                level="confirm",
            )
        )
        event = {
            # No "type" field — mimics the Workspace Add-ons envelope.
            "commonEventObject": {
                "invokedFunction": "confirm_action",
                "parameters": [{"key": "action_id", "value": "addon1"}],
            },
            "chat": {"user": {"email": "ops@example.com", "displayName": "Ops User"}},
        }
        response = await handler.handle_event(event)
        message = response["hostAppDataAction"]["chatDataAction"]["createMessageAction"]["message"]
        assert "Approved" in message["text"]

    @pytest.mark.asyncio
    async def test_legacy_action_method_name_format(self, handler, store):
        """Handler should also accept the legacy actionMethodName payload."""
        store.add(
            PendingConfirmation(
                action_id="leg1",
                tool_name="restart",
                user_id="user@example.com",
                session_id="gchat:spaces/abc",
                space_name="spaces/abc",
                thread_name=None,
                level="destructive",
            )
        )
        event = {
            "type": "CARD_CLICKED",
            "action": {
                "actionMethodName": "confirm_action",
                "parameters": [{"key": "action_id", "value": "leg1"}],
            },
            "user": {"email": "ops@example.com"},
        }
        response = await handler.handle_event(event)
        message = response["hostAppDataAction"]["chatDataAction"]["createMessageAction"]["message"]
        assert "Approved" in message["text"]


class TestGoogleChatConfirmation:
    def _ctx(self):
        ctx = MagicMock()
        ctx.state = {}
        ctx.user_id = "user@example.com"
        session = MagicMock()
        session.id = "gchat:threads/1"
        ctx.session = session
        return ctx

    def test_not_guarded(self, store):
        callback = google_chat_confirmation(store)
        tool = MagicMock()
        tool.func = lambda x: x
        assert callback(tool=tool, args={}, tool_context=self._ctx()) is None

    def test_guarded_emits_card(self, store):
        from orrery_core import confirm

        callback = google_chat_confirmation(store)

        @confirm("testing")
        def my_tool():
            return "ok"

        tool = MagicMock()
        tool.func = my_tool
        tool.name = "my_tool"

        ctx = self._ctx()
        ctx.state["gchat_space"] = "spaces/abc"
        ctx.state["gchat_thread"] = "threads/1"

        buf, token = start_request_buffer()
        try:
            result = callback(tool=tool, args={"a": 1}, tool_context=ctx)
        finally:
            end_request_buffer(token)

        assert result is not None
        assert result["status"] == "confirmation_required"
        assert ctx.state["_gchat_pending_my_tool"] is True
        assert len(buf) == 1
        assert buf[0]["card"]["header"]["title"].startswith("\U0001f535")
        # A pending confirmation must be in the store for card click lookup.
        assert len(store._pending) == 1
        pending = next(iter(store._pending.values()))
        assert pending.tool_name == "my_tool"
        assert pending.space_name == "spaces/abc"

    def test_already_confirmed_proceeds(self, store):
        from orrery_core import confirm

        callback = google_chat_confirmation(store)

        @confirm("testing")
        def my_tool():
            return "ok"

        tool = MagicMock()
        tool.func = my_tool
        tool.name = "my_tool"

        ctx = self._ctx()
        ctx.state["_gchat_pending_my_tool"] = True

        result = callback(tool=tool, args={}, tool_context=ctx)
        assert result is None
        assert ctx.state["_gchat_pending_my_tool"] is False


# ── Progressive-card flow ────────────────────────────────────────────


def _make_event(*, author: str, text: str = "", state_delta: dict | None = None) -> MagicMock:
    """Build a fake ADK runner event with the fields the tracker reads."""
    event = MagicMock()
    event.author = author
    if text:
        event.content = types.Content(role="model", parts=[types.Part.from_text(text=text)])
    else:
        event.content = None
    event.actions = MagicMock()
    event.actions.state_delta = state_delta or {}
    event.get_function_calls = lambda: []
    return event


def _make_tool_call_event(author: str, tool_name: str) -> MagicMock:
    """Fake event that reports a function call breadcrumb."""
    event = MagicMock()
    event.author = author
    event.content = None
    event.actions = MagicMock()
    event.actions.state_delta = {}
    call = MagicMock()
    call.name = tool_name
    event.get_function_calls = lambda: [call]
    return event


@pytest.fixture
def progressive_runner():
    """Runner that emits triage events: agent-change → tool-call → status writes → summary."""
    runner = MagicMock()

    async def async_gen(*args, **kwargs):
        yield _make_event(author="kafka_health_checker")
        yield _make_tool_call_event("kafka_health_checker", "list_consumer_groups")
        yield _make_event(
            author="kafka_health_checker",
            state_delta={"kafka_status": "Kafka cluster is green, all brokers up."},
        )
        yield _make_event(
            author="k8s_health_checker",
            state_delta={"k8s_status": "Pod api-7f in CrashLoopBackOff — failing."},
        )
        yield _make_event(
            author="triage_summarizer",
            text="Overall: degraded. K8s api is critical.",
            state_delta={"triage_report": "Overall: degraded. K8s api is critical."},
        )

    runner.run_async.side_effect = async_gen
    return runner


@pytest.fixture
def async_handler(config, store, progressive_runner):
    """Handler wired with a mock ChatClient → triggers the deferred path."""
    chat_client = MagicMock()
    chat_client.create_message = AsyncMock(return_value={"name": "spaces/abc/messages/PROG-1"})
    chat_client.update_message = AsyncMock(return_value={"name": "spaces/abc/messages/PROG-1"})
    return GoogleChatHandler(
        runner=progressive_runner,
        config=config,
        store=store,
        chat_client=chat_client,
    )


class TestProgressiveUpdates:
    @pytest.mark.asyncio
    async def test_message_defers_to_background(self, async_handler):
        event = {
            "type": "MESSAGE",
            "message": {"argumentText": "run triage"},
            "user": {"email": "ops@example.com"},
            "space": {"name": "spaces/abc"},
        }
        response = await async_handler.handle_event(event)
        # Empty ack — the real reply goes out via the background task.
        assert response == {"hostAppDataAction": {}}
        # Drain the background task.
        for task in list(async_handler._background_tasks):
            await task

    @pytest.mark.asyncio
    async def test_progress_card_posted_then_updated(self, async_handler):
        event = {
            "type": "MESSAGE",
            "message": {"argumentText": "run triage"},
            "user": {"email": "ops@example.com"},
            "space": {"name": "spaces/abc"},
        }
        await async_handler.handle_event(event)
        for task in list(async_handler._background_tasks):
            await task

        # 1. Exactly one create_message — the initial progress card.
        async_handler.chat_client.create_message.assert_awaited_once()
        create_kwargs = async_handler.chat_client.create_message.call_args.kwargs
        first_card = create_kwargs["cards_v2"][0]
        assert first_card["cardId"] == "progress"
        assert "Investigating" in first_card["card"]["header"]["title"]

        # 2. At least one update_message was called along the way
        #    (state_delta writes force-flush).
        assert async_handler.chat_client.update_message.await_count >= 1

    @pytest.mark.asyncio
    async def test_final_card_is_triage_result_when_chips_landed(self, async_handler):
        event = {
            "type": "MESSAGE",
            "message": {"argumentText": "triage"},
            "user": {"email": "ops@example.com"},
            "space": {"name": "spaces/abc"},
        }
        await async_handler.handle_event(event)
        for task in list(async_handler._background_tasks):
            await task

        # Inspect the *last* update_message call — that's the final
        # result card (triage report with chips).
        last_call = async_handler.chat_client.update_message.await_args_list[-1]
        cards = last_call.kwargs["cards_v2"]
        assert cards[0]["cardId"] == "triage_result"
        subtitle = cards[0]["card"]["header"]["subtitle"]
        # k8s_status had "failing" → overall should be Critical.
        assert subtitle == "Critical"

    @pytest.mark.asyncio
    async def test_remediation_button_gated_by_role(self, config, store, progressive_runner):
        """Viewer role must not see the Run-Remediation button."""
        chat_client = MagicMock()
        chat_client.create_message = AsyncMock(return_value={"name": "spaces/abc/messages/PROG-2"})
        chat_client.update_message = AsyncMock(return_value={})
        handler = GoogleChatHandler(
            runner=progressive_runner,
            config=config,
            store=store,
            chat_client=chat_client,
        )
        event = {
            "type": "MESSAGE",
            "message": {"argumentText": "triage"},
            "user": {"email": "viewer@example.com"},  # not in admin/operator lists
            "space": {"name": "spaces/abc"},
        }
        await handler.handle_event(event)
        for task in list(handler._background_tasks):
            await task

        last_call = chat_client.update_message.await_args_list[-1]
        final_card = last_call.kwargs["cards_v2"][0]
        # Walk the card and confirm no Run-Remediation button.
        buttons = []
        for section in final_card["card"].get("sections", []):
            for widget in section.get("widgets", []):
                bl = widget.get("buttonList")
                if bl:
                    buttons.extend(bl.get("buttons", []))
        assert not any(b.get("text") == "Run Remediation" for b in buttons)

    @pytest.mark.asyncio
    async def test_update_failure_falls_back_to_new_message(
        self, config, store, progressive_runner
    ):
        """If the final update PATCH fails, post a fresh message instead."""
        chat_client = MagicMock()
        chat_client.create_message = AsyncMock(return_value={"name": "spaces/abc/messages/PROG-3"})

        # First few updates succeed (progress card live refreshes); the
        # FINAL update (with the triage_result card) raises, and the
        # handler should fall back to create_message.
        update_calls = {"count": 0}

        async def update_side_effect(*args, **kwargs):
            update_calls["count"] += 1
            cards = kwargs.get("cards_v2") or []
            if cards and cards[0]["cardId"] == "triage_result":
                raise RuntimeError("simulated API failure")
            return {"name": "spaces/abc/messages/PROG-3"}

        chat_client.update_message = AsyncMock(side_effect=update_side_effect)
        handler = GoogleChatHandler(
            runner=progressive_runner,
            config=config,
            store=store,
            chat_client=chat_client,
        )
        event = {
            "type": "MESSAGE",
            "message": {"argumentText": "triage"},
            "user": {"email": "ops@example.com"},
            "space": {"name": "spaces/abc"},
        }
        await handler.handle_event(event)
        for task in list(handler._background_tasks):
            await task

        # create_message was called twice: once for the progress card,
        # once for the fallback after PATCH failure.
        assert chat_client.create_message.await_count == 2

    @pytest.mark.asyncio
    async def test_runtime_error_replaces_progress_with_error_card(self, config, store):
        """An exception during the run must overwrite the progress card."""
        runner = MagicMock()

        async def boom(*args, **kwargs):
            raise RuntimeError("boom")
            yield  # pragma: no cover — unreachable, keeps this an async gen

        runner.run_async.side_effect = boom

        chat_client = MagicMock()
        chat_client.create_message = AsyncMock(return_value={"name": "spaces/abc/messages/PROG-4"})
        chat_client.update_message = AsyncMock(return_value={})
        handler = GoogleChatHandler(
            runner=runner, config=config, store=store, chat_client=chat_client
        )
        event = {
            "type": "MESSAGE",
            "message": {"argumentText": "triage"},
            "user": {"email": "ops@example.com"},
            "space": {"name": "spaces/abc"},
        }
        await handler.handle_event(event)
        for task in list(handler._background_tasks):
            await task

        # Final update_message must have been called with the error card.
        all_calls = chat_client.update_message.await_args_list
        assert any(
            (c.kwargs.get("cards_v2") or [{}])[0].get("cardId") == "error" for c in all_calls
        )

    @pytest.mark.asyncio
    async def test_non_triage_final_update_clears_progress_card(self, config, store):
        """Regression: final PATCH must include cardsV2 in the updateMask
        to clear the progress card, otherwise Chat renders both the new
        text AND the stale 'Investigating…' card on the same message.
        """
        runner = MagicMock()

        async def plain_text_run(*args, **kwargs):
            event = MagicMock()
            event.author = "orrery_assistant"
            event.content = types.Content(
                role="model",
                parts=[types.Part.from_text(text="Found 2 deployments in gatekeeper-system.")],
            )
            event.actions = MagicMock()
            event.actions.state_delta = {}
            event.get_function_calls = lambda: []
            yield event

        runner.run_async.side_effect = plain_text_run

        chat_client = MagicMock()
        chat_client.create_message = AsyncMock(return_value={"name": "spaces/abc/messages/PROG-X"})
        chat_client.update_message = AsyncMock(return_value={"name": "spaces/abc/messages/PROG-X"})
        handler = GoogleChatHandler(
            runner=runner, config=config, store=store, chat_client=chat_client
        )
        event = {
            "type": "MESSAGE",
            "message": {"argumentText": "list deployments"},
            "user": {"email": "ops@example.com"},
            "space": {"name": "spaces/abc"},
        }
        await handler.handle_event(event)
        for task in list(handler._background_tasks):
            await task

        last_call = chat_client.update_message.await_args_list[-1]
        # cards_v2 must be explicitly passed (even empty) so the mask
        # includes "cardsV2" and Chat drops the progress card.
        assert "cards_v2" in last_call.kwargs
        assert last_call.kwargs["cards_v2"] == []
        assert "Found 2 deployments" in last_call.kwargs["text"]

    @pytest.mark.asyncio
    async def test_run_remediation_click_dispatches_new_run(
        self, config, store, progressive_runner
    ):
        chat_client = MagicMock()
        chat_client.create_message = AsyncMock(return_value={"name": "spaces/abc/messages/REM-1"})
        chat_client.update_message = AsyncMock(return_value={})
        handler = GoogleChatHandler(
            runner=progressive_runner,
            config=config,
            store=store,
            chat_client=chat_client,
        )
        event = {
            "type": "CARD_CLICKED",
            "common": {"invokedFunction": "run_remediation", "parameters": []},
            "user": {"email": "ops@example.com", "displayName": "Ops User"},
            "space": {"name": "spaces/abc"},
            "message": {"thread": {"name": "threads/42"}},
        }
        await handler.handle_event(event)
        for task in list(handler._background_tasks):
            await task

        # Runner was invoked with the remediation prompt in the right session.
        progressive_runner.run_async.assert_called_once()
        call_kwargs = progressive_runner.run_async.call_args.kwargs
        assert call_kwargs["session_id"] == "gchat:threads/42"
        assert "remediation_pipeline" in call_kwargs["new_message"].parts[0].text
