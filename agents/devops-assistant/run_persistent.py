"""Run devops-assistant with SQLite-backed persistent sessions and memory.

Usage:
    uv run python run_persistent.py
"""

import asyncio

from ai_agents_core import SecureMemoryService, default_plugins, run_persistent
from ai_agents_core.runner import create_context_cache_config
from devops_assistant.agent import root_agent

if __name__ == "__main__":
    asyncio.run(
        run_persistent(
            root_agent,
            app_name="devops_assistant",
            memory_service=SecureMemoryService(),
            plugins=default_plugins(enable_memory=True),
            context_cache_config=create_context_cache_config(),
        )
    )
