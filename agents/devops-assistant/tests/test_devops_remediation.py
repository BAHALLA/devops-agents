"""Unit tests for the remediation loop module."""

from unittest.mock import MagicMock

import pytest
from google.adk.agents import LoopAgent

# Importing agent validates that the full module loads without errors
from devops_assistant.agent import root_agent  # noqa: F401
from devops_assistant.remediation import (
    exit_loop,
    remediation_actor,
    remediation_loop,
    remediation_pipeline,
    remediation_summarizer,
    remediation_verifier,
)

# ── exit_loop tool ───────────────────────────────────────────────────


class TestExitLoop:
    @pytest.mark.asyncio
    async def test_sets_escalate_flag(self):
        ctx = MagicMock()
        result = await exit_loop("issue resolved", tool_context=ctx)
        assert ctx.actions.escalate is True
        assert result["status"] == "remediation_complete"
        assert result["reason"] == "issue resolved"

    @pytest.mark.asyncio
    async def test_returns_reason(self):
        ctx = MagicMock()
        result = await exit_loop("pods healthy", tool_context=ctx)
        assert result["reason"] == "pods healthy"


# ── Agent wiring ─────────────────────────────────────────────────────


class TestRemediationAgentWiring:
    def test_remediation_actor_has_tools(self):
        tool_names = {
            getattr(t, "name", getattr(t, "__name__", None)) for t in remediation_actor.tools
        }
        assert "restart_deployment" in tool_names
        assert "scale_deployment" in tool_names
        assert "rollback_deployment" in tool_names
        assert "log_operation" in tool_names

    def test_remediation_actor_has_output_key(self):
        assert remediation_actor.output_key == "remediation_action"

    def test_remediation_verifier_has_tools(self):
        tool_names = {
            getattr(t, "name", getattr(t, "__name__", None)) for t in remediation_verifier.tools
        }
        assert "get_deployment_status" in tool_names
        assert "list_pods" in tool_names
        assert "get_pod_logs" in tool_names
        assert "exit_loop" in tool_names

    def test_remediation_verifier_has_output_key(self):
        assert remediation_verifier.output_key == "verification_result"

    def test_remediation_loop_is_loop_agent(self):
        assert isinstance(remediation_loop, LoopAgent)

    def test_remediation_loop_max_iterations(self):
        assert remediation_loop.max_iterations == 3

    def test_remediation_loop_has_actor_and_verifier(self):
        names = [a.name for a in remediation_loop.sub_agents]
        assert names == ["remediation_actor", "remediation_verifier"]

    def test_remediation_pipeline_includes_loop_and_summarizer(self):
        names = [a.name for a in remediation_pipeline.sub_agents]
        assert names == ["remediation_loop", "remediation_summarizer"]

    def test_remediation_summarizer_has_output_key(self):
        assert remediation_summarizer.output_key == "remediation_summary"
