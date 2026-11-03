import re
from datetime import UTC
from decimal import Context, Decimal, localcontext

from sqlalchemy.orm import Session

from splitbill import expense_repository, services
from splitbill.errors import ApiError
from splitbill.expense_schemas import EqualSplitRequest, ExpenseCreateRequest, ExpenseResponse
from splitbill.models import Expense, ExpenseShare
from splitbill.money import MAX_AMOUNT, split_equal

MONEY_PATTERN = re.compile(r"[0-9]+(?:\.[0-9]{1,2})?")


def parse_money(value: str, *, label: str, allow_zero: bool = False) -> Decimal:
    if MONEY_PATTERN.fullmatch(value) is None:
        raise ApiError(
            422,
            "invalid_amount",
            f"{label} must use plain decimal digits with at most two decimal places",
        )
    amount = Decimal(value)
    if amount > MAX_AMOUNT or amount < 0 or (amount == 0 and not allow_zero):
        minimum = "zero or greater" if allow_zero else "greater than zero"
        raise ApiError(
            422, "invalid_amount", f"{label} must be {minimum} and no more than {MAX_AMOUNT}"
        )
    return amount


def allocate_shares(
    payload: ExpenseCreateRequest, amount: Decimal, group_members: list[str]
) -> dict[str, Decimal]:
    members = set(group_members)
    if payload.paid_by not in members:
        raise ApiError(422, "invalid_payer", "The payer must be a member of this group")

    if isinstance(payload.split, EqualSplitRequest):
        selected = payload.split.members
        if len(set(selected)) != len(selected):
            raise ApiError(422, "invalid_split", "Split members must not contain duplicates")
        if not set(selected) <= members:
            raise ApiError(422, "invalid_split", "Every split member must belong to this group")
        return split_equal(amount, selected)

    if not set(payload.split.shares) <= members:
        raise ApiError(422, "invalid_split", "Every split member must belong to this group")
    shares = {
        username: parse_money(value, label=f"Share for {username}", allow_zero=True)
        for username, value in payload.split.shares.items()
    }
    with localcontext(Context(prec=28)):
        if sum(shares.values(), Decimal("0.00")) != amount:
            raise ApiError(422, "invalid_split", "The shares do not add up to the total")
    return shares


def expense_response(expense: Expense, shares: list[ExpenseShare]) -> ExpenseResponse:
    return ExpenseResponse(
        id=expense.id,
        group_id=expense.group_id,
        description=expense.description,
        paid_by=expense.paid_by,
        amount=format(expense.amount, ".2f"),
        split_type=expense.split_type,
        shares={share.username: format(share.amount, ".2f") for share in shares},
        created_at=expense.created_at.astimezone(UTC),
        deleted=expense.deleted,
    )


def stored_response(session: Session, expense: Expense) -> ExpenseResponse:
    return expense_response(expense, expense_repository.get_expense_shares(session, [expense.id]))


def create_expense(
    session: Session,
    group_id: int,
    username: str,
    key: str,
    payload: ExpenseCreateRequest,
) -> tuple[ExpenseResponse, bool]:
    group = services.read_group(session, group_id, username)
    if not key.strip():
        raise ApiError(422, "invalid_idempotency_key", "Idempotency-Key must not be blank")

    existing = expense_repository.get_expense_by_key(session, group_id, key)
    if existing is not None:
        return stored_response(session, existing), False

    amount = parse_money(payload.amount, label="Amount")
    shares = allocate_shares(payload, amount, group.members)
    expense = expense_repository.insert_expense(
        session,
        group_id=group_id,
        key=key,
        description=payload.description,
        paid_by=payload.paid_by,
        amount=amount,
        split_type=payload.split.type,
    )
    if expense is None:
        # This separate statement sees the winning transaction after ON CONFLICT waits.
        existing = expense_repository.get_expense_by_key(session, group_id, key)
        if existing is None:
            raise RuntimeError("The conflicting expense was not visible after its transaction")
        return stored_response(session, existing), False

    expense_repository.add_expense_shares(session, expense.id, group_id, shares)
    result = stored_response(session, expense)
    # The request dependency closes/rolls back the session if any write or commit fails.
    session.commit()
    return result, True


def list_expenses(session: Session, group_id: int, username: str) -> list[ExpenseResponse]:
    services.read_group(session, group_id, username)
    records = expense_repository.list_group_expenses(session, group_id)
    shares_by_expense: dict[int, list[ExpenseShare]] = {expense.id: [] for expense in records}
    for share in expense_repository.get_expense_shares(
        session, [expense.id for expense in records]
    ):
        shares_by_expense[share.expense_id].append(share)
    return [expense_response(expense, shares_by_expense[expense.id]) for expense in records]


def delete_expense(session: Session, group_id: int, expense_id: int, username: str) -> None:
    services.read_group(session, group_id, username)
    expense = expense_repository.get_group_expense(session, group_id, expense_id)
    if expense is None:
        raise ApiError(404, "expense_not_found", "Expense not found")
    if expense.paid_by != username:
        raise ApiError(403, "expense_delete_forbidden", "Only the payer can delete this expense")
    expense.deleted = True
    session.commit()
