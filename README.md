# Poltergeist Discord relay

Listens to the events a [Poltergeist](https://github.com/RealistikGDPS/Poltergeist)
server publishes on Redis and posts them to Discord webhooks as embeds: new
accounts, level uploads, ratings, dailies, bans, roles, settings changes and
the full moderation log. Python 3.14, no database access, no ports.

Each event kind is routed to its own webhook, so a public channel can carry
rated levels while a staff channel receives the moderation log. An event
without a webhook is ignored, which is how the relay is opted into one event
at a time.

## Configuration

`configuration/discord.env.example` lists one `DISCORD_WEBHOOK_<KIND>`
variable per event kind. Set it to a webhook URL to relay that event, or to
several URLs separated by commas to post it in more than one channel. Leave
it empty to skip the event. The kinds and their payloads are documented in
[poltergeist-core](https://github.com/RealistikGDPS/poltergeist-core#events).

On top of that the relay reads `APP_PUBLIC_URL` and `APP_SERVER_NAME` (the
website address the embeds link to and the name the webhook posts as, shared
with the server's `app.env`), `REDIS_HOST`, `REDIS_PORT`, `REDIS_DATABASE`,
`DISCORD_TIMEOUT_SECONDS` and `APP_COMPONENT=relay`.

## Behaviour

- Embeds link players to their profile on the website and moderation log
  entries to the admin area. Player-typed text is escaped and mentions are
  never resolved, so a level name cannot ping a role.
- A rate-limited webhook is retried after the wait Discord asks for. Other
  failures are logged and the event is skipped; Pub/Sub has no replay.
- Losing the Redis connection resubscribes after a short pause. Events
  published meanwhile are missed.
- `moderation.action` mirrors every moderation log row, so routing it and a
  typed event such as `users.banned` to the same channel posts twice.

## Layout

```
relay/adapters/    Redis subscription and the Discord webhook client
relay/events.py    The wire contract: envelope and one model per event kind
relay/embeds.py    Event to Discord embed
relay/service.py   The relay loop
relay/main.py      Entry point, selected by APP_COMPONENT
relay/settings.py  Configuration read from the environment
```

## Running

The `Dockerfile` builds the image and pushing `master` publishes
`ghcr.io/realistikgdps/poltergeist-discord`. The
[deployment](https://github.com/RealistikGDPS/deployment) starts the relay
only when `configuration/discord.env` names at least one webhook.

Locally, export the variables above and:

```bash
uv sync
make lint
APP_COMPONENT=relay uv run python -m relay.main
```
