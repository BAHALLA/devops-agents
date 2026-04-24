"""Regression guard on the k8s_health_agent instruction.

The agent must advertise an explicit capability list so the LLM doesn't
offer mutations it can't perform (e.g. patch/edit/kubectl apply). This
test keeps that contract pinned.
"""

from __future__ import annotations

from k8s_health_agent.agent import root_agent


def test_instruction_lists_only_supported_mutations():
    assert isinstance(root_agent.instruction, str)
    instr = root_agent.instruction.lower()
    # Supported mutations are named.
    for word in (
        "scale_deployment",
        "restart_deployment",
        "rollback_deployment",
        "patch_deployment",
        "patch_statefulset",
    ):
        assert word in instr, f"missing capability mention: {word}"


def test_instruction_forbids_unsupported_mutations():
    """The agent must NOT promise it can apply YAML or run kubectl."""
    assert isinstance(root_agent.instruction, str)
    instr = root_agent.instruction.lower()
    # These phrases must appear inside a "cannot / never" context.
    assert "cannot" in instr or "can't" in instr
    # Explicitly mentioned as unsupported.
    for forbidden in ("apply", "kubectl", "configmaps"):
        assert forbidden in instr, (
            f"instruction should explicitly mention {forbidden!r} as unsupported"
        )


def test_never_promise_clause_present():
    """Explicit negative guardrail on capability hallucinations."""
    assert isinstance(root_agent.instruction, str)
    instr = root_agent.instruction.lower()
    assert "never promise" in instr or "never offer" in instr or "don't promise" in instr
