from orrery_core import create_agent, load_agent_env

from .tools import (
    docker_compose_status,
    get_container_logs,
    get_container_stats,
    inspect_container,
    list_containers,
    list_images,
    remove_image,
    restart_container,
    start_container,
    stop_container,
)

load_agent_env(__file__)

root_agent = create_agent(
    name="docker_agent",
    description=(
        "Specialist for Docker container and image operations. Use this agent for "
        "anything related to containers and images: listing, inspecting, logs, stats, "
        "lifecycle management (start/stop/restart), and compose status."
    ),
    instruction=(
        "You are a Docker operations specialist. Use your tools to inspect containers, "
        "read logs, check resource usage, manage container lifecycle, list images, and "
        "report on Docker Compose services.\n\n"
        "When diagnosing issues, start by listing containers to see what's running, "
        "then drill into specific containers as needed.\n\n"
        "For lifecycle operations (stop, start, restart), always confirm the target "
        "container name with the user before proceeding."
    ),
    tools=[
        list_containers,
        inspect_container,
        get_container_logs,
        get_container_stats,
        docker_compose_status,
        stop_container,
        start_container,
        restart_container,
        list_images,
        remove_image,
    ],
)
