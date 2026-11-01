from sqlalchemy import select
from sqlalchemy.orm import Session

from splitbill.models import Group, GroupMember, User


def user_exists(session: Session, username: str) -> bool:
    return session.get(User, username) is not None


def groups_for_user(session: Session, username: str) -> list[Group]:
    return list(
        session.scalars(
            select(Group)
            .join(GroupMember, GroupMember.group_id == Group.id)
            .where(GroupMember.username == username)
            .order_by(Group.id)
        )
    )


def group_for_member(session: Session, group_id: int, username: str) -> Group | None:
    return session.scalar(
        select(Group)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .where(Group.id == group_id, GroupMember.username == username)
    )


def members_of_group(session: Session, group_id: int) -> list[str]:
    return list(
        session.scalars(
            select(GroupMember.username)
            .where(GroupMember.group_id == group_id)
            .order_by(GroupMember.username)
        )
    )
