from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    false,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(64), primary_key=True)


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String(200))


class GroupMember(Base):
    __tablename__ = "group_members"

    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), primary_key=True)
    username: Mapped[str] = mapped_column(ForeignKey("users.username"), primary_key=True)


class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (
        UniqueConstraint("group_id", "idempotency_key", name="uq_expenses_group_key"),
        UniqueConstraint("id", "group_id", name="uq_expenses_id_group"),
        ForeignKeyConstraint(
            ["group_id", "paid_by"],
            ["group_members.group_id", "group_members.username"],
            name="fk_expenses_payer_membership",
        ),
        CheckConstraint("amount > 0 AND amount <= 9999999999.99", name="ck_expenses_amount_range"),
        CheckConstraint("split_type IN ('equal', 'exact')", name="ck_expenses_split_type"),
        CheckConstraint("length(btrim(description)) > 0", name="ck_expenses_description"),
        Index("ix_expenses_group_created", "group_id", "created_at", "id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))
    description: Mapped[str] = mapped_column(String(500))
    paid_by: Mapped[str] = mapped_column(String(64))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    split_type: Mapped[str] = mapped_column(String(5))
    idempotency_key: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted: Mapped[bool] = mapped_column(Boolean, server_default=false())


class ExpenseShare(Base):
    __tablename__ = "expense_shares"
    __table_args__ = (
        ForeignKeyConstraint(
            ["expense_id", "group_id"],
            ["expenses.id", "expenses.group_id"],
            name="fk_expense_shares_expense_group",
        ),
        ForeignKeyConstraint(
            ["group_id", "username"],
            ["group_members.group_id", "group_members.username"],
            name="fk_expense_shares_membership",
        ),
        UniqueConstraint("expense_id", "position", name="uq_expense_shares_position"),
        CheckConstraint(
            "amount >= 0 AND amount <= 9999999999.99", name="ck_expense_shares_amount_range"
        ),
        CheckConstraint("position >= 0", name="ck_expense_shares_position"),
    )

    expense_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    group_id: Mapped[int] = mapped_column()
    username: Mapped[str] = mapped_column(String(64), primary_key=True)
    position: Mapped[int] = mapped_column()
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
