"""Allow running as `python -m slack_bot` for Socket Mode."""

import asyncio

from .socket_mode import main

asyncio.run(main())
