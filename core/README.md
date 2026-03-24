# ai-agents-core

Shared library providing the foundation for all agents: agent factory, RBAC, guardrails, input validation, audit logging, and typed configuration.

## Agent Factory

### `create_agent()`

Creates an ADK Agent with sensible defaults and optional safety hooks.

```python
from ai_agents_core import create_agent, load_agent_env, require_confirmation, audit_logger

load_agent_env(__file__)

root_agent = create_agent(
    name="my_agent",
    description="What this agent does.",
    instruction="How the agent should behave.",
    tools=[my_tool, another_tool],
    before_tool_callback=require_confirmation(),   # guardrails
    after_tool_callback=audit_logger(),             # audit logging
)
```

| Parameter | Description |
|-----------|-------------|
| `name` | Agent name (used by ADK for routing) |
| `description` | Used by parent orchestrators to decide when to delegate |
| `instruction` | System prompt for the agent |
| `tools` | List of tool functions |
| `model` | Override model — can be a string (Gemini) or `BaseLlm` instance (LiteLlm). When `None`, resolved from `MODEL_PROVIDER`/`MODEL_NAME` env vars via `resolve_model()` |
| `sub_agents` | List of child agents for orchestrators |
| `before_tool_callback` | Called before each tool — return a dict to block execution |
| `after_tool_callback` | Called after each tool — return a dict to override the result |
| `on_tool_error_callback` | Called when a tool raises an exception — return a dict for graceful recovery |
| `on_model_error_callback` | Called when the model call fails — return an `LlmResponse` to recover |
| `output_key` | Session state key to store this agent's output |

### `create_sequential_agent()` / `create_parallel_agent()`

Factory functions for structured multi-agent workflows that don't rely on LLM delegation.

```python
from ai_agents_core import create_agent, create_sequential_agent, create_parallel_agent

# Run health checks in parallel
health_checks = create_parallel_agent(
    name="health_checks",
    description="Runs all health checks concurrently.",
    sub_agents=[kafka_checker, k8s_checker, docker_checker],
)

# Sequential pipeline: check → summarize → save
triage = create_sequential_agent(
    name="incident_triage",
    description="Full incident triage pipeline.",
    sub_agents=[health_checks, summarizer, journal_writer],
)
```

Sub-agents pass data via `output_key`, which writes to session state for downstream agents to read.

### `load_agent_env(__file__)`

Loads the `.env` file located next to the calling module.

---

## Error Handling

Error callbacks prevent agents from crashing when tools or model calls fail. Instead, the error is logged and returned as a structured response so the LLM can reason about it.

### `graceful_tool_error()`

An `on_tool_error_callback` that catches tool exceptions and returns a dict:

```python
from ai_agents_core import create_agent, graceful_tool_error

root_agent = create_agent(
    ...,
    on_tool_error_callback=graceful_tool_error(),
)
```

When a tool raises (e.g., Kafka timeout, K8s API error), the LLM receives:

```json
{"status": "error", "error_type": "KafkaException", "message": "Tool 'get_kafka_cluster_health' failed: broker down"}
```

The LLM can then inform the user or try an alternative approach.

### `graceful_model_error()`

An `on_model_error_callback` that returns a friendly message when the LLM API call fails:

```python
from ai_agents_core import create_agent, graceful_model_error

root_agent = create_agent(
    ...,
    on_model_error_callback=graceful_model_error(),
)
```

---

## Resilience

Fault-tolerance utilities for handling transient failures and service outages.

### `CircuitBreaker`

Per-tool circuit breaker that integrates with ADK callbacks. When a tool exceeds the failure threshold, subsequent calls are short-circuited until a recovery timeout allows a probe.

```python
from ai_agents_core import CircuitBreaker, graceful_tool_error, audit_logger, authorize, require_confirmation

breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

root_agent = create_agent(
    ...,
    before_tool_callback=[authorize(), require_confirmation(), breaker.before_tool_callback()],
    after_tool_callback=[audit_logger(), breaker.after_tool_callback()],
    on_tool_error_callback=[breaker.on_tool_error_callback(), graceful_tool_error()],
)
```

| State | Behavior |
|-------|----------|
| **Closed** | All calls pass through normally |
| **Open** | Calls are blocked with `{"error_type": "CircuitOpen", ...}` |
| **Half-open** | One probe call is allowed after `recovery_timeout` seconds |

The circuit breaker error callback returns `None` so it composes with `graceful_tool_error()` — it records the failure, then the graceful handler produces the response dict.

### `@with_retry`

Decorator for tool functions that adds retry with exponential backoff and jitter.

```python
from ai_agents_core import with_retry

@with_retry(max_retries=3, retryable=(ConnectionError, TimeoutError))
def list_kafka_topics(timeout: int = 10) -> dict:
    ...
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_retries` | `3` | Max retry attempts (total calls = max_retries + 1) |
| `base_delay` | `1.0` | Initial backoff delay in seconds |
| `max_delay` | `30.0` | Cap on backoff delay |
| `retryable` | `(ConnectionError, TimeoutError, OSError)` | Exception types that trigger a retry |

Apply `@with_retry` to **read-only** tools that call external services. Do not apply to mutating operations (create, delete) where retries could be dangerous.

---

## Input Validation

Reusable validators for tool inputs. Each returns `None` on success or `{"status": "error", "message": ...}` on failure. Use the walrus operator for concise early-return:

```python
from ai_agents_core.validation import validate_string, validate_positive_int, KAFKA_TOPIC_PATTERN

def create_kafka_topic(topic_name: str, num_partitions: int = 1) -> dict:
    if err := validate_string(topic_name, "topic_name", pattern=KAFKA_TOPIC_PATTERN):
        return err
    if err := validate_positive_int(num_partitions, "num_partitions", max_value=10_000):
        return err
    ...
```

### Available Validators

| Validator | Key Parameters | Description |
|-----------|---------------|-------------|
| `validate_string()` | `min_len`, `max_len`, `pattern` | Length bounds + optional regex |
| `validate_positive_int()` | `min_value`, `max_value` | Integer range (rejects bool, float, str) |
| `validate_url()` | `allowed_schemes` | Scheme allowlist; rejects `javascript:`, `data:`, `file:` |
| `validate_path()` | — | Rejects `..` path traversal |
| `validate_list()` | `min_len`, `max_len` | List length bounds |

### Constants

| Constant | Value | Usage |
|----------|-------|-------|
| `MAX_LOG_LINES` | `10,000` | Cap for log tail parameters |
| `MAX_REPLICAS` | `1,000` | Cap for K8s replica scaling |
| `MAX_PARTITIONS` | `10,000` | Cap for Kafka topic partitions |
| `MAX_REPLICATION_FACTOR` | `10` | Cap for Kafka replication factor |
| `MAX_QUERY_LENGTH` | `5,000` | Cap for Prometheus/Loki queries |
| `K8S_NAME_PATTERN` | `^[a-z0-9]([a-z0-9._-]*[a-z0-9])?$` | Kubernetes resource name format |
| `KAFKA_TOPIC_PATTERN` | `^[a-zA-Z0-9._-]+$` | Kafka topic name format |

---

## Guardrails

Guardrails prevent destructive tools from executing without confirmation. They use ADK's `before_tool_callback` mechanism.

### Marking tools as destructive

```python
from ai_agents_core import destructive

@destructive("permanently deletes the topic and all its data")
def delete_kafka_topic(topic_name: str) -> dict:
    ...
```

The `@destructive()` decorator marks the function with metadata. It does not change the function's behavior — the guardrail callbacks read this metadata at runtime.

### `require_confirmation()`

A `before_tool_callback` that intercepts destructive tools and returns a confirmation prompt instead of executing them. The LLM then asks the user to confirm before retrying.

```python
root_agent = create_agent(
    ...,
    before_tool_callback=require_confirmation(),
)
```

Flow:
1. User asks to delete a topic
2. LLM calls `delete_kafka_topic`
3. Guardrail intercepts → returns `{"status": "confirmation_required", ...}`
4. LLM receives the message and asks the user to confirm
5. User confirms → LLM calls the tool again → guardrail allows it

![Guardrails in action — destructive operation confirmation flow](assets/guardrails-confirmation.png)

*The guardrail intercepts `delete_kafka_topic` (#12-#13), asks the user to confirm (#14), and only executes after explicit confirmation (#15-#18).*

### `dry_run()`

A `before_tool_callback` that blocks all destructive tools permanently, returning a message showing what *would* have been done. Useful for testing or demo environments.

```python
root_agent = create_agent(
    ...,
    before_tool_callback=dry_run(),
)
```

---

## Role-Based Access Control (RBAC)

Three-role hierarchy that reuses existing guardrail metadata to control who can call which tools. See [ADR-001](../docs/adr/001-rbac.md) for the full design rationale.

```
VIEWER (0)   → read-only tools (unguarded)
OPERATOR (1) → + mutating tools (@confirm)
ADMIN (2)    → + destructive tools (@destructive)
```

### `authorize()`

A `before_tool_callback` that checks the user's role from `session.state["user_role"]` and blocks tools that exceed their permission level.

```python
from ai_agents_core import authorize, require_confirmation

root_agent = create_agent(
    ...,
    before_tool_callback=[authorize(), require_confirmation()],
)
```

RBAC runs first (blocks unauthorized users), then guardrails run (prompts authorized users for confirmation). Compose them as a list — the first callback that returns a dict short-circuits.

### `Role` enum

```python
from ai_agents_core import Role

Role.VIEWER    # can call unguarded tools
Role.OPERATOR  # can also call @confirm tools
Role.ADMIN     # can call everything
```

### `RolePolicy`

Maps tools to their minimum required role. By default, roles are inferred from `@destructive`/`@confirm` decorators. Use overrides for exceptions:

```python
from ai_agents_core import RolePolicy, Role, authorize

policy = RolePolicy(overrides={"sensitive_read": Role.OPERATOR})
root_agent = create_agent(
    ...,
    before_tool_callback=authorize(policy),
)
```

### `@requires_role()`

Decorator for explicit role annotation on tools that don't use `@destructive`/`@confirm`:

```python
from ai_agents_core import requires_role, Role

@requires_role(Role.ADMIN)
def manage_users() -> dict:
    ...
```

### `infer_minimum_role()`

Derives the minimum role from guardrail metadata:

```python
from ai_agents_core import infer_minimum_role

infer_minimum_role(tool)  # → Role.ADMIN if @destructive, Role.OPERATOR if @confirm, Role.VIEWER otherwise
```

### Setting the user role

Use `set_user_role()` to assign a role from trusted server-side code. This marks the role as server-set, preventing untrusted session state from escalating privileges.

```python
from ai_agents_core import set_user_role

# In your session creation handler (e.g., Slack bot, API endpoint):
initial_state = {}
set_user_role(initial_state, "admin")  # marks role as trusted
session = session_service.create_session(state=initial_state, ...)
```

Invalid role values default to `viewer`. The role is normalized to lowercase.

### `ensure_default_role()`

A `before_agent_callback` that enforces the default role if no trusted role was set. Prevents privilege escalation from untrusted session state (e.g., a client injecting `"user_role": "admin"` into session state).

```python
from ai_agents_core import ensure_default_role, authorize, require_confirmation, create_agent

root_agent = create_agent(
    ...,
    before_agent_callback=ensure_default_role(),  # forces "viewer" if role not set via set_user_role()
    before_tool_callback=[authorize(), require_confirmation()],
)
```

For the Slack bot, roles are configured via environment variables:

```bash
SLACK_ADMIN_USERS=U12345,U67890
SLACK_OPERATOR_USERS=U11111,U22222
```

Users not listed default to `viewer` (least privilege).

---

## Structured Logging

### `setup_logging()`

Configures the root Python logger with a JSON formatter that outputs structured log lines to stdout — container-friendly and ready for Loki, ELK, Splunk, or Cloud Logging.

```python
from ai_agents_core import setup_logging

setup_logging()  # call once at startup
```

Called automatically by `load_agent_env()`, so all agents get structured logging by default. Every log line is a single JSON object:

```json
{"timestamp": "2026-03-17T21:33:25+00:00", "level": "INFO", "logger": "ai_agents.audit", "message": "tool_call: k8s_health_checker.get_cluster_info", "agent": "k8s_health_checker", "tool": "get_cluster_info", "tool_args": {}, "status": "success", "user_id": "user", "session_id": "abc-123"}
```

Exception stack traces are included as an `"exception"` field when present.

### `JSONFormatter`

The underlying `logging.Formatter` that produces JSON output. Can be used standalone if you need custom handler configuration.

---

## Audit Logging

### `audit_logger()`

An `after_tool_callback` that emits a structured audit entry for every tool invocation via Python's logging system.

```python
root_agent = create_agent(
    ...,
    after_tool_callback=audit_logger(),        # stdout only (recommended)
    # after_tool_callback=audit_logger("audit.jsonl"),  # stdout + local file fallback
)
```

Each audit entry includes:

```json
{
  "timestamp": "2026-03-17T21:33:25+00:00",
  "level": "INFO",
  "logger": "ai_agents.audit",
  "message": "tool_call: observability_agent.query_prometheus",
  "agent": "observability_agent",
  "tool": "query_prometheus",
  "tool_args": {"query": "kafka_broker_info"},
  "status": "success",
  "response": {"status": "success", "result_type": "vector", "results": [...]},
  "user_id": "user",
  "session_id": "f3a68524-eefb-400d-95c1-5f89a2a97aef"
}
```

When `setup_logging()` is active (the default), audit entries go to stdout as structured JSON. An optional `log_path` argument writes a local `.jsonl` file in addition to stdout — useful for local development.

Sensitive arguments (containing `password`, `secret`, `token`, `api_key`, `credential`) are automatically redacted to `***`.

---

## Activity Tracking

### `activity_tracker()`

An `after_tool_callback` that records every tool call to `session_log` in session state. This makes all agent activity visible to `get_session_summary()` in the journal agent, regardless of which sub-agent performed the work.

```python
from ai_agents_core import activity_tracker, audit_logger

_track = activity_tracker()
_audit = audit_logger()

root_agent = create_agent(
    ...,
    after_tool_callback=[_track, _audit],  # both activity tracking + audit logging
)
```

Each entry in `session_log` follows the same format as `log_operation()`:

```json
{
  "operation": "get_cluster_info",
  "details": "[k8s_health_checker] namespace=default → success",
  "timestamp": "2026-03-17T21:33:25+00:00"
}
```

Without `activity_tracker`, `get_session_summary()` only shows operations that explicitly called `log_operation()` — missing all the tool calls from other sub-agents.

---

## Typed Configuration

### `AgentConfig`

A pydantic-settings base class for typed, validated configuration. Replaces raw `os.getenv()` calls.

```python
from ai_agents_core import AgentConfig, load_config

class KafkaConfig(AgentConfig):
    kafka_bootstrap_servers: str = "localhost:9092"

config = load_config(KafkaConfig, __file__)
print(config.kafka_bootstrap_servers)
print(config.model_provider)   # "gemini", "anthropic", "openai", etc.
print(config.model_name)       # "gemini-2.0-flash", "anthropic/claude-sonnet-4-20250514", etc.
```

Base fields (inherited by all configs):

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `model_provider` | `"gemini"` | `MODEL_PROVIDER` | LLM backend (`gemini`, `anthropic`, `openai`, `ollama`, ...) |
| `model_name` | `"gemini-2.0-flash"` | `MODEL_NAME` | Model identifier |
| `google_genai_use_vertexai` | `True` | `GOOGLE_GENAI_USE_VERTEXAI` | Use Vertex AI or AI Studio (Gemini only) |
| `google_cloud_project` | `None` | `GOOGLE_CLOUD_PROJECT` | GCP project (Vertex AI only) |
| `google_cloud_location` | `None` | `GOOGLE_CLOUD_LOCATION` | GCP region (Vertex AI only) |
| `google_api_key` | `None` | `GOOGLE_API_KEY` | AI Studio API key (Gemini only) |
| `gemini_model_version` | `None` | `GEMINI_MODEL_VERSION` | Legacy alias for `MODEL_NAME` when provider is gemini |

### `resolve_model()`

Resolves the LLM model from environment variables. Called automatically by `create_agent()` when no explicit `model` is passed.

- For `MODEL_PROVIDER=gemini` (default): returns a plain model string
- For any other provider: returns a `LiteLlm` instance via ADK's built-in LiteLLM integration

```python
from ai_agents_core.base import resolve_model

model = resolve_model()  # reads MODEL_PROVIDER + MODEL_NAME from env
```

See [Configuration reference](../docs/configuration.md) for provider-specific env vars and API key setup.

### `load_config(ConfigClass, __file__)`

Loads configuration from the `.env` file next to the calling module, with environment variable overrides.

---

## Persistent Runner

### `run_persistent()`

An async helper that runs an agent in a CLI loop with SQLite-backed sessions. Replaces the boilerplate of setting up `DatabaseSessionService`, `Runner`, and the input loop.

```python
import asyncio
from ai_agents_core import run_persistent
from my_agent.agent import root_agent

asyncio.run(run_persistent(root_agent, app_name="my_agent"))
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `agent` | — | The root agent to run |
| `app_name` | — | Application name for session scoping |
| `db_url` | `sqlite:///{app_name}.db` | SQLAlchemy database URL |
| `user_id` | `"default_user"` | User ID for session scoping |

Session state (notes, preferences, bookmarks) survives across restarts. Type `new` for a fresh session or `quit` to exit.

For the web UI, use ADK's built-in persistence flag instead:

```bash
adk web --session_service_uri=sqlite:///my_agent.db agents/my-agent
```

---

## Combining Callbacks

You can pass a list of callbacks to chain multiple behaviors:

```python
root_agent = create_agent(
    ...,
    before_tool_callback=[authorize(), require_confirmation()],
    after_tool_callback=[activity_tracker(), audit_logger()],
)
```

Callbacks are called in order. For `before_tool_callback`, the first one that returns a dict short-circuits (the tool is skipped) — so `authorize()` blocks unauthorized users before `require_confirmation()` even runs. For `after_tool_callback`, the last one that returns a dict wins.
