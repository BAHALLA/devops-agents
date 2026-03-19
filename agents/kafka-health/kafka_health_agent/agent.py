from ai_agents_core import (
    CircuitBreaker,
    MetricsCollector,
    audit_logger,
    authorize,
    create_agent,
    graceful_tool_error,
    load_agent_env,
    require_confirmation,
)

from .tools import (
    create_kafka_topic,
    delete_kafka_topic,
    describe_consumer_groups,
    get_consumer_lag,
    get_kafka_cluster_health,
    get_topic_metadata,
    list_consumer_groups,
    list_kafka_topics,
)

load_agent_env(__file__)

_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
_metrics = MetricsCollector(circuit_breaker=_breaker)

root_agent = create_agent(
    name="kafka_health_agent",
    description="Agent to monitor and report on the health of a Kafka cluster.",
    instruction=(
        "You are a specialized agent for Kafka monitoring. You can check cluster health, "
        "manage topics, and inspect consumer groups and lag. Use the provided tools to "
        "retrieve cluster information and troubleshoot performance or connectivity issues.\n\n"
        "When a tool returns a 'confirmation_required' status, you MUST ask the user "
        "to confirm before calling the tool again."
    ),
    tools=[
        get_kafka_cluster_health,
        list_kafka_topics,
        create_kafka_topic,
        delete_kafka_topic,
        get_topic_metadata,
        list_consumer_groups,
        describe_consumer_groups,
        get_consumer_lag,
    ],
    before_tool_callback=[
        authorize(),
        require_confirmation(),
        _breaker.before_tool_callback(),
        _metrics.before_tool_callback(),
    ],
    after_tool_callback=[
        audit_logger(),
        _breaker.after_tool_callback(),
        _metrics.after_tool_callback(),
    ],
    on_tool_error_callback=[
        _breaker.on_tool_error_callback(),
        _metrics.on_tool_error_callback(),
        graceful_tool_error(),
    ],
)
