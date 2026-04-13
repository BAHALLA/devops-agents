"""Unit tests for create_loop_agent factory function."""

from google.adk.agents import LoopAgent

from orrery_core.base import create_agent, create_loop_agent


def _make_sub_agent(name: str):
    return create_agent(
        name=name,
        description=f"Test agent {name}",
        instruction="Do nothing.",
        tools=[],
    )


class TestCreateLoopAgent:
    def test_returns_loop_agent(self):
        agent = create_loop_agent(
            name="test_loop",
            sub_agents=[_make_sub_agent("a")],
        )
        assert isinstance(agent, LoopAgent)

    def test_name_and_description(self):
        agent = create_loop_agent(
            name="my_loop",
            description="A test loop",
            sub_agents=[_make_sub_agent("a")],
        )
        assert agent.name == "my_loop"
        assert agent.description == "A test loop"

    def test_default_max_iterations(self):
        agent = create_loop_agent(
            name="test_loop",
            sub_agents=[_make_sub_agent("a")],
        )
        assert agent.max_iterations == 3

    def test_custom_max_iterations(self):
        agent = create_loop_agent(
            name="test_loop",
            sub_agents=[_make_sub_agent("a")],
            max_iterations=5,
        )
        assert agent.max_iterations == 5

    def test_sub_agents_wired(self):
        a = _make_sub_agent("actor")
        b = _make_sub_agent("verifier")
        agent = create_loop_agent(
            name="test_loop",
            sub_agents=[a, b],
        )
        assert len(agent.sub_agents) == 2
        assert agent.sub_agents[0].name == "actor"
        assert agent.sub_agents[1].name == "verifier"
