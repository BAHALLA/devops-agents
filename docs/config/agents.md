# Agent Configuration

Each agent defines its own configuration class that inherits from `AgentConfig`. Values are loaded from `.env` files located within the agent's package directory.

## Agent-Specific Settings

| Agent | Variable | Default | Description |
|-------|----------|---------|-------------|
| **kafka-health** | `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka broker address(es) |
| **k8s-health** | `KUBECONFIG_PATH` | — | Path to kubeconfig file |
| **observability** | `PROMETHEUS_URL` | `http://localhost:9090` | Prometheus server URL |
| **observability** | `LOKI_URL` | `http://localhost:3100` | Loki server URL |
| **observability** | `ALERTMANAGER_URL` | `http://localhost:9093` | Alertmanager server URL |
| **slack-bot** | `SLACK_BOT_TOKEN` | — | Slack bot token (`xoxb-...`) |
| **slack-bot** | `SLACK_APP_TOKEN` | — | App-level token for Socket Mode (`xapp-...`) |
| **slack-bot** | `SLACK_SIGNING_SECRET` | — | Request signing secret |
| **slack-bot** | `SLACK_ADMIN_USERS` | — | Comma-separated Slack user IDs with `admin` role |
| **slack-bot** | `SLACK_OPERATOR_USERS` | — | Comma-separated Slack user IDs with `operator` role |

## Local `.env` Files

Each agent ships with a `.env.example` template. To configure an agent:

1. Navigate to the agent's directory (e.g., `agents/kafka-health/kafka_health_agent/`).
2. Copy `.env.example` to `.env`.
3. Fill in the required values.

The `load_agent_env(__file__)` helper automatically loads these values when the agent starts.
