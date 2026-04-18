# Google Chat Bot

Google Chat bot that connects the DevOps agent platform to Google Workspace. Messages in threads are routed to the ADK Runner, and responses are posted back in-thread. Guarded tools (`@destructive`, `@confirm`) post interactive **Card v2** Approve/Deny cards.

Two transports are supported: **HTTP webhook** (public URL) and **Pub/Sub pull** (private network). The agent logic is identical — only the event plumbing changes.

---

### 🚀 [Full documentation at bahalla.github.io/orrery](https://bahalla.github.io/orrery/integrations/google-chat/)

---

## Architecture

```
Google Chat event
  → HTTP webhook (FastAPI) OR Pub/Sub subscription (pull)
    → GoogleChatHandler
      → ADK Runner (orrery-assistant root_agent)
        → AgentTools (kafka, k8s, docker, observability, journal)
        → sub-agents (incident triage workflow)
      → reply posted in-thread (sync or async via Chat REST API)

Guarded tools → Card v2 [Approve] [Deny]
```

**One Chat thread = one ADK session.** New thread = fresh conversation.

## Setup

For the full setup guide — GCP infrastructure, App Authentication, Connection settings — see the [Integration Guide](https://bahalla.github.io/orrery/integrations/google-chat/).

Quick pointers:

- **HTTP transport** — see [HTTP Webhook Setup](https://bahalla.github.io/orrery/integrations/google-chat-webhook/)
- **Pub/Sub transport** — see [Pub/Sub Setup](https://bahalla.github.io/orrery/integrations/google-chat-pubsub/) (recommended for private GKE)

## Running

### HTTP transport (via ngrok for local dev)

```bash
# 1. Start the bot on :3001
make run-google-chat

# 2. Expose with ngrok and paste the HTTPS URL into the Chat API console
ngrok http 3001
```

### Pub/Sub transport

```bash
GOOGLE_CHAT_PUBSUB_SUBSCRIPTION=orrery-chat-events-sub \
GOOGLE_CHAT_PUBSUB_PROJECT=your-project-id \
make run-google-chat-pubsub
```

In-cluster deployment uses the Helm chart's `pubsubWorker.enabled: true`.

## How It Works

### Async Response Mode

Google Chat enforces a ~30 s synchronous budget. The bot returns `200 OK` immediately with a "Working..." card, continues the agent run in the background, and posts the final reply via the Chat REST API. Enabled by default (`GOOGLE_CHAT_ASYNC_RESPONSE=true`).

### Confirmation Cards

When the agent invokes a tool marked `@confirm` or `@destructive`, a Card v2 is posted to the thread:

1. **Approve** → agent re-invokes the tool (now allowed through)
2. **Deny** → agent skips the operation

Destructive tools show a warning banner; confirm tools show an info banner.

### Session Management

| Concept | Mapping |
|---------|---------|
| Chat thread | ADK session |
| User email | ADK user ID + RBAC lookup |
| New thread | New session |
| Reply in thread | Continues session |

Sessions are persisted in the shared Postgres store (same as Slack).

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_CHAT_AUDIENCE` | — | JWT audience — must match the public URL byte-for-byte (HTTP mode only) |
| `GOOGLE_CHAT_ASYNC_RESPONSE` | `true` | Enable async Chat REST API replies |
| `GOOGLE_CHAT_SERVICE_ACCOUNT_FILE` | — | SA key for async replies (required locally, uses ADC on GKE) |
| `GOOGLE_CHAT_ADMIN_EMAILS` | — | Comma-separated admin emails |
| `GOOGLE_CHAT_OPERATOR_EMAILS` | — | Comma-separated operator emails |
| `GOOGLE_CHAT_IDENTITIES` | `chat@system.gserviceaccount.com` | Allowed token issuers (add the Workspace Add-ons SA when applicable) |
| `GOOGLE_CHAT_PUBSUB_SUBSCRIPTION` | — | Subscription ID (Pub/Sub mode only) |
| `GOOGLE_CHAT_PUBSUB_PROJECT` | — | Project hosting the subscription (Pub/Sub mode) |
| `GOOGLE_CHAT_PUBSUB_MAX_MESSAGES` | `4` | Max concurrent callbacks (Pub/Sub mode) |
| `GOOGLE_CHAT_PUBSUB_HANDLER_TIMEOUT_SECONDS` | `600` | Per-turn timeout before nack |
| `GOOGLE_CHAT_PUBSUB_HEALTH_PORT` | `8080` | Health endpoints for the Pub/Sub worker |

## Testing

```bash
uv run pytest agents/google-chat-bot/tests/ -v
```

All tests are mocked — no Google Chat / Pub/Sub / GCP credentials required.
