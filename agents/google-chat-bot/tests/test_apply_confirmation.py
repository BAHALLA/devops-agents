"""Tests for ``apply_chat_confirmation`` tree-walking."""

from __future__ import annotations

from typing import Any

from google_chat_bot.confirmation import ConfirmationStore, apply_chat_confirmation


class _FakeTool:
    """Minimal ADK AgentTool stand-in — carries a wrapped agent."""

    def __init__(self, agent: Any | None = None) -> None:
        self.agent = agent


class _FakeLlmAgent:
    """LlmAgent stand-in — identified by having a ``tools`` attribute."""

    def __init__(
        self,
        name: str,
        tools: list[Any] | None = None,
        sub_agents: list[Any] | None = None,
    ) -> None:
        self.name = name
        self.tools = tools if tools is not None else []
        self.sub_agents = sub_agents or []
        self.before_tool_callback: Any = None


class _FakeWorkflowAgent:
    """SequentialAgent/ParallelAgent/LoopAgent stand-in — no ``tools``."""

    def __init__(self, name: str, sub_agents: list[Any] | None = None) -> None:
        self.name = name
        self.sub_agents = sub_agents or []


def test_walks_sub_agents_and_agent_tools():
    """Every LlmAgent reachable via sub_agents or AgentTool gets wired."""
    # Root → SequentialAgent → two leaf LlmAgents
    leaf_a = _FakeLlmAgent("leaf_a")
    leaf_b = _FakeLlmAgent("leaf_b")
    seq = _FakeWorkflowAgent("seq", sub_agents=[leaf_a, leaf_b])

    # Root also exposes two AgentTool-wrapped specialists
    specialist_x = _FakeLlmAgent("specialist_x")
    specialist_y = _FakeLlmAgent("specialist_y")
    root = _FakeLlmAgent(
        "root",
        tools=[_FakeTool(specialist_x), _FakeTool(specialist_y), object()],
        sub_agents=[seq],
    )

    store = ConfirmationStore()
    wired = apply_chat_confirmation(root, store)

    # 1 root + 2 leaves + 2 specialists = 5 LlmAgents; workflow agent skipped.
    assert wired == 5
    for agent in (root, leaf_a, leaf_b, specialist_x, specialist_y):
        assert callable(agent.before_tool_callback), f"{agent.name} not wired"

    # Non-agent tool entries (``object()``) are tolerated.


def test_skips_workflow_agents():
    """Workflow agents have no tools attribute and should be skipped."""
    workflow = _FakeWorkflowAgent("workflow_only")
    store = ConfirmationStore()
    wired = apply_chat_confirmation(workflow, store)
    assert wired == 0
    assert not hasattr(workflow, "before_tool_callback") or (
        workflow.__dict__.get("before_tool_callback") is None
    )


def test_cycle_safe():
    """A child that points back to its parent must not loop forever."""
    a = _FakeLlmAgent("a")
    b = _FakeLlmAgent("b", sub_agents=[a])
    a.sub_agents.append(b)  # cycle
    store = ConfirmationStore()
    wired = apply_chat_confirmation(a, store)
    assert wired == 2  # each visited exactly once


def test_idempotent_rewire():
    """Calling twice is safe — second pass overwrites with same callback."""
    leaf = _FakeLlmAgent("leaf")
    root = _FakeLlmAgent("root", sub_agents=[leaf])
    store = ConfirmationStore()
    apply_chat_confirmation(root, store)
    first = root.before_tool_callback
    apply_chat_confirmation(root, store)
    # The callback is recreated each call, but the wiring doesn't error
    # and remains callable.
    assert callable(root.before_tool_callback)
    assert first is not root.before_tool_callback  # fresh closure on re-wire


def test_real_orrery_assistant_tree():
    """End-to-end: apply the walker to the actual root agent graph.

    This is the test that would have caught the original regression
    (sub-agent tools falling back to CLI-style text confirmation).
    """
    from orrery_assistant.agent import root_agent

    store = ConfirmationStore()
    wired = apply_chat_confirmation(root_agent, store)

    # At minimum root + 5 triage health checkers + summarizer + journal
    # writer + 6 AgentTool specialists (kafka/k8s/obs/es/docker/journal)
    # + remediation sub-agents. Exact count may drift as agents land —
    # assert a reasonable lower bound instead of an exact number.
    assert wired >= 10, f"expected ≥10 LlmAgents wired, got {wired}"

    # Spot-check a known sub-agent: the k8s specialist exposed as an
    # AgentTool on root must have the Chat callback (this is the exact
    # regression path from the conversation log).
    k8s_agent = next(
        (
            getattr(t, "agent")  # noqa: B009
            for t in root_agent.tools
            if getattr(t, "agent", None) is not None
            and getattr(getattr(t, "agent"), "name", "") == "k8s_health_agent"  # noqa: B009
        ),
        None,
    )
    assert k8s_agent is not None, "k8s_health_agent AgentTool not found on root"
    assert callable(k8s_agent.before_tool_callback)
