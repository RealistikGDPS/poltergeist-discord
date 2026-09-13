import asyncio
import signal
import sys

from relay import service
from relay import settings
from relay.adapters import discord
from relay.adapters import redis
from relay.utilities import logging

logging.configure_from_yaml()

logger = logging.get_logger(__name__)


async def _relay() -> None:
    stream = redis.default()
    client = discord.default()
    task = asyncio.current_task()
    assert task is not None, "Runs inside the event loop."
    asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, task.cancel)

    try:
        await service.run(
            stream,
            client,
            webhooks=settings.DISCORD_WEBHOOKS,
            site_url=settings.APP_PUBLIC_URL,
            server_name=settings.APP_SERVER_NAME,
        )
    except asyncio.CancelledError:
        # The signal handler cancels this task; that is the orderly stop.
        logger.info("Stopping the relay.")
    finally:
        await client.close()
        await stream.close()


match settings.APP_COMPONENT:
    case "relay":
        asyncio.run(_relay())
    case _:
        logger.error(
            "Unknown application component.",
            extra={"component": settings.APP_COMPONENT},
        )
        sys.exit(1)
