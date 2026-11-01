"""Create users, groups and group memberships.

Revision ID: 20261101_0001
Revises:
"""

import sqlalchemy as sa

from alembic import op

revision = "20261101_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("username", sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint("username"),
    )
    op.create_table(
        "groups",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "group_members",
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(64), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.ForeignKeyConstraint(["username"], ["users.username"]),
        sa.PrimaryKeyConstraint("group_id", "username"),
    )


def downgrade() -> None:
    op.drop_table("group_members")
    op.drop_table("groups")
    op.drop_table("users")
