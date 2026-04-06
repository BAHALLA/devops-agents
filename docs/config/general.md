# General Configuration

The platform's core behavior, including LLM providers and infrastructure services, is controlled via environment variables.

## LLM Provider

The platform supports multiple LLM providers through [LiteLLM](https://docs.litellm.ai/). Switch providers by setting two environment variables — no code changes needed.

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_PROVIDER` | `gemini` | LLM backend: `gemini`, `anthropic`, `openai`, `ollama`, etc. |
| `MODEL_NAME` | `gemini-2.0-flash` | Model identifier (provider prefix auto-added if missing) |

### Provider examples

<details>
<summary>Google Gemini (Default)</summary>

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
</details>

<details>
<summary>Anthropic Claude</summary>

```env
MODEL_PROVIDER=anthropic
MODEL_NAME=anthropic/claude-sonnet-4-20250514
ANTHROPIC_API_KEY=sk-ant-api03-...
```
</details>

<details>
<summary>OpenAI</summary>

```env
MODEL_PROVIDER=openai
MODEL_NAME=openai/gpt-4o
OPENAI_API_KEY=sk-...
```
</details>

<details>
<summary>Ollama (Local)</summary>

```env
MODEL_PROVIDER=ollama
MODEL_NAME=ollama/llama3
OLLAMA_API_BASE=http://localhost:11434
```
</details>

### Getting API keys

| Provider | How to get a key | Env var |
|----------|-----------------|---------|
| **Google AI Studio** | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | `GOOGLE_API_KEY` |
| **Google Vertex AI** | GCP Project + `gcloud auth application-default login` | `GOOGLE_CLOUD_PROJECT` |
| **Anthropic** | [console.anthropic.com](https://console.anthropic.com/settings/keys) | `ANTHROPIC_API_KEY` |
| **OpenAI** | [platform.openai.com](https://platform.openai.com/api-keys) | `OPENAI_API_KEY` |
| **Ollama** | Install [Ollama](https://ollama.com/), run `ollama pull llama3` | N/A |

---

## Infrastructure

The included `docker-compose.yml` starts the local diagnostic stack.

| Service | Port | Description |
|---------|------|-------------|
| Kafka | `9092` | Kafka broker |
| Zookeeper | `2181` | Zookeeper for Kafka |
| Kafka UI | `8080` | Web UI for browsing topics and consumer groups |
| Kafka Exporter | `9308` | Prometheus exporter for Kafka metrics |
| Prometheus | `9090` | Metrics collection and alerting rules |
| Loki | `3100` | Log aggregation |
| Alertmanager | `9093` | Alert routing and silence management |

### Management Commands

```bash
make infra-up     # start all services
make infra-down   # stop all services
make infra-reset  # stop and wipe volumes
```

### Docker Compose profiles

| Command | What it starts |
|---------|---------------|
| `docker compose up -d` | Infrastructure only |
| `docker compose --profile demo up -d` | Infrastructure + devops-assistant web UI on `:8000` |
| `docker compose --profile slack up -d` | Infrastructure + Slack bot on `:3000` |
