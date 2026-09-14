from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from typing import ClassVar

from gdformat.enums import Difficulty
from gdformat.enums import Rating
from gdformat.enums import TimelyType
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import ValidationError


class Model(BaseModel):
    model_config = ConfigDict(frozen=True)


class Envelope(Model):
    """The wire shape of every message on `poltergeist:*`, as documented in
    poltergeist-core's README."""

    event: str
    component: str
    emitted_at: int
    data: dict[str, Any]


class Event(Model):
    kind: ClassVar[str]


class UserRegistered(Event):
    kind: ClassVar[str] = "users.registered"

    user_id: int
    username: str


class UserRenamed(Event):
    kind: ClassVar[str] = "users.renamed"

    user_id: int
    old_username: str
    new_username: str
    actor_user_id: int


class UserBanned(Event):
    kind: ClassVar[str] = "users.banned"

    ban_id: int
    user_id: int
    username: str
    ban_type: str
    reason: str
    days: int | None
    expires_at: int | None
    actor_user_id: int


class UserUnbanned(Event):
    kind: ClassVar[str] = "users.unbanned"

    user_id: int
    username: str
    ban_type: str
    revoked: int
    actor_user_id: int


class UserFlagged(Event):
    kind: ClassVar[str] = "users.flagged"

    flag_id: int
    user_id: int
    username: str
    flag_kind: str
    summary: str


class LevelUploaded(Event):
    kind: ClassVar[str] = "levels.uploaded"

    level_id: int
    level_name: str
    user_id: int
    username: str
    version: int


class LevelUpdated(Event):
    kind: ClassVar[str] = "levels.updated"

    level_id: int
    level_name: str
    user_id: int
    username: str
    version: int


class LevelDeleted(Event):
    kind: ClassVar[str] = "levels.deleted"

    level_id: int
    level_name: str
    user_id: int
    actor_user_id: int


class LevelRated(Event):
    kind: ClassVar[str] = "levels.rated"

    level_id: int
    level_name: str
    user_id: int
    username: str
    stars: int
    difficulty: Difficulty
    rating: Rating
    feature_order: int
    actor_user_id: int


class TimelyScheduled(Event):
    kind: ClassVar[str] = "timely.scheduled"

    timely_id: int
    timely_type: TimelyType
    sequence: int
    level_id: int
    level_name: str
    starts_at: int
    ends_at: int
    actor_user_id: int


class RoleAssigned(Event):
    kind: ClassVar[str] = "roles.assigned"

    user_id: int
    username: str
    role_id: int
    role_name: str
    expires_at: int | None
    actor_user_id: int


class RoleRevoked(Event):
    kind: ClassVar[str] = "roles.revoked"

    user_id: int
    role_id: int
    role_name: str
    actor_user_id: int


class ServerSettingsUpdated(Event):
    kind: ClassVar[str] = "server_settings.updated"

    changes: dict[str, Any]
    actor_user_id: int


class LeaderboardsRebuilt(Event):
    kind: ClassVar[str] = "leaderboards.rebuilt"

    users: int


class ModerationAction(Event):
    kind: ClassVar[str] = "moderation.action"

    mod_action_id: int
    actor_user_id: int
    action: str
    target_type: str
    target_id: int
    details: dict[str, Any] | None


class ParseError(StrEnum):
    MALFORMED = "malformed"
    UNKNOWN_EVENT = "unknown_event"


@dataclass(frozen=True, slots=True)
class Received:
    envelope: Envelope
    event: Event


_EVENT_TYPES: dict[str, type[Event]] = {
    event_type.kind: event_type
    for event_type in (
        UserRegistered,
        UserRenamed,
        UserBanned,
        UserUnbanned,
        UserFlagged,
        LevelUploaded,
        LevelUpdated,
        LevelDeleted,
        LevelRated,
        TimelyScheduled,
        RoleAssigned,
        RoleRevoked,
        ServerSettingsUpdated,
        LeaderboardsRebuilt,
        ModerationAction,
    )
}


def parse(text: str) -> Received | ParseError:
    # Pydantic signals invalid input by raising; it offers no non-raising API.
    try:
        envelope = Envelope.model_validate_json(text)
    except ValidationError:
        return ParseError.MALFORMED

    event_type = _EVENT_TYPES.get(envelope.event)

    if event_type is None:
        return ParseError.UNKNOWN_EVENT

    try:
        event = event_type.model_validate(envelope.data)
    except ValidationError:
        return ParseError.MALFORMED

    return Received(envelope=envelope, event=event)
