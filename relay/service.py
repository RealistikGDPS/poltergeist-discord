import asyncio
from collections.abc import Mapping
from collections.abc import Sequence

from relay import embeds
from relay import events
from relay.adapters.discord import DiscordClient
from relay.adapters.redis import EventStream
from relay.utilities import logging

logger = logging.get_logger(__name__)

_RECONNECT_SECONDS = 5.0
_TEXT_LOG_LIMIT = 200


async def _relay(
    text: str,
    discord: DiscordClient,
    *,
    webhooks: Mapping[str, Sequence[str]],
    site_url: str,
    server_name: str,
) -> None:
    received = events.parse(text)

    if received is events.ParseError.UNKNOWN_EVENT:
        logger.debug("Ignored an event of an unknown kind.")

        return

    if isinstance(received, events.ParseError):
        logger.warning(
            "Dropped a malformed event.", extra={"text": text[:_TEXT_LOG_LIMIT]}
        )

        return

    kind = received.event.kind
    urls = webhooks.get(kind, ())

    if not urls:
        return

    payload = embeds.message(received, site_url=site_url, server_name=server_name)

    if payload is None:
        return

    delivered = 0

    for url in urls:
        error = await discord.post(url, payload)

        if error is None:
            delivered += 1
        else:
            logger.warning(
                "A webhook was not delivered.",
                extra={"event": kind, "error": error.value},
            )

    logger.info(
        "Relayed an event.",
        extra={"event": kind, "delivered": delivered, "webhooks": len(urls)},
    )


async def run(
    stream: EventStream,
    discord: DiscordClient,
    *,
    webhooks: Mapping[str, Sequence[str]],
    site_url: str,
    server_name: str,
) -> None:
    """Relays until cancelled, resubscribing whenever the stream drops."""

    routed = sorted(kind for kind, urls in webhooks.items() if urls)

    if not routed:
        logger.warning("No webhooks are configured; nothing will be relayed.")
    else:
        logger.info("Relaying events.", extra={"events": routed})

    while True:
        try:
            async for text in stream.messages():
                await _relay(
                    text,
                    discord,
                    webhooks=webhooks,
                    site_url=site_url,
                    server_name=server_name,
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("The event stream failed; resubscribing.")

        await asyncio.sleep(_RECONNECT_SECONDS)
