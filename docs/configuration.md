# Configuration

Each agent defines its own config class that inherits from `AgentConfig`. Values are loaded from `.env` files and environment variables.

## LLM Provider

The platform supports multiple LLM providers through [LiteLLM](https://docs.litellm.ai/). Switch providers by setting two environment variables — no code changes needed.

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_PROVIDER` | `gemini` | LLM backend: `gemini`, `anthropic`, `openai`, `ollama`, etc. |
| `MODEL_NAME` | `gemini-2.0-flash` | Model identifier (provider prefix auto-added if missing) |

### Provider examples

**Google Gemini** (default — works out of the box):

```env
MODEL_PROVIDER=gemini
MODEL_NAME=gemini-2.5-pro
# Either Vertex AI:
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=my-project
GOOGLE_CLOUD_LOCATION=us-central1
# Or AI Studio:
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=AIza...
```

**Anthropic Claude**:

```env
MODEL_PROVIDER=anthropic
MODEL_NAME=anthropic/claude-sonnet-4-20250514
ANTHROPIC_API_KEY=sk-ant-api03-...
```

**OpenAI**:

```env
MODEL_PROVIDER=openai
MODEL_NAME=openai/gpt-4o
OPENAI_API_KEY=sk-...
```

**Ollama (local)**:

```env
MODEL_PROVIDER=ollama
MODEL_NAME=ollama/llama3
OLLAMA_API_BASE=http://localhost:11434
```

### Getting API keys

| Provider | How to get a key | Env var |
|----------|-----------------|---------|
| **Google AI Studio** | Go to [aistudio.google.com/apikey](https://aistudio.google.com/apikey), sign in, click "Create API Key" | `GOOGLE_API_KEY` |
| **Google Vertex AI** | Create a GCP project, enable the Vertex AI API, then set project/location. Uses Application Default Credentials (`gcloud auth application-default login`) | `GOOGLE_CLOUD_PROJECT` + `GOOGLE_CLOUD_LOCATION` |
| **Anthropic** | Go to [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys), sign in, click "Create Key" | `ANTHROPIC_API_KEY` |
| **OpenAI** | Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys), sign in, click "Create new secret key" | `OPENAI_API_KEY` |
| **Ollama** | Install [Ollama](https://ollama.com/), run `ollama pull llama3`, no API key needed | `OLLAMA_API_BASE` (defaults to `http://localhost:11434`) |

### Backward compatibility

The legacy `GEMINI_MODEL_VERSION` env var still works when `MODEL_PROVIDER=gemini` (the default). If both `MODEL_NAME` and `GEMINI_MODEL_VERSION` are set, `MODEL_NAME` takes precedence.

## Google AI / Vertex AI settings

These apply when `MODEL_PROVIDER=gemini`:

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_GENAI_USE_VERTEXAI` | `TRUE` | Use Vertex AI (`TRUE`) or AI Studio (`FALSE`) |
| `GOOGLE_CLOUD_PROJECT` | — | GCP project ID (required for Vertex AI) |
| `GOOGLE_CLOUD_LOCATION` | — | GCP region, e.g. `us-central1` (required for Vertex AI) |
| `GOOGLE_API_KEY` | — | API key (required for AI Studio) |
| `GEMINI_MODEL_VERSION` | — | Legacy alias for `MODEL_NAME` |

## Agent-specific settings

| Agent | Variable | Default | Description |
|-------|----------|---------|-------------|
| kafka-health | `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka broker address(es) |
| k8s-health | `KUBECONFIG_PATH` | — | Path to kubeconfig file |
| observability | `PROMETHEUS_URL` | `http://localhost:9090` | Prometheus server URL |
| observability | `LOKI_URL` | `http://localhost:3100` | Loki server URL |
| observability | `ALERTMANAGER_URL` | `http://localhost:9093` | Alertmanager server URL |
| slack-bot | `SLACK_BOT_TOKEN` | — | Slack bot token (`xoxb-...`) |
| slack-bot | `SLACK_APP_TOKEN` | — | App-level token for Socket Mode (`xapp-...`) |
| slack-bot | `SLACK_SIGNING_SECRET` | — | Request signing secret |
| slack-bot | `SLACK_ADMIN_USERS` | — | Comma-separated Slack user IDs with `admin` role |
| slack-bot | `SLACK_OPERATOR_USERS` | — | Comma-separated Slack user IDs with `operator` role |

## Infrastructure

The included `docker-compose.yml` starts the local infrastructure:

| Service | Port | Description |
|---------|------|-------------|
| Kafka | `9092` | Kafka broker |
| Zookeeper | `2181` | Zookeeper for Kafka |
| Kafka UI | `8080` | Web UI for browsing topics and consumer groups |
| Kafka Exporter | `9308` | Prometheus exporter for Kafka metrics |
| Prometheus | `9090` | Metrics collection and alerting rules |
| Loki | `3100` | Log aggregation |
| Alertmanager | `9093` | Alert routing and silence management |

```bash
make infra-up     # start all services
make infra-down   # stop all services
make infra-reset  # stop and wipe volumes
```

## Docker Compose profiles

| Command | What it starts |
|---------|---------------|
| `docker compose up -d` | Infrastructure only |
| `docker compose --profile demo up -d` | Infrastructure + devops-assistant web UI on `:8000` |
| `docker compose --profile slack up -d` | Infrastructure + Slack bot on `:3000` |
