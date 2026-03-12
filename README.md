# AI Agents

This repository contains a collection of autonomous agents built with [Google ADK](https://google.github.io/adk-docs/).

## Repository Structure

```text
ai-agents/
├── kafka-health-agent/      # Agent for monitoring Kafka health
└── ...                      # Future agents
```

## General Setup

### Prerequisites

- [uv](https://docs.astral.sh/uv/) for Python package management.
- A Google Cloud Project with the Vertex AI API enabled (or an AI Studio API key).

### Global Environment Configuration

Most agents in this repository follow the Google ADK conventions. You will generally need a `.env` file in the agent's package directory (e.g., `kafka-health-agent/kafka_health_agent/.env`) with the following variables:

```bash
# Using Vertex AI (Recommended)
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=your-region
GEMINI_MODEL_VERSION=gemini-1.5-pro # or gemini-2.0-flash

# OR using Google AI Studio
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=your-api-key
```

### Installation

To set up any agent, navigate to its directory and run:

```bash
# Install dependencies and create venv
uv sync
```

## ADK Conventions

Agents in this repository are structured to be compatible with `adk` discovery:

1.  **Package Structure**: Each agent is a Python package (e.g., `kafka_health_agent/`).
2.  **Entry Point**: The `agent.py` file within the package must define a `root_agent` variable.
3.  **Discovery**: The `__init__.py` file must import the `agent` module.

## Usage (Common Commands)

From within an agent's directory:

```bash
# Launch the ADK Dev UI
uv run adk web

# Run the agent in the terminal
uv run adk run <package_name>

# Start the API server
uv run adk api_server
```
