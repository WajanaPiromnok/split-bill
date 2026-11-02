from typing import Annotated

from fastapi import APIRouter, Header, Response

from splitbill import expenses
from splitbill.api import CurrentUser, DatabaseSession
from splitbill.expense_schemas import ExpenseCreateRequest, ExpenseResponse
from splitbill.schemas import ErrorResponse

router = APIRouter(prefix="/groups/{group_id}/expenses", tags=["expenses"])

ERROR_RESPONSES = {
    401: {"model": ErrorResponse, "description": "Missing, empty or unknown X-User"},
    404: {"model": ErrorResponse, "description": "Group not found or inaccessible"},
    422: {"model": ErrorResponse, "description": "Invalid request or expense allocation"},
}


@router.post(
    "",
    response_model=ExpenseResponse,
    status_code=201,
    responses={
        **ERROR_RESPONSES,
        200: {"model": ExpenseResponse, "description": "Original expense for an existing key"},
    },
)
def create_expense(
    group_id: int,
    payload: ExpenseCreateRequest,
    response: Response,
    session: DatabaseSession,
    username: CurrentUser,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=200)],
):
    result, created = expenses.create_expense(session, group_id, username, idempotency_key, payload)
    response.status_code = 201 if created else 200
    return result


@router.get("", response_model=list[ExpenseResponse], responses=ERROR_RESPONSES)
def list_expenses(group_id: int, session: DatabaseSession, username: CurrentUser):
    return expenses.list_expenses(session, group_id, username)
