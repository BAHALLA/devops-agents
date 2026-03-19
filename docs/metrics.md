# Prometheus Metrics

The platform exposes Prometheus metrics for every tool call across all agents. This provides real-time visibility into tool latency, error rates, agent usage, and circuit breaker state.

## Quick Start

```python
from ai_agents_core import MetricsCollector, create_agent

metrics = MetricsCollector()

root_agent = create_agent(
    name="my_agent",
    ...,
    before_tool_callback=[metrics.before_tool_callback()],
    after_tool_callback=[metrics.after_tool_callback()],
    on_tool_error_callback=metrics.on_tool_error_callback(),
)

# Expose /metrics on port 9100 (call once at startup)
metrics.start_server()
```

## Available Metrics

All metrics use the `ai_agents_` namespace prefix following [Prometheus naming conventions](https://prometheus.io/docs/practices/naming/).

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `ai_agents_tool_calls_total` | Counter | `agent`, `tool`, `status` | Total tool invocations with bounded status values |
| `ai_agents_tool_duration_seconds` | Histogram | `agent`, `tool` | Tool execution latency (buckets: 50ms to 60s) |
| `ai_agents_tool_errors_total` | Counter | `agent`, `tool`, `error_type` | Errors broken down by exception type |
| `ai_agents_circuit_breaker_state` | Gauge | `tool` | Circuit breaker state: 0=closed, 1=open, 2=half_open |
| `ai_agents_llm_tokens_total` | Counter | `agent`, `direction` | LLM token consumption (input/output) |

### Bounded Status Labels

The `status` label on `ai_agents_tool_calls_total` is restricted to a fixed set of values to prevent [cardinality explosion](https://prometheus.io/docs/practices/naming/#labels):

- `ok` — successful execution (default)
- `success` — explicit success from tool response
- `error` — tool returned an error or raised an exception
- `confirmation_required` — tool blocked by guardrail

Any other status value from a tool response is normalised to `ok`.

## How It Works

`MetricsCollector` provides three ADK callbacks following the same factory pattern as `audit_logger()`, `authorize()`, and `CircuitBreaker`:

- **`before_tool_callback()`** — generates a unique invocation ID and starts a timer
- **`after_tool_callback()`** — records duration and success/error status
- **`on_tool_error_callback()`** — records error type, duration, and increments error counters

These compose naturally with other callbacks:

```python
_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
_metrics = MetricsCollector(circuit_breaker=_breaker)

root_agent = create_agent(
    ...,
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
```

## Circuit Breaker Integration

Pass a `CircuitBreaker` instance to `MetricsCollector` to track circuit state as a Prometheus gauge:

```python
breaker = CircuitBreaker()
metrics = MetricsCollector(circuit_breaker=breaker)
```

The `ai_agents_circuit_breaker_state` gauge will reflect state changes (closed/open/half_open) for each tool on every callback invocation.

## LLM Token Tracking

Use `track_llm_tokens()` to record token consumption from custom LLM wrappers or model callbacks:

```python
from ai_agents_core import track_llm_tokens

track_llm_tokens("my_agent", input_tokens=150, output_tokens=300)
```

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `METRICS_PORT` | `9100` | TCP port for the `/metrics` HTTP server |

The port can also be passed explicitly: `metrics.start_server(port=9200)`.

`start_server()` is safe to call from multiple `MetricsCollector` instances — only the first call in the process starts the HTTP server.

## Prometheus Scraping

The `infra/prometheus.yml` includes a pre-configured scrape job. For **local development** (agent on host, Prometheus in Docker):

```yaml
- job_name: "agents"
  static_configs:
    - targets: ["host.docker.internal:9100"]
      labels:
        service: "devops-assistant"
```

For **Docker deployment** (agent and Prometheus both in containers):

```yaml
- job_name: "agents"
  static_configs:
    - targets: ["devops-assistant:9100"]
      labels:
        service: "devops-assistant"
    - targets: ["slack-bot:9100"]
      labels:
        service: "slack-bot"
```

The `docker-compose.yml` Prometheus service includes `extra_hosts: ["host.docker.internal:host-gateway"]` so the local development config works on Linux.

## Example PromQL Queries

**Tool error rate (5m window):**
```promql
rate(ai_agents_tool_errors_total[5m])
```

**p95 tool latency by agent:**
```promql
histogram_quantile(0.95, rate(ai_agents_tool_duration_seconds_bucket[5m]))
```

**Tool calls per minute by tool:**
```promql
rate(ai_agents_tool_calls_total[1m]) * 60
```

**Circuit breaker state (1 = open):**
```promql
ai_agents_circuit_breaker_state == 1
```

**LLM tokens consumed per agent (last hour):**
```promql
increase(ai_agents_llm_tokens_total[1h])
```

## Agents with Metrics Enabled

All agents ship with metrics wired in:

| Agent | Circuit Breaker Gauge | Metrics Server |
|-------|-----------------------|----------------|
| kafka-health-agent | Yes | Started at module load |
| k8s-health-agent | No | Started at module load |
| observability-agent | No | Started at module load |
| ops-journal-agent | No | Started at module load |
| devops-assistant | No | Started at module load |
| slack-bot | No | Started in FastAPI lifespan |
