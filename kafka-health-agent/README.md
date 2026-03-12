# Kafka Health Agent

A Kafka health monitoring agent built with [Google ADK](https://google.github.io/adk-docs/).

## Setup

```bash
# Install dependencies
uv sync

# Create and activate the virtual environment
uv venv
source .venv/bin/activate

# Configure your environment
# Create a kafka_health_agent/.env file with the following structure:
#
# GOOGLE_GENAI_USE_VERTEXAI=TRUE
# GOOGLE_CLOUD_PROJECT=your-project-id
# GOOGLE_CLOUD_LOCATION=your-region
# GEMINI_MODEL_VERSION=your-model-version
#
# If not using Vertex AI, you can set:
# GOOGLE_GENAI_USE_VERTEXAI=FALSE
# GOOGLE_API_KEY=your-api-key
```

## Project Structure

```
kafka-health-agent/              # Project root (defined by pyproject.toml)
├── kafka_health_agent/           # Python package (has __init__.py)
│   ├── __init__.py               # Imports agent module, makes package discoverable
│   ├── agent.py                  # Agent definition with root_agent
│   └── .env                      # API key configuration
├── pyproject.toml                # Project metadata and dependencies
└── README.md
```

ADK expects this convention:
- `<package_name>/agent.py` must define a `root_agent` variable
- `<package_name>/__init__.py` must import the agent module (`from . import agent`)
- `adk run kafka_health_agent` discovers the agent by importing the package and finding `root_agent`

## Usage

```bash
# Launch dev UI (http://localhost:8000)
uv run adk web

# Run in terminal
uv run adk run kafka_health_agent

# Start API server
uv run adk api_server
```
