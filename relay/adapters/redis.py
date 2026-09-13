from collections.abc import AsyncGenerator

from redis.asyncio import Redis

from relay.utilities import logging

logger = logging.get_logger(__name__)

_PATTERN = "poltergeist:*"
_POLL_SECONDS = 1.0
# A ping on the otherwise idle subscription, so a dead connection is noticed.
_HEALTH_CHECK_SECONDS = 30


class EventStream:
    """A pattern subscription yielding each message's payload. The generator
    ends with the driver's exception when the connection is lost; the caller
    decides whether to resume."""

    __slots__ = ("_redis",)

    def __init__(self, *, host: str, port: int, database: int) -> None:
        self._redis = Redis(
            host=host,
            port=port,
            db=database,
            decode_responses=True,
            health_check_interval=_HEALTH_CHECK_SECONDS,
        )

    async def messages(self) -> AsyncGenerator[str]:
        async with self._redis.pubsub() as pubsub:
            await pubsub.psubscribe(_PATTERN)
            logger.info(
                "Subscribed to the event channels.", extra={"pattern": _PATTERN}
            )

            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=_POLL_SECONDS
                )

                if message is None:
                    continue

                yield str(message["data"])

    async def close(self) -> None:
        await self._redis.aclose()


def default() -> EventStream:
    # Local import keeps this module importable without configuration.
    from relay import settings

    return EventStream(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        database=settings.REDIS_DATABASE,
    )
