import os
from pathlib import Path
from dotenv import load_dotenv
from google.adk.agents import Agent

# Load environment variables from .env file in the same directory as this script
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

MODEL_NAME = os.getenv("GEMINI_MODEL_VERSION", "gemini-2.0-flash")


def get_kafka_cluster_health() -> dict:
    """Checks the health of the Kafka cluster.

    Returns:
        A dictionary with the health status and cluster information.
    """
    # This is a placeholder for actual Kafka health check logic
    # In a real scenario, you would use a Kafka client (like confluent-kafka) here.
    return {
        "status": "success",
        "health": "healthy",
        "brokers_online": 1,
        "zookeeper_online": True,
        "message": "The Kafka cluster is operating normally."
    }


def list_kafka_topics() -> dict:
    """Lists all available topics in the Kafka cluster.

    Returns:
        A dictionary with the list of topics or an error message.
    """
    # Placeholder for actual Kafka topic listing
    return {
        "status": "success",
        "topics": ["health-checks", "system-logs", "telemetry"]
    }


root_agent = Agent(
    name="kafka_health_agent",
    model=MODEL_NAME,
    description=(
        "Agent to monitor and report on the health of a Kafka cluster."
    ),
    instruction=(
        "You are a specialized agent for Kafka monitoring. You can check cluster health, "
        "list topics, and help troubleshoot Kafka-related issues using the provided tools."
    ),
    tools=[get_kafka_cluster_health, list_kafka_topics],
)
