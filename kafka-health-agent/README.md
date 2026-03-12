# Kafka Health Agent

A Kafka health monitoring agent built with [Google ADK](https://google.github.io/adk-docs/). This agent is designed to monitor Kafka cluster health and provide insights into its state.

## Overview

The Kafka Health Agent uses the Google ADK framework to interact with LLMs and analyze Kafka-related metrics and logs.

## Setup

For general setup and prerequisites (e.g., `uv`, Google Cloud configuration), please refer to the [Root README](../README.md).

### Agent-Specific Configuration

Create a `.env` file in `kafka_health_agent/` (e.g., `kafka-health-agent/kafka_health_agent/.env`) with the following variables:

```bash
# General AI configuration (refer to Root README)
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=your-region
GEMINI_MODEL_VERSION=your-model-version

# Kafka-specific configuration (if any)
# KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

## Project Structure

```text
kafka-health-agent/              # Project root (defined by pyproject.toml)
├── kafka_health_agent/           # Python package (has __init__.py)
│   ├── __init__.py               # Imports agent module, makes package discoverable
│   ├── agent.py                  # Agent definition with root_agent
│   └── .env                      # Agent-specific configuration
├── pyproject.toml                # Project metadata and dependencies
└── README.md
```

## Usage

From the `kafka-health-agent/` directory:

```bash
# Launch dev UI (http://localhost:8000)
uv run adk web

# Run in terminal
uv run adk run kafka_health_agent

# Start API server
uv run adk api_server
```
