# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-04-09

First public release of the AI Agents for DevOps & SRE platform.

### Added

- **Multi-agent orchestrator** — `devops-assistant` root agent delegates to 5 specialist agents via `AgentTool` and deterministic sub-agent workflows ([ADR-002](docs/adr/002-agent-tool-vs-sub-agents.md))
- **Specialist agents** — Kafka health, K8s health, Observability (Prometheus/Loki/Alertmanager), Docker, and Ops Journal
- **Slack bot** — Thread-based sessions with interactive Approve/Deny buttons for guarded operations
- **Incident triage pipeline** — `SequentialAgent` + `ParallelAgent` for parallel health checks across all systems, triage summary, and journal recording
- **Closed-loop remediation** (AEP-004) — `LoopAgent`-based pipeline: act (restart/scale/rollback) → verify → retry up to 3 iterations, with `exit_loop` tool for early termination
- **Context caching** (AEP-007) — ADK `ContextCacheConfig` for Gemini models, reducing token usage for repeated requests. Configurable via `CONTEXT_CACHE_MIN_TOKENS`, `CONTEXT_CACHE_TTL_SECONDS`, `CONTEXT_CACHE_INTERVALS` env vars
- **Cross-session memory** (AEP-003) — `SecureMemoryService` with automatic PII redaction and size limits
- **Agent evaluation framework** (AEP-002) — 22 eval scenarios across 4 agents verifying correct tool routing via ADK's `AgentEvaluator`. Run with `make eval`
- **RBAC** — 3-role hierarchy (viewer/operator/admin) enforced globally via `GuardrailsPlugin` ([ADR-001](docs/adr/001-rbac.md))
- **Safety guardrails** — `@destructive` and `@confirm` decorators gate dangerous operations with args-hash + TTL confirmation tracking (AEP-001)
- **Authentication enforcement** — `set_user_role()` marks server-trusted roles; `ensure_default_role()` forces `viewer` for unset roles
- **Input validation** — 5 reusable validators (`validate_string`, `validate_positive_int`, `validate_url`, `validate_path`, `validate_list`) applied across 30+ tool functions
- **ADK Plugins** — cross-cutting concerns as `BasePlugin` subclasses: `GuardrailsPlugin`, `ResiliencePlugin`, `MetricsPlugin`, `AuditPlugin`, `ActivityPlugin`, `ErrorHandlerPlugin`, `MemoryPlugin`
- **Prometheus metrics** — tool call counts, latency histograms, error rates, circuit breaker state, LLM tokens, and context cache events on `/metrics`
- **Resilience** — per-tool circuit breaker via `ResiliencePlugin`, `@with_retry` decorator with exponential backoff and jitter
- **Structured JSON logging** — `setup_logging()` with `JSONFormatter`, audit trail via `AuditPlugin`, activity tracking via `ActivityPlugin`
- **Multi-provider LLM** — Gemini (default), Claude, OpenAI, Ollama via `resolve_model()` + LiteLLM
- **Persistent runner** — `run_persistent()` with SQLite-backed sessions, health probes, graceful shutdown
- **Agent factory functions** — `create_agent()`, `create_sequential_agent()`, `create_parallel_agent()`, `create_loop_agent()`
- **Docker deployment** — multi-stage builds, non-root user, `docker-compose.yml` with demo/slack profiles
- **468 unit tests** — all async, all mocked, no running infrastructure required
- **CI pipeline** — lint (ruff), type check (ty), security scan (bandit), tests, evals

### Security

- Input validation at tool boundaries prevents injection attacks
- Path traversal prevention in Docker and K8s tools
- URL scheme allowlisting rejects `javascript:`, `data:`, `file:` URIs
- Docker container inspection redacts sensitive environment variables
- Guardrail confirmation bypass fixed with args-hash + TTL tracking
- Server-side role enforcement prevents privilege escalation

[Unreleased]: https://github.com/BAHALLA/devops-agents/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/BAHALLA/devops-agents/releases/tag/v0.1.0
