"""Tests for the Google Chat card builders."""

from google_chat_bot.cards import (
    build_confirmation_card,
    build_error_card,
    build_progress_card,
    build_triage_result_card,
    classify_status,
)

from orrery_core import LEVEL_CONFIRM, LEVEL_DESTRUCTIVE


def test_confirmation_card_structure():
    card = build_confirmation_card(
        tool_name="restart_pod",
        args={"name": "api", "ns": "prod"},
        reason="restarts a pod",
        level=LEVEL_CONFIRM,
        action_id="abc123",
    )
    assert card["cardId"] == "abc123"

    header = card["card"]["header"]
    assert "restart_pod" in header["title"]
    assert header["subtitle"] == "Safety Guardrail"

    widgets = card["card"]["sections"][0]["widgets"]
    reason_widget = next(
        w for w in widgets if "Reason" in w.get("textParagraph", {}).get("text", "")
    )
    assert "restarts a pod" in reason_widget["textParagraph"]["text"]

    args_widget = next(
        w for w in widgets if "Arguments" in w.get("textParagraph", {}).get("text", "")
    )
    assert "name=api" in args_widget["textParagraph"]["text"]
    assert "ns=prod" in args_widget["textParagraph"]["text"]

    # Verify quick command instructions are present
    instruction_widget = next(
        w
        for w in widgets
        if "Send the <b>Approve</b> quick command" in w.get("textParagraph", {}).get("text", "")
    )
    assert instruction_widget is not None


def test_destructive_card_uses_warning_emoji():
    card = build_confirmation_card(
        tool_name="drop_topic",
        args={},
        reason="deletes Kafka data",
        level=LEVEL_DESTRUCTIVE,
        action_id="xyz",
    )
    title = card["card"]["header"]["title"]
    assert title.startswith("\u26a0")  # warning sign
    assert "DESTRUCTIVE" in title


def test_card_handles_empty_args():
    card = build_confirmation_card(
        tool_name="list_pods",
        args={},
        reason="",
        level=LEVEL_CONFIRM,
        action_id="id1",
    )
    widgets = card["card"]["sections"][0]["widgets"]
    # No reason widget when reason is empty.
    assert not any("Reason" in w.get("textParagraph", {}).get("text", "") for w in widgets)
    # Args widget still present with "none" placeholder.
    args_widget = next(
        w for w in widgets if "Arguments" in w.get("textParagraph", {}).get("text", "")
    )
    assert "none" in args_widget["textParagraph"]["text"]


def _all_widget_text(card: dict) -> str:
    lines: list[str] = []
    for section in card["card"].get("sections", []):
        for widget in section.get("widgets", []):
            tp = widget.get("textParagraph")
            if tp:
                lines.append(tp.get("text", ""))
    return "\n".join(lines)


class TestClassifyStatus:
    def test_none_is_pending(self):
        assert classify_status(None) == "pending"

    def test_empty_is_pending(self):
        assert classify_status("") == "pending"

    def test_red_cluster_is_fail(self):
        assert classify_status("cluster health is RED") == "fail"

    def test_crashloop_is_fail(self):
        assert classify_status("pod in CrashLoopBackOff") == "fail"

    def test_yellow_is_warn(self):
        assert classify_status("cluster is yellow") == "warn"

    def test_degraded_is_warn(self):
        assert classify_status("service degraded") == "warn"

    def test_healthy_is_ok(self):
        assert classify_status("everything green and healthy") == "ok"


class TestProgressCard:
    def test_shape_with_no_chips(self):
        card = build_progress_card(
            current_agent="kafka_health_checker",
            current_tool="list_consumer_groups",
            subsystem_chips={},
            remediation=None,
            elapsed_seconds=3.0,
        )
        assert card["cardId"] == "progress"
        assert "Investigating" in card["card"]["header"]["title"]
        text = _all_widget_text(card)
        assert "Checking Kafka" in text  # friendly agent label
        assert "list_consumer_groups" in text
        assert "Elapsed 3s" in text

    def test_chips_rendered_when_subsystem_reports(self):
        card = build_progress_card(
            current_agent="triage_summarizer",
            current_tool=None,
            subsystem_chips={
                "kafka_status": {"status": "ok", "summary": "all brokers up"},
                "k8s_status": {"status": "fail", "summary": "api pod crashlooping"},
            },
            remediation=None,
            elapsed_seconds=0.0,
        )
        text = _all_widget_text(card)
        assert "Kafka" in text and "all brokers up" in text
        assert "Kubernetes" in text and "api pod crashlooping" in text
        # Severity icons appear.
        assert "❌" in text  # ❌
        assert "✅" in text  # ✅

    def test_remediation_panel_shows_when_present(self):
        card = build_progress_card(
            current_agent="remediation_actor",
            current_tool=None,
            subsystem_chips={},
            remediation={"remediation_action": "restarting api deployment"},
            elapsed_seconds=0.0,
        )
        text = _all_widget_text(card)
        assert "Remediation" in text
        assert "restarting api deployment" in text


class TestTriageResultCard:
    def _chips(self):
        return {
            "kafka_status": {"status": "ok", "summary": "all green"},
            "k8s_status": {"status": "fail", "summary": "api pod crashlooping"},
            "docker_status": {"status": "ok", "summary": "4 containers running"},
            "observability_status": {"status": "warn", "summary": "2 firing alerts"},
            "elasticsearch_status": {"status": "ok", "summary": "cluster green"},
        }

    def test_overall_fail_dominates(self):
        card = build_triage_result_card(
            subsystem_chips=self._chips(),
            triage_report="Overall degraded, k8s is critical.",
            user_role="operator",
        )
        assert "Critical" in card["card"]["header"]["subtitle"]

    def test_all_ok_shows_healthy(self):
        chips = {
            "kafka_status": {"status": "ok", "summary": "ok"},
            "k8s_status": {"status": "ok", "summary": "ok"},
        }
        card = build_triage_result_card(
            subsystem_chips=chips, triage_report="fine", user_role="viewer"
        )
        assert "healthy" in card["card"]["header"]["subtitle"].lower()

    def test_remediate_instruction_visible_for_operator_on_fail(self):
        card = build_triage_result_card(
            subsystem_chips=self._chips(),
            triage_report="bad",
            user_role="operator",
        )
        text = _all_widget_text(card)
        assert "<b>Remediate</b> quick command" in text

    def test_remediate_instruction_hidden_for_viewer(self):
        card = build_triage_result_card(
            subsystem_chips=self._chips(),
            triage_report="bad",
            user_role="viewer",
        )
        text = _all_widget_text(card)
        assert "<b>Remediate</b> quick command" not in text

    def test_remediate_instruction_hidden_when_healthy(self):
        chips = {
            "kafka_status": {"status": "ok", "summary": "ok"},
            "k8s_status": {"status": "ok", "summary": "ok"},
        }
        card = build_triage_result_card(
            subsystem_chips=chips, triage_report="fine", user_role="admin"
        )
        text = _all_widget_text(card)
        assert "<b>Remediate</b> quick command" not in text

    def test_subsystem_sections_present(self):
        card = build_triage_result_card(
            subsystem_chips=self._chips(),
            triage_report="full summary",
            user_role="operator",
        )
        text = _all_widget_text(card)
        assert "Kafka" in text
        assert "Kubernetes" in text
        assert "Elasticsearch" in text
        assert "full summary" in text


def test_error_card_shape():
    card = build_error_card("Something went wrong")
    assert card["cardId"] == "error"
    text = _all_widget_text(card)
    assert "Something went wrong" in text
