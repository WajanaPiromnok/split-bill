from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from splitbill.config import Settings
from splitbill.models import Group, GroupMember, User


def seed_database(session: Session) -> None:
    """Insert the brief's seed records without overwriting or duplicating existing rows."""
    session.execute(
        insert(User)
        .values([{"username": name} for name in ("alice", "bob", "carol", "dan")])
        .on_conflict_do_nothing()
    )
    session.execute(
        insert(Group)
        .values([{"id": 1, "name": "Chiang Mai trip"}, {"id": 2, "name": "Office lunch"}])
        .on_conflict_do_nothing()
    )
    session.execute(
        insert(GroupMember)
        .values(
            [
                {"group_id": group_id, "username": username}
                for group_id, username in (
                    (1, "alice"),
                    (1, "bob"),
                    (1, "carol"),
                    (2, "bob"),
                    (2, "dan"),
                )
            ]
        )
        .on_conflict_do_nothing()
    )


def main() -> None:
    engine = create_engine(Settings().database_url)
    try:
        with Session(engine) as session, session.begin():
            seed_database(session)
        print("Seed complete (safe to replay).")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
