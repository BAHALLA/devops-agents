# Cross-Session Memory

By default, each agent session is isolated — when a new session starts, prior context is lost. The **Memory Service** enables agents to recall information from past sessions, making them smarter over time.

This is especially valuable for DevOps/SRE use cases:

- Correlate a current incident with a similar one from last week
- Recall what steps resolved a previous Kafka consumer lag spike
- Detect recurring patterns ("this pod crashes every Monday morning")

## How It Works

```mermaid
sequenceDiagram
    participant User
    participant Agent
    participant PreloadMemoryTool
    participant MemoryPlugin
    participant SecureMemoryService

    User->>Agent: "Why is Kafka lagging again?"
    Agent->>PreloadMemoryTool: Auto-load relevant past context
    PreloadMemoryTool->>SecureMemoryService: search_memory(query)
    SecureMemoryService-->>PreloadMemoryTool: Past incidents about Kafka lag
    PreloadMemoryTool-->>Agent: Inject context into LLM prompt
    Agent-->>User: "This looks similar to the lag spike on March 15..."
    Note over MemoryPlugin: After session completes
    MemoryPlugin->>SecureMemoryService: add_session_to_memory(session)
    Note over SecureMemoryService: Redact secrets, enforce limits, store
```

The memory system has three components:

| Component | Role |
|-----------|------|
| **`SecureMemoryService`** | Wraps ADK's `InMemoryMemoryService` with security hardening |
| **`MemoryPlugin`** | Auto-saves sessions to memory after the root agent completes |
| **`PreloadMemoryTool`** | ADK tool that auto-loads relevant memories at the start of each turn |

## Security Hardening

The `SecureMemoryService` wraps ADK's built-in `InMemoryMemoryService` and adds two layers of protection:

### Sensitive Data Redaction

All event content is redacted **at write time** — secrets never enter the memory store. The following patterns are automatically detected and replaced with `[REDACTED]`:

- `password=...`, `token=...`, `secret=...`, `api_key=...`, `bearer=...`
- PEM private key blocks (`-----BEGIN RSA PRIVATE KEY-----`)
- Any key-value pair where the key matches common secret names

You can also supply custom patterns:

```python
import re
from orrery_core import SecureMemoryService

memory = SecureMemoryService(
    sensitive_patterns=[
        re.compile(r"(?i)my_custom_secret\s*[:=]\s*\S+"),
    ]
)
```

### Bounded Storage

Memory is capped at **500 events per user** by default (configurable via `max_entries_per_user`). When the limit is reached, the oldest events are evicted (FIFO). This prevents unbounded memory growth in long-running deployments.

```python
memory = SecureMemoryService(max_entries_per_user=1000)
```

### User Isolation

Memory is scoped by `app_name` and `user_id` — inherited from ADK's design. User A cannot search User B's memory, and the `devops_assistant` app cannot see memories from the `ops_journal` app.

## Setup

### Enable Memory in Persistent Mode

```python
import asyncio
from orrery_core import SecureMemoryService, default_plugins, run_persistent
from my_agent.agent import root_agent

asyncio.run(
    run_persistent(
        root_agent,
        app_name="my_agent",
        memory_service=SecureMemoryService(),
        plugins=default_plugins(enable_memory=True),
    )
)
```

This does two things:

1. **`memory_service=SecureMemoryService()`** — enables the Runner to store and search memories
2. **`enable_memory=True`** — activates the `MemoryPlugin`, which auto-saves sessions after each root agent interaction (skips trivial sessions with fewer than 4 events)

### Add Memory Tools to Your Agent

For the agent to actively use memory, add `PreloadMemoryTool` to its tools:

```python
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from orrery_core import create_agent

root_agent = create_agent(
    name="my_agent",
    description="...",
    instruction="You have access to cross-session memory. Relevant context "
        "from past sessions is automatically loaded.",
    tools=[..., PreloadMemoryTool()],
)
```

`PreloadMemoryTool` automatically searches memory at the start of each turn and injects relevant past context into the LLM prompt — no explicit tool call needed from the user.

## Configuration

### MemoryPlugin Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `enable_memory` | `False` | Enable auto-save of sessions to memory |
| `memory_min_events` | `4` | Minimum events before a session is saved (filters out trivial interactions) |

### SecureMemoryService Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_entries_per_user` | `500` | Maximum events stored per user; oldest evicted when exceeded |
| `sensitive_patterns` | Built-in set | List of `re.Pattern` objects for custom redaction rules |

## Plugin Order

The `MemoryPlugin` is registered as part of `default_plugins()` when enabled. It runs after `ActivityPlugin` and before `ErrorHandlerPlugin`:

```
1. GuardrailsPlugin   — RBAC + confirmation
2. ResiliencePlugin    — circuit breaker
3. MetricsPlugin       — Prometheus metrics
4. AuditPlugin         — structured audit logs
5. ActivityPlugin      — session activity tracking
6. MemoryPlugin        — cross-session memory persistence
7. ErrorHandlerPlugin  — graceful error recovery
```

## Production Considerations

The current `InMemoryMemoryService` uses keyword-based search and is suitable for development and testing. For production:

- **Semantic search** — keyword matching may miss relevant memories. Consider implementing a custom `BaseMemoryService` backed by PostgreSQL + pgvector or switching to `VertexAiMemoryBankService` for LLM-powered semantic search.
- **Persistence** — in-memory storage is lost on restart. A database-backed implementation is recommended for production.
- **Memory growth** — the `max_entries_per_user` limit helps, but monitor memory usage in long-running deployments.

The `SecureMemoryService` uses a delegation pattern, so swapping the inner service requires only a constructor change — no agent modifications needed.
