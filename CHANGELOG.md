# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased] - 2026-04-09

### Added

- **Closed-loop remediation** (AEP-004) — Self-healing using ADK `LoopAgent` that runs act → verify → retry (up to 3 iterations):
  - `create_loop_agent()` factory function in core, matching existing `create_sequential_agent`/`create_parallel_agent` pattern
  - `remediation_pipeline` exposed as `AgentTool` on the root orchestrator: actor (restart/scale/rollback) → verifier (diagnostics + `exit_loop`) → summarizer
  - `exit_loop` tool signals loop termination via `tool_context.actions.escalate = True`
  - `rollback_deployment` tool (`@destructive`) added to k8s-health agent
  - RBAC enforced on all remediation tools via existing `@destructive`/`@confirm` decorators
  - 20 new tests (468 total)

- **Context caching for LLM cost reduction** (AEP-007) — ADK `ContextCacheConfig` for Gemini models:
  - `create_context_cache_config()` factory with env-var defaults (`CONTEXT_CACHE_MIN_TOKENS`, `CONTEXT_CACHE_TTL_SECONDS`, `CONTEXT_CACHE_INTERVALS`)
  - `context_cache_config` parameter on `run_persistent()` and `App` object in devops-assistant
  - `CONTEXT_CACHE_EVENTS_TOTAL` Prometheus counter and `track_cache_event()` helper for hit/miss tracking
  - 9 new tests

## [Unreleased] - 2026-04-06

### Added

- **Agent evaluation framework** (AEP-002) — 22 eval scenarios across 4 agents verifying correct tool routing via ADK's `AgentEvaluator`:
  - `kafka-health`: 6 scenarios (cluster health, topics, consumer groups, metadata, describe groups, lag)
  - `k8s-health`: 9 scenarios (cluster info, nodes, namespaces, pods, describe, logs, deployments, status, events)
  - `docker-agent`: 6 scenarios (list containers, inspect, logs, stats, compose status, images)
  - `observability`: 6 scenarios (Prometheus query/targets, Loki logs/labels, Alertmanager alerts/silences)
  - Each agent has `tests/evals/` with `.test.json` datasets, `test_config.json` criteria, and a `test_*_eval.py` runner
  - Evals are gated behind `@pytest.mark.eval` and require LLM credentials (Vertex AI / Gemini API key)
  - Criteria: `tool_trajectory_avg_score >= 1.0` (exact tool call match); `response_match_score` intentionally excluded due to LLM non-determinism
  - Run with `make eval`; CI triggers via manual dispatch or `run-eval` PR label

## [Unreleased] - 2026-03-31

### Changed

- **ADK Plugins** — cross-cutting concerns (RBAC, guardrails, metrics, audit, activity tracking, resilience, error handling) are now packaged as ADK `BasePlugin` subclasses in `core/ai_agents_core/plugins.py` and registered once on the `Runner` via `default_plugins()`. Per-agent callback wiring has been removed from all agents.
  - `GuardrailsPlugin` — combines `authorize()`, `require_confirmation()`/`dry_run()`, and `ensure_default_role()` into a single plugin
  - `ResiliencePlugin` — wraps `CircuitBreaker` for global per-tool circuit breaking
  - `MetricsPlugin` — wraps `MetricsCollector` for global Prometheus metrics collection
  - `AuditPlugin` — wraps `audit_logger()` for global structured audit logging
  - `ActivityPlugin` — wraps `activity_tracker()` for global session activity tracking
  - `ErrorHandlerPlugin` — wraps `graceful_tool_error()` and `graceful_model_error()` for global error recovery

- **Async tools** — all tool functions across all agents converted from sync to async:
  - Kafka tools use `_run_sync()` (thread pool executor) for confluent-kafka blocking calls
  - K8s tools use `asyncio.to_thread()` for kubernetes client calls
  - Docker tools use `asyncio.create_subprocess_exec()` instead of `subprocess.run()`
  - Observability tools use `asyncio.to_thread()` for `requests` HTTP calls
  - Ops journal tools converted to `async def` (no blocking I/O)
  - `@with_retry` decorator automatically detects async functions and uses `await asyncio.sleep()`

- **Runner updated** — `run_persistent()` accepts an optional `plugins` parameter for ADK plugin registration

- **Slack bot updated** — uses `default_plugins(guardrail_mode="none")` for global cross-cutting concerns while keeping Slack-specific confirmation buttons as agent-level callbacks

- **All tests updated** — 404 tests (up from 395), all tool tests now use `@pytest.mark.asyncio` and `async def`/`await`. Docker tests mock `_run_docker` instead of `subprocess.run`

## [Unreleased] - 2026-03-24

### Added

- **Input validation library** (`core/ai_agents_core/validation.py`) — reusable validators for all agent tools:
  - `validate_string()` — length bounds + optional regex pattern matching
  - `validate_positive_int()` — integer range checking with type enforcement
  - `validate_url()` — scheme allowlisting, rejects `javascript:`, `data:`, `file:` URIs
  - `validate_path()` — rejects `..` path traversal components
  - `validate_list()` — list length bounds with type enforcement
  - Pre-compiled patterns: `K8S_NAME_PATTERN`, `KAFKA_TOPIC_PATTERN`
  - Safety constants: `MAX_LOG_LINES`, `MAX_REPLICAS`, `MAX_PARTITIONS`, `MAX_REPLICATION_FACTOR`, `MAX_QUERY_LENGTH`

- **Input validation across all agents** — every tool function now validates its inputs at entry and returns structured error dicts on invalid input:
  - **kafka-health**: topic name pattern, partition/replication factor ranges, consumer group list bounds
  - **k8s-health**: namespace/pod name K8s naming rules (with `"all"` special case), replica count 0-1000, log tail cap
  - **observability**: query length caps, log line limits, silence duration range, matcher list bounds
  - **devops-assistant (Docker)**: container name validation, log tail cap, path traversal prevention
  - **ops-journal**: title/content/tag length caps, URL scheme validation

- **Authentication enforcement** (`set_user_role()`, `ensure_default_role()` in `core/ai_agents_core/rbac.py`):
  - `set_user_role(state, role)` — sets role and marks it as server-trusted via a lock flag
  - `ensure_default_role()` — `before_agent_callback` that forces `viewer` if the role wasn't set by the server, preventing privilege escalation from untrusted session state

- **Docker secret redaction** — `inspect_container()` now redacts environment variables containing sensitive keywords (`password`, `secret`, `token`, `api_key`, `credential`, `key`, `auth`)

- **106 new tests** (289 -> 395 total) covering input validation, guardrail bypass prevention, RBAC enforcement, and Docker secret redaction

### Fixed

- **Guardrails confirmation bypass** — the `require_confirmation()` callback previously stored a simple boolean flag, allowing bypass via different arguments or stale state. Now stores an args hash + timestamp:
  - Different arguments on retry trigger a new confirmation prompt
  - Confirmations expire after 5 minutes (TTL)
  - State is consumed after use (one-time confirmation)
  - Legacy boolean pending state is treated as invalid

### Security

- Closed input injection vectors across 30+ tool functions by adding validation at the tool boundary
- Prevented path traversal attacks in Docker Compose status and K8s tools
- Prevented URL scheme injection (`javascript:`, `data:`, `file:`) in team bookmark URLs
- Prevented secret leakage through Docker container inspection
- Prevented privilege escalation by enforcing server-side role assignment with `set_user_role()`
- Fixed confirmation bypass that allowed destructive operations without re-confirmation when arguments changed
