from sqlalchemy.orm import Session

from splitbill import repository
from splitbill.errors import ApiError
from splitbill.models import Group
from splitbill.schemas import GroupDetail


def require_user(session: Session, username: str) -> str:
    if not username or not repository.user_exists(session, username):
        raise ApiError(401, "unauthenticated", "A valid X-User header is required")
    return username


def list_groups(session: Session, username: str) -> list[Group]:
    return repository.groups_for_user(session, username)


def read_group(session: Session, group_id: int, username: str) -> GroupDetail:
    group = repository.group_for_member(session, group_id, username)
    if group is None:
        raise ApiError(404, "group_not_found", "Group not found")
    return GroupDetail(
        id=group.id, name=group.name, members=repository.members_of_group(session, group_id)
    )
