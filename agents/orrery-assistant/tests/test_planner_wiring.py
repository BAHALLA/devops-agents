"""Structural tests for planner attachment across orrery-assistant agents.

These are deterministic, LLM-free checks that verify the right agents pick
up a planner when ``ORRERY_PLANNER`` is set, and tool-leaf agents stay
planner-free regardless. They complement the per-planner unit tests in
``core/tests/test_base.py::TestResolvePlanner`` and the agent-level evals
in ``test_orrery_eval.py``.

The agent module reads ``ORRERY_PLANNER`` once at import time, so each
test reloads the module after setting the env var.
"""

import importlib
import sys

import pytest
from google.adk.planners import BuiltInPlanner, PlanReActPlanner


def _reload_agent():
    """Reload the agent + remediation modules so module-level
    ``resolve_planner()`` re-runs with the current env."""
    for name in (
        "orrery_assistant.remediation",
        "orrery_assistant.agent",
    ):
        if name in sys.modules:
            importlib.reload(sys.modules[name])
        else:
            importlib.import_module(name)
    return (
        sys.modules["orrery_assistant.agent"],
        sys.modules["orrery_assistant.remediation"],
    )


@pytest.fixture
def clean_planner_env(monkeypatch):
    """Pin ORRERY_PLANNER to ``none`` so a developer-set value in the
    root .env does not leak through ``load_agent_env()`` on reload.

    Tests that need a different value override via ``setenv``."""
    monkeypatch.setenv("ORRERY_PLANNER", "none")
    for var in (
        "ORRERY_PLANNER_THINKING_BUDGET",
        "ORRERY_PLANNER_INCLUDE_THOUGHTS",
        "MODEL_PROVIDER",
    ):
        monkeypatch.delenv(var, raising=False)


class TestPlannerWiring:
    def test_default_no_planner(self, clean_planner_env):
        agent_mod, rem_mod = _reload_agent()
        # All agents — including the three that *can* opt in — start with
        # no planner when ORRERY_PLANNER is unset. Zero behavior change.
        assert agent_mod.root_agent.planner is None
        assert agent_mod.triage_summarizer.planner is None
        assert rem_mod.remediation_actor.planner is None

    def test_plan_react_attaches_to_reasoning_agents(self, clean_planner_env, monkeypatch):
        monkeypatch.setenv("ORRERY_PLANNER", "plan_react")
        agent_mod, rem_mod = _reload_agent()

        # Three reasoning-heavy agents opt in.
        assert isinstance(agent_mod.root_agent.planner, PlanReActPlanner)
        assert isinstance(agent_mod.triage_summarizer.planner, PlanReActPlanner)
        assert isinstance(rem_mod.remediation_actor.planner, PlanReActPlanner)

    def test_leaves_stay_planner_free_under_plan_react(self, clean_planner_env, monkeypatch):
        """Per-system health checkers, the journal writer, and the
        remediation verifier do one short tool sequence per turn — adding
        a planner there would burn latency without changing the output."""
        monkeypatch.setenv("ORRERY_PLANNER", "plan_react")
        agent_mod, rem_mod = _reload_agent()

        leaf_agents = [
            agent_mod.kafka_health_checker,
            agent_mod.k8s_health_checker,
            agent_mod.docker_health_checker,
            agent_mod.observability_health_checker,
            agent_mod.elasticsearch_health_checker,
            agent_mod.journal_writer,
            rem_mod.remediation_verifier,
        ]
        for leaf in leaf_agents:
            assert leaf.planner is None, (
                f"{leaf.name} should stay planner-free; planning belongs on "
                f"orchestration / synthesis agents, not on tool-leaf agents."
            )

    def test_builtin_falls_back_for_non_gemini(self, clean_planner_env, monkeypatch, caplog):
        """builtin requires Gemini; any other provider falls back to no
        planner with a warning so LiteLLM-routed deployments are silent."""
        monkeypatch.setenv("ORRERY_PLANNER", "builtin")
        monkeypatch.setenv("MODEL_PROVIDER", "anthropic")
        with caplog.at_level("WARNING", logger="orrery.base"):
            agent_mod, rem_mod = _reload_agent()
        assert agent_mod.root_agent.planner is None
        assert agent_mod.triage_summarizer.planner is None
        assert rem_mod.remediation_actor.planner is None

    def test_builtin_attaches_under_gemini(self, clean_planner_env, monkeypatch):
        monkeypatch.setenv("ORRERY_PLANNER", "builtin")
        # MODEL_PROVIDER unset defaults to gemini in resolve_planner.
        agent_mod, rem_mod = _reload_agent()
        assert isinstance(agent_mod.root_agent.planner, BuiltInPlanner)
        assert isinstance(agent_mod.triage_summarizer.planner, BuiltInPlanner)
        assert isinstance(rem_mod.remediation_actor.planner, BuiltInPlanner)
