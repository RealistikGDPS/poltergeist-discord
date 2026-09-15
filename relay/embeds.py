import json
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime

from gdformat.enums import Rating

from relay.events import Event
from relay.events import LeaderboardsRebuilt
from relay.events import LevelDeleted
from relay.events import LevelMoved
from relay.events import LevelRated
from relay.events import LevelUpdated
from relay.events import LevelUploaded
from relay.events import ModerationAction
from relay.events import Received
from relay.events import RoleAssigned
from relay.events import RoleRevoked
from relay.events import ServerSettingsUpdated
from relay.events import TimelyScheduled
from relay.events import UserBanned
from relay.events import UserFlagged
from relay.events import UserRegistered
from relay.events import UserRenamed
from relay.events import UserUnbanned

# Discord's own palette, so the embeds sit naturally next to its UI.
_GREEN = 0x57F287
_RED = 0xED4245
_YELLOW = 0xFEE75C
_BLURPLE = 0x5865F2
_FUCHSIA = 0xEB459E
_ORANGE = 0xE67E22
_GREY = 0x99AAB5

# Discord's limits per embed.
_TITLE_LIMIT = 256
_DESCRIPTION_LIMIT = 4096
_FIELD_VALUE_LIMIT = 1024
_FIELD_LIMIT = 25

_NONE = "—"
_MARKDOWN = str.maketrans({character: "\\" + character for character in "\\*_~`|>#[]"})


@dataclass(frozen=True, slots=True)
class Field:
    name: str
    value: str
    inline: bool = True


@dataclass(frozen=True, slots=True)
class Embed:
    title: str
    colour: int
    description: str = ""
    url: str | None = None
    fields: tuple[Field, ...] = ()


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _escape(text: str) -> str:
    return text.translate(_MARKDOWN)


def _label(name: str) -> str:
    return name.replace("_", " ").capitalize()


def _absolute(unix: int) -> str:
    return f"<t:{unix}:f>"


def _relative(unix: int) -> str:
    return f"<t:{unix}:R>"


class _Links:
    """Builds the website links the embeds point at."""

    __slots__ = ("_site_url",)

    def __init__(self, site_url: str) -> None:
        self._site_url = site_url

    def profile_url(self, user_id: int) -> str:
        return f"{self._site_url}/users/{user_id}"

    def user(self, user_id: int, username: str | None = None) -> str:
        label = f"user #{user_id}" if username is None else _escape(username)

        return f"[{label}]({self.profile_url(user_id)})"

    def actor(self, actor_user_id: int, *, subject_user_id: int | None = None) -> str:
        if actor_user_id == subject_user_id:
            return "Themselves"

        return self.user(actor_user_id)

    def admin_flags_url(self) -> str:
        return f"{self._site_url}/admin/flags"

    def admin_target(self, target_type: str, target_id: int) -> str | None:
        match target_type:
            case "user":
                return f"{self._site_url}/admin/users/{target_id}"
            case "level":
                return f"{self._site_url}/admin/levels/{target_id}"
            case _:
                return None


def _details(details: dict[str, object]) -> str:
    lines = [
        f"`{key}`: {json.dumps(value) if not isinstance(value, str) else value}"
        for key, value in details.items()
    ]

    return "\n".join(lines) if lines else _NONE


def _user_registered(event: UserRegistered, links: _Links) -> Embed:
    return Embed(
        title=f"New account: {_escape(event.username)}",
        colour=_GREEN,
        url=links.profile_url(event.user_id),
        fields=(Field("ID", str(event.user_id)),),
    )


def _user_renamed(event: UserRenamed, links: _Links) -> Embed:
    return Embed(
        title="Username changed",
        colour=_BLURPLE,
        description=(
            f"**{_escape(event.old_username)}** is now "
            f"**{_escape(event.new_username)}**."
        ),
        url=links.profile_url(event.user_id),
        fields=(
            Field(
                "By", links.actor(event.actor_user_id, subject_user_id=event.user_id)
            ),
        ),
    )


def _user_banned(event: UserBanned, links: _Links) -> Embed:
    if event.days is None or event.expires_at is None:
        duration = "Permanent"
    else:
        duration = f"{event.days} days, ends {_relative(event.expires_at)}"

    return Embed(
        title=f"{_label(event.ban_type)} ban: {_escape(event.username)}",
        colour=_RED,
        url=links.profile_url(event.user_id),
        fields=(
            Field("Duration", duration),
            Field("By", links.user(event.actor_user_id)),
            Field("Reason", _escape(event.reason) or _NONE, inline=False),
        ),
    )


def _user_unbanned(event: UserUnbanned, links: _Links) -> Embed:
    return Embed(
        title=f"{_label(event.ban_type)} ban lifted: {_escape(event.username)}",
        colour=_GREEN,
        url=links.profile_url(event.user_id),
        fields=(
            Field("Bans lifted", str(event.revoked)),
            Field("By", links.user(event.actor_user_id)),
        ),
    )


def _user_flagged(event: UserFlagged, links: _Links) -> Embed:
    return Embed(
        title=f"Flagged ({_label(event.flag_kind).lower()}): {_escape(event.username)}",
        colour=_ORANGE,
        url=links.admin_target("user", event.user_id),
        fields=(
            Field("Evidence", _escape(event.summary) or _NONE, inline=False),
            Field("Flag", f"[#{event.flag_id}]({links.admin_flags_url()})"),
            Field("Profile", links.user(event.user_id, event.username)),
        ),
    )


def _level_uploaded(event: LevelUploaded | LevelUpdated, links: _Links) -> Embed:
    updated = isinstance(event, LevelUpdated)
    heading = "Level updated" if updated else "New level"

    return Embed(
        title=f"{heading}: {_escape(event.level_name)}",
        colour=_BLURPLE if updated else _GREEN,
        fields=(
            Field("Creator", links.user(event.user_id, event.username)),
            Field("ID", str(event.level_id)),
            Field("Version", str(event.version)),
        ),
    )


def _level_deleted(event: LevelDeleted, links: _Links) -> Embed:
    return Embed(
        title=f"Level deleted: {_escape(event.level_name)}",
        colour=_RED,
        fields=(
            Field("Creator", links.user(event.user_id)),
            Field("ID", str(event.level_id)),
            Field(
                "By", links.actor(event.actor_user_id, subject_user_id=event.user_id)
            ),
        ),
    )


def _level_moved(event: LevelMoved, links: _Links) -> Embed:
    return Embed(
        title=f"Level moved: {_escape(event.level_name)}",
        colour=_BLURPLE,
        fields=(
            Field("From", links.user(event.from_user_id, event.from_username)),
            Field("To", links.user(event.to_user_id, event.to_username)),
            Field("ID", str(event.level_id)),
            Field(
                "By",
                links.actor(event.actor_user_id, subject_user_id=event.to_user_id),
            ),
        ),
    )


def _level_rated(event: LevelRated, links: _Links) -> Embed:
    if event.rating is not Rating.NONE:
        feature = event.rating.name.capitalize()
    elif event.feature_order > 0:
        feature = "Featured"
    else:
        feature = _NONE

    unrated = event.stars == 0
    heading = "Level unrated" if unrated else "Level rated"

    return Embed(
        title=f"{heading}: {_escape(event.level_name)}",
        colour=_GREY if unrated else _YELLOW,
        fields=(
            Field("Creator", links.user(event.user_id, event.username)),
            Field("Stars", str(event.stars)),
            Field("Difficulty", event.difficulty.name.replace("_", " ").title()),
            Field("Feature", feature),
            Field("ID", str(event.level_id)),
            Field("By", links.user(event.actor_user_id)),
        ),
    )


def _timely_scheduled(event: TimelyScheduled, links: _Links) -> Embed:
    return Embed(
        title=(
            f"{event.timely_type.name.capitalize()} #{event.sequence}: "
            f"{_escape(event.level_name)}"
        ),
        colour=_FUCHSIA,
        fields=(
            Field("Level ID", str(event.level_id)),
            Field("Starts", _absolute(event.starts_at)),
            Field("Ends", _absolute(event.ends_at)),
            Field("By", links.user(event.actor_user_id)),
        ),
    )


def _role_assigned(event: RoleAssigned, links: _Links) -> Embed:
    expires = "Never" if event.expires_at is None else _relative(event.expires_at)

    return Embed(
        title="Role assigned",
        colour=_BLURPLE,
        description=(
            f"{links.user(event.user_id, event.username)} was given "
            f"**{_escape(event.role_name)}**."
        ),
        fields=(
            Field("Expires", expires),
            Field("By", links.user(event.actor_user_id)),
        ),
    )


def _role_revoked(event: RoleRevoked, links: _Links) -> Embed:
    return Embed(
        title="Role revoked",
        colour=_ORANGE,
        description=(
            f"**{_escape(event.role_name)}** was removed from "
            f"{links.user(event.user_id)}."
        ),
        fields=(Field("By", links.user(event.actor_user_id)),),
    )


def _server_settings_updated(event: ServerSettingsUpdated, links: _Links) -> Embed:
    changes = tuple(
        Field(_label(key), _escape(str(value)))
        for key, value in list(event.changes.items())[: _FIELD_LIMIT - 1]
    )

    return Embed(
        title="Server settings changed",
        colour=_ORANGE,
        fields=(*changes, Field("By", links.user(event.actor_user_id), inline=False)),
    )


def _leaderboards_rebuilt(event: LeaderboardsRebuilt) -> Embed:
    return Embed(
        title="Leaderboards rebuilt",
        colour=_GREY,
        fields=(Field("Ranked accounts", str(event.users)),),
    )


def _moderation_action(event: ModerationAction, links: _Links) -> Embed:
    target = f"{_label(event.target_type)} #{event.target_id}"
    target_url = links.admin_target(event.target_type, event.target_id)

    return Embed(
        title=f"{_label(event.action)}: {target}",
        colour=_GREY,
        url=target_url,
        fields=(
            Field("Actor", links.user(event.actor_user_id)),
            Field("Log entry", f"#{event.mod_action_id}"),
            Field("Details", _details(event.details or {}), inline=False),
        ),
    )


def _embed(event: Event, links: _Links) -> Embed | None:
    match event:
        case UserRegistered():
            return _user_registered(event, links)
        case UserRenamed():
            return _user_renamed(event, links)
        case UserBanned():
            return _user_banned(event, links)
        case UserUnbanned():
            return _user_unbanned(event, links)
        case UserFlagged():
            return _user_flagged(event, links)
        case LevelUploaded() | LevelUpdated():
            return _level_uploaded(event, links)
        case LevelDeleted():
            return _level_deleted(event, links)
        case LevelMoved():
            return _level_moved(event, links)
        case LevelRated():
            return _level_rated(event, links)
        case TimelyScheduled():
            return _timely_scheduled(event, links)
        case RoleAssigned():
            return _role_assigned(event, links)
        case RoleRevoked():
            return _role_revoked(event, links)
        case ServerSettingsUpdated():
            return _server_settings_updated(event, links)
        case LeaderboardsRebuilt():
            return _leaderboards_rebuilt(event)
        case ModerationAction():
            return _moderation_action(event, links)
        case _:
            return None


def _serialise(embed: Embed, received: Received) -> dict[str, object]:
    emitted_at = datetime.fromtimestamp(received.envelope.emitted_at, tz=UTC)

    serialised: dict[str, object] = {
        "title": _clip(embed.title, _TITLE_LIMIT),
        "color": embed.colour,
        "timestamp": emitted_at.isoformat(),
        "footer": {"text": received.envelope.component},
        "fields": [
            {
                "name": field.name,
                "value": _clip(field.value, _FIELD_VALUE_LIMIT),
                "inline": field.inline,
            }
            for field in embed.fields
        ],
    }

    if embed.description:
        serialised["description"] = _clip(embed.description, _DESCRIPTION_LIMIT)

    if embed.url is not None:
        serialised["url"] = embed.url

    return serialised


def message(
    received: Received, *, site_url: str, server_name: str
) -> dict[str, object] | None:
    """The webhook body for an event, or `None` for a kind without an embed.
    Mentions are never resolved: names and reasons are typed by players."""

    embed = _embed(received.event, _Links(site_url))

    if embed is None:
        return None

    return {
        "username": server_name,
        "allowed_mentions": {"parse": []},
        "embeds": [_serialise(embed, received)],
    }
