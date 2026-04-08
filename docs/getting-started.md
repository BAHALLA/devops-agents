# Getting Started

Welcome to the AI Agents platform for DevOps and SRE. After following the **Quick Start** on the home page, this guide will walk you through your first interaction with the agents.

## Your First Interaction

1.  **Start the Platform**: If you haven't already, run the infrastructure and the `devops-assistant`:
    ```bash
    make infra-up
    make run-devops
    ```
2.  **Open the Web UI**: Visit `http://localhost:8000` in your browser.
3.  **Ask a Question**: Type a request like:
    *"Is my Kafka cluster healthy?"*
4.  **Observe the Triage**: The agent will likely trigger the `incident_triage_agent`, which performs parallel health checks across all systems (Kafka, K8s, Docker, and Observability).
5.  **Review the Report**: After the parallel checks finish, a synthesis agent will provide a concise triage report.

---

## Exploring Key Concepts

### 1. Collaborative Triage
When you ask for a system check, the **Coordinator Agent** delegates to specialist sub-agents. These sub-agents run in **Parallel**, significantly reducing the time needed to gather a complete system state.

### 2. Human-in-the-Loop
Try a mutating action like:
*"Create a Kafka topic named 'test-topic' with 3 partitions."*

The agent will identify this as a **guarded operation** and pause. You will see a confirmation prompt asking for approval. This ensures no irreversible actions are taken without human oversight.

### 3. Specialist Delegation
If you have a targeted query, such as *"How many pods are running in the 'kube-system' namespace?"*, the orchestrator will route your request directly to the `k8s_health_agent` using the **AgentTool** pattern.

---

## Next Steps

- **[Set up Slack](integrations/slack.md)** to interact with your agents where your team already collaborates.
- **[Configure Providers](config/general.md)** to switch from Gemini to Claude, OpenAI, or a local model.
- **[Enable Cross-Session Memory](memory.md)** so agents recall past incidents and investigations.
- **[Examine Metrics](metrics.md)** to see how your agents perform in real-time via Prometheus.
