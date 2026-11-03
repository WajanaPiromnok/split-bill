from fastapi import APIRouter

from splitbill import balances
from splitbill.api import CurrentUser, DatabaseSession
from splitbill.schemas import ErrorResponse

router = APIRouter(prefix="/groups/{group_id}/balances", tags=["balances"])


@router.get(
    "",
    response_model=dict[str, str],
    responses={
        401: {"model": ErrorResponse, "description": "Missing, empty or unknown X-User"},
        404: {"model": ErrorResponse, "description": "Group not found or inaccessible"},
        422: {"model": ErrorResponse, "description": "Invalid path parameters"},
    },
)
def read_balances(group_id: int, session: DatabaseSession, username: CurrentUser) -> dict[str, str]:
    return balances.read_balances(session, group_id, username)
