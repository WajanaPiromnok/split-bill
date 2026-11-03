from decimal import Decimal

from sqlalchemy import func, select, union_all
from sqlalchemy.orm import Session

from splitbill.models import Expense, ExpenseShare, GroupMember


def balances_for_group(session: Session, group_id: int) -> dict[str, Decimal]:
    credits = select(Expense.paid_by.label("username"), Expense.amount.label("delta")).where(
        Expense.group_id == group_id, Expense.deleted.is_(False)
    )
    debits = (
        select(ExpenseShare.username.label("username"), (-ExpenseShare.amount).label("delta"))
        .join(
            Expense,
            (ExpenseShare.expense_id == Expense.id) & (ExpenseShare.group_id == Expense.group_id),
        )
        .where(Expense.group_id == group_id, Expense.deleted.is_(False))
    )
    # One statement observes credits and debits from the same committed snapshot.
    movements = union_all(credits, debits).subquery()
    statement = (
        select(GroupMember.username, func.coalesce(func.sum(movements.c.delta), Decimal("0.00")))
        .outerjoin(movements, movements.c.username == GroupMember.username)
        .where(GroupMember.group_id == group_id)
        .group_by(GroupMember.username)
        .order_by(GroupMember.username)
    )
    return dict(session.execute(statement).all())
