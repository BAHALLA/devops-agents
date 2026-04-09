"""Closed-loop remediation agents using ADK LoopAgent.

Provides a remediation loop pattern: Act -> Verify -> (exit or retry).
The loop runs up to ``max_iterations`` times before giving up, and a
verifier agent can signal early exit via the ``exit_loop`` tool.

RBAC: The remediation actor inherits the guardrails from the tools it
calls (@destructive, @confirm), so only operator/admin roles can trigger
destructive actions inside the loop.
"""

from google.adk.tools.tool_context import ToolContext

from ai_agents_core import (
    create_agent,
    create_loop_agent,
    create_sequential_agent,
)
from k8s_health_agent.tools import (
    describe_pod,
    get_deployment_status,
    get_events,
    get_pod_logs,
    list_pods,
    restart_deployment,
    rollback_deployment,
    scale_deployment,
)
from kafka_health_agent.tools import get_consumer_lag, get_kafka_cluster_health
from ops_journal_agent.tools import log_operation

# ── Exit loop tool ────────────────────────────────────────────────────


async def exit_loop(
    reason: str,
    tool_context: ToolContext,
) -> dict:
    """Signal that remediation is complete and the loop should stop.

    Args:
        reason: Why remediation is considered complete.
        tool_context: ADK tool context (injected automatically).

    Returns:
        A dict confirming the loop exit.
    """
    tool_context.actions.escalate = True
    return {"status": "remediation_complete", "reason": reason}


# ── Remediation actor ─────────────────────────────────────────────────

remediation_actor = create_agent(
    name="remediation_actor",
    description="Takes remediation actions based on the triage diagnosis.",
    instruction=(
        "You are a DevOps remediation agent. Read the triage report from "
        "session state (triage_report) and the previous verification result "
        "(verification_result) if available.\n\n"
        "Based on the diagnosis, take the SINGLE most appropriate remediation "
        "action using your tools. Choose from:\n"
        "- restart_deployment: For pods in CrashLoopBackOff or OOMKilled\n"
        "- scale_deployment: For high resource usage or consumer lag\n"
        "- rollback_deployment: For failed deployments after a bad release\n\n"
        "If a previous verification shows your last action didn't help, "
        "try a DIFFERENT approach. Do not repeat the same action.\n\n"
        "Record what you did in your output so the verifier can check it."
    ),
    tools=[
        restart_deployment,
        scale_deployment,
        rollback_deployment,
        log_operation,
    ],
    output_key="remediation_action",
)

# ── Remediation verifier ──────────────────────────────────────────────

remediation_verifier = create_agent(
    name="remediation_verifier",
    description="Verifies whether the last remediation action was successful.",
    instruction=(
        "You are a remediation verifier. Check whether the remediation action "
        "described in session state (remediation_action) was successful.\n\n"
        "Use your diagnostic tools to verify the current system state:\n"
        "- get_deployment_status: Check if replicas are ready and available\n"
        "- list_pods: Check if pods are Running and not crash-looping\n"
        "- describe_pod: Get details on specific problematic pods\n"
        "- get_pod_logs: Check logs for errors after the remediation\n"
        "- get_events: Look for new warnings or errors\n"
        "- get_consumer_lag: Check if Kafka lag is decreasing\n"
        "- get_kafka_cluster_health: Verify Kafka cluster status\n\n"
        "If the issue is RESOLVED, call exit_loop with a reason explaining "
        "what was fixed.\n\n"
        "If the issue PERSISTS, describe what is still wrong in your output "
        "so the actor can try a different approach on the next iteration."
    ),
    tools=[
        get_deployment_status,
        list_pods,
        describe_pod,
        get_pod_logs,
        get_events,
        get_consumer_lag,
        get_kafka_cluster_health,
        exit_loop,
    ],
    output_key="verification_result",
)

# ── Remediation loop ──────────────────────────────────────────────────

remediation_loop = create_loop_agent(
    name="remediation_loop",
    description=(
        "Closed-loop remediation: takes an action, verifies it worked, "
        "and retries with a different approach if not (up to 3 iterations)."
    ),
    sub_agents=[remediation_actor, remediation_verifier],
    max_iterations=3,
)

# ── Remediation summary ──────────────────────────────────────────────

remediation_summarizer = create_agent(
    name="remediation_summarizer",
    description="Summarizes the remediation outcome.",
    instruction=(
        "Read the session state: remediation_action and verification_result.\n\n"
        "Write a concise remediation summary including:\n"
        "1. What issue was found\n"
        "2. What actions were taken (and how many iterations)\n"
        "3. Final outcome: resolved or unresolved\n"
        "4. Recommended follow-up actions if unresolved\n\n"
        "Be concise and actionable."
    ),
    tools=[log_operation],
    output_key="remediation_summary",
)

# ── Full remediation pipeline ─────────────────────────────────────────

remediation_pipeline = create_sequential_agent(
    name="remediation_pipeline",
    description=(
        "Full remediation pipeline: runs the remediation loop, then summarizes the outcome."
    ),
    sub_agents=[remediation_loop, remediation_summarizer],
)
