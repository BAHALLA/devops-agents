# devops-assistant

A multi-agent orchestrator that delegates to specialized sub-agents. It has no tools of its own — it routes user requests to the right specialist.

## Agent Graph

```text
devops_assistant (orchestrator)
├── kafka_health_agent   — Kafka cluster operations
└── docker_agent         — Docker container operations
```

![DevOps Assistant — agent graph and container inspection](assets/devops-assistant-graph.png)

*The ADK Dev UI showing the agent graph: `devops_assistant` delegates to `kafka_health_agent` and `docker_agent`, each with their own tools. Here the docker agent inspects the Kafka container's configuration.*

## Sub-agents

### kafka_health_agent

Reused from the standalone [kafka-health-agent](kafka-health-agent.md). Handles all Kafka cluster operations.

### docker_agent

| Tool | Description |
|------|-------------|
| `list_containers` | List running (or all) Docker containers |
| `inspect_container` | Get detailed info: state, ports, env vars, health |
| `get_container_logs` | Tail recent logs with optional `--since` filter |
| `get_container_stats` | CPU, memory, network, and block I/O stats |
| `docker_compose_status` | Status of services in a Compose project |

## How Delegation Works

The root `devops_assistant` agent has no tools. When a user sends a message, the LLM reads the sub-agent descriptions and decides which specialist to hand off to:

- *"what's the consumer lag?"* → `kafka_health_agent`
- *"show me kafka container logs"* → `docker_agent`
- *"is everything healthy?"* → delegates to both, then synthesizes

## Running

```bash
cd agents/devops-assistant
uv run adk web                    # ADK Dev UI
uv run adk run devops_assistant   # Terminal mode
```

Or from the repo root:

```bash
make run-devops          # ADK Dev UI
make run-devops-cli      # Terminal mode
```
