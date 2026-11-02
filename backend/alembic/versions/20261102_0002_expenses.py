"""Add immutable expenses, ordered shares and group-scoped idempotency.

Revision ID: 20261102_0002
Revises: 20261101_0001
"""

import sqlalchemy as sa

from alembic import op

revision = "20261102_0002"
down_revision = "20261101_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "expenses",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("paid_by", sa.String(64), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("split_type", sa.String(5), nullable=False),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.ForeignKeyConstraint(
            ["group_id", "paid_by"],
            ["group_members.group_id", "group_members.username"],
            name="fk_expenses_payer_membership",
        ),
        sa.UniqueConstraint("group_id", "idempotency_key", name="uq_expenses_group_key"),
        sa.UniqueConstraint("id", "group_id", name="uq_expenses_id_group"),
        sa.CheckConstraint(
            "amount > 0 AND amount <= 9999999999.99", name="ck_expenses_amount_range"
        ),
        sa.CheckConstraint("split_type IN ('equal', 'exact')", name="ck_expenses_split_type"),
        sa.CheckConstraint("length(btrim(description)) > 0", name="ck_expenses_description"),
    )
    op.create_index("ix_expenses_group_created", "expenses", ["group_id", "created_at", "id"])
    op.create_table(
        "expense_shares",
        sa.Column("expense_id", sa.BigInteger(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.PrimaryKeyConstraint("expense_id", "username"),
        sa.ForeignKeyConstraint(
            ["expense_id", "group_id"],
            ["expenses.id", "expenses.group_id"],
            name="fk_expense_shares_expense_group",
        ),
        sa.ForeignKeyConstraint(
            ["group_id", "username"],
            ["group_members.group_id", "group_members.username"],
            name="fk_expense_shares_membership",
        ),
        sa.UniqueConstraint("expense_id", "position", name="uq_expense_shares_position"),
        sa.CheckConstraint(
            "amount >= 0 AND amount <= 9999999999.99", name="ck_expense_shares_amount_range"
        ),
        sa.CheckConstraint("position >= 0", name="ck_expense_shares_position"),
    )


def downgrade() -> None:
    op.drop_table("expense_shares")
    op.drop_index("ix_expenses_group_created", table_name="expenses")
    op.drop_table("expenses")
