from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from splitbill.seed import seed_database


def test_migration_creates_group_tables(database_engine):
    assert {"users", "groups", "group_members"} <= set(inspect(database_engine).get_table_names())


def test_seed_is_complete_and_safe_to_replay(database_engine):
    with Session(database_engine) as session, session.begin():
        seed_database(session)
        seed_database(session)
        assert session.execute(
            text("SELECT username FROM users ORDER BY username")
        ).scalars().all() == ["alice", "bob", "carol", "dan"]
        assert session.execute(text("SELECT id, name FROM groups ORDER BY id")).all() == [
            (1, "Chiang Mai trip"),
            (2, "Office lunch"),
        ]
        assert session.execute(
            text("SELECT group_id, username FROM group_members ORDER BY group_id, username")
        ).all() == [(1, "alice"), (1, "bob"), (1, "carol"), (2, "bob"), (2, "dan")]
