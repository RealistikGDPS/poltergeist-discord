import asyncio
from enum import StrEnum
from http import HTTPStatus

import httpx

from relay.utilities import logging

logger = logging.get_logger(__name__)

_RATE_LIMIT_ATTEMPTS = 3
_RETRY_AFTER_DEFAULT_SECONDS = 1.0
_RETRY_AFTER_MAX_SECONDS = 30.0
_BODY_LOG_LIMIT = 200


class DiscordError(StrEnum):
    UNREACHABLE = "unreachable"
    REJECTED = "rejected"
    RATE_LIMITED = "rate_limited"
    UNAVAILABLE = "unavailable"


def _retry_after(response: httpx.Response) -> float:
    header = response.headers.get("Retry-After")

    if header is None:
        return _RETRY_AFTER_DEFAULT_SECONDS

    try:
        seconds = float(header)
    except ValueError:
        # `float` has no non-raising parse; a malformed header is Discord's
        # bug, not a reason to stop retrying.
        return _RETRY_AFTER_DEFAULT_SECONDS

    return min(max(seconds, 0.0), _RETRY_AFTER_MAX_SECONDS)


class DiscordClient:
    """Posts webhook messages. The webhook URL is a secret and is therefore
    never logged."""

    def __init__(self, *, timeout_seconds: float) -> None:
        self._client = httpx.AsyncClient(timeout=timeout_seconds)

    async def close(self) -> None:
        await self._client.aclose()

    async def post(self, url: str, payload: dict[str, object]) -> DiscordError | None:
        """Waits out a rate limit for the time Discord asks, a few times over."""

        for _ in range(_RATE_LIMIT_ATTEMPTS):
            try:
                response = await self._client.post(url, json=payload)
            except httpx.HTTPError:
                logger.warning("Discord could not be reached.")

                return DiscordError.UNREACHABLE

            if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                wait = _retry_after(response)
                logger.warning(
                    "Discord rate limited the webhook.", extra={"retry_after": wait}
                )
                await asyncio.sleep(wait)

                continue

            if response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
                logger.warning(
                    "Discord returned a server error.",
                    extra={"status_code": response.status_code},
                )

                return DiscordError.UNAVAILABLE

            if response.status_code >= HTTPStatus.BAD_REQUEST:
                logger.warning(
                    "Discord rejected the webhook.",
                    extra={
                        "status_code": response.status_code,
                        "body": response.text[:_BODY_LOG_LIMIT],
                    },
                )

                return DiscordError.REJECTED

            return None

        return DiscordError.RATE_LIMITED


def default() -> DiscordClient:
    # Local import keeps this module importable without configuration.
    from relay import settings

    return DiscordClient(timeout_seconds=settings.DISCORD_TIMEOUT_SECONDS)
