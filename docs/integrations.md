# Platform Integrations

The AI Agents platform is designed to be interface-agnostic. A single agent runner can be exposed through multiple frontends, each inheriting the same RBAC, guardrails, and observability plugins.

## Current Integrations

### 1. ADK Web UI (Developer Portal)
The primary interface for local development and agent debugging.
- **Features**: Real-time trace visualization, session state inspection, and artifact downloads.
- **Best For**: SREs and developers building or testing new agent capabilities.
- **Run Command**: `make run-devops`

### 2. Slack Bot (Collaborative Operations)
A production-ready bot that brings autonomous DevOps to your Slack channels.
- **Features**: Thread-based session isolation, interactive Approve/Deny buttons for guarded tools, and role-based access control based on Slack user IDs.
- **Interactive Guards**: When an agent hits a `@confirm` or `@destructive` tool, it posts a Slack Card with buttons, pausing execution until a human interacts.
- **Setup Guide**: [Slack Setup Reference](slack-setup.md)

### 3. CLI Runner
A headless interface for terminal-based interactions and CI/CD automation.
- **Features**: Persistent session support and structured JSON logging.
- **Best For**: Scripted diagnostics and automated remediation triggers.

---

## Upcoming Integrations (Roadmap)

### 1. Google Chat Bot (In Progress)
Bringing the same collaborative power of the Slack bot to Google Workspace.
- **Target Pattern**: Interactive Cards for human-in-the-loop approvals.
- **Identity**: Mapping Google Workspace emails to RBAC roles.
- **Deployment**: Optimized for Google Cloud Run with VPC-native connectivity.

### 2. Microsoft Teams Bot
Expanding support for enterprise collaboration environments.
- **Target Pattern**: Adaptive Cards for tool confirmation and incident reporting.

### 3. Custom API Gateway
A REST/SSE interface for embedding agents into internal developer portals (IDP).
- **Target Pattern**: Standardized `/run_sse` endpoints for real-time streaming to custom web frontends.

---

## Architecture of an Integration

Every integration follows the **Host Pattern**:

1.  **Event Capture**: The integration layer listens for user input (HTTP POST, Socket Mode, Pub/Sub).
2.  **Identity Resolution**: It resolves the user's platform-specific ID (e.g., Slack ID, Email) and maps it to a `viewer`, `operator`, or `admin` role.
3.  **Runner Execution**: It calls `Runner.run_async()`, passing the user message and session ID.
4.  **Callback Handling**:
    *   **Content Events**: Displayed as chat messages.
    *   **Confirmation Events**: Displayed as interactive buttons/cards.
    *   **Artifact Events**: Displayed as file attachments or download links.
