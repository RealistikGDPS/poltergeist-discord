import os

APP_COMPONENT = os.environ["APP_COMPONENT"]
APP_PUBLIC_URL = os.environ["APP_PUBLIC_URL"].rstrip("/")
APP_SERVER_NAME = os.environ["APP_SERVER_NAME"]

REDIS_HOST = os.environ["REDIS_HOST"]
REDIS_PORT = int(os.environ["REDIS_PORT"])
REDIS_DATABASE = int(os.environ["REDIS_DATABASE"])

DISCORD_TIMEOUT_SECONDS = float(os.environ["DISCORD_TIMEOUT_SECONDS"])


def _webhooks(kind: str) -> tuple[str, ...]:
    # Unset or empty means the event is not relayed; opting in is per event.
    raw = os.environ.get("DISCORD_WEBHOOK_" + kind.replace(".", "_").upper(), "")

    return tuple(url.strip() for url in raw.split(",") if url.strip())


DISCORD_WEBHOOKS = {
    kind: _webhooks(kind)
    for kind in (
        "users.registered",
        "users.renamed",
        "users.banned",
        "users.unbanned",
        "users.flagged",
        "levels.uploaded",
        "levels.updated",
        "levels.deleted",
        "levels.moved",
        "levels.rated",
        "timely.scheduled",
        "roles.assigned",
        "roles.revoked",
        "server_settings.updated",
        "leaderboards.rebuilt",
        "moderation.action",
    )
}
