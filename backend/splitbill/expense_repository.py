from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from splitbill.models import Expense, ExpenseShare


def get_expense_by_key(session: Session, group_id: int, key: str) -> Expense | None:
    # Include deleted rows: a deletion must not free an idempotency key for reuse.
    return session.scalar(
        select(Expense).where(Expense.group_id == group_id, Expense.idempotency_key == key)
    )


def insert_expense(
    session: Session,
    *,
    group_id: int,
    key: str,
    description: str,
    paid_by: str,
    amount: Decimal,
    split_type: str,
) -> Expense | None:
    statement = (
        insert(Expense)
        .values(
            group_id=group_id,
            idempotency_key=key,
            description=description,
            paid_by=paid_by,
            amount=amount,
            split_type=split_type,
        )
        .on_conflict_do_nothing(constraint="uq_expenses_group_key")
        .returning(Expense)
    )
    return session.scalars(statement).one_or_none()


def add_expense_shares(
    session: Session, expense_id: int, group_id: int, shares: dict[str, Decimal]
) -> None:
    session.execute(
        insert(ExpenseShare),
        [
            {
                "expense_id": expense_id,
                "group_id": group_id,
                "username": username,
                "position": position,
                "amount": amount,
            }
            for position, (username, amount) in enumerate(shares.items())
        ],
    )


def get_expense_shares(session: Session, expense_ids: list[int]) -> list[ExpenseShare]:
    if not expense_ids:
        return []
    return list(
        session.scalars(
            select(ExpenseShare)
            .where(ExpenseShare.expense_id.in_(expense_ids))
            .order_by(ExpenseShare.expense_id, ExpenseShare.position)
        )
    )
