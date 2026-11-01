from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from splitbill import services
from splitbill.schemas import ErrorResponse, GroupDetail, GroupSummary

router = APIRouter(tags=["groups"])


def get_session(request: Request) -> Iterator[Session]:
    with Session(request.app.state.engine) as session:
        yield session


DatabaseSession = Annotated[Session, Depends(get_session)]


def get_user(session: DatabaseSession, username: Annotated[str, Header(alias="X-User")]) -> str:
    return services.require_user(session, username)


CurrentUser = Annotated[str, Depends(get_user)]
ERROR_RESPONSES = {
    401: {"model": ErrorResponse, "description": "Missing, empty or unknown X-User"},
    404: {"model": ErrorResponse, "description": "Group not found or inaccessible"},
    422: {"model": ErrorResponse, "description": "Invalid request parameters"},
}


@router.get("/groups", response_model=list[GroupSummary], responses=ERROR_RESPONSES)
def list_groups(session: DatabaseSession, username: CurrentUser):
    return services.list_groups(session, username)


@router.get("/groups/{group_id}", response_model=GroupDetail, responses=ERROR_RESPONSES)
def read_group(group_id: int, session: DatabaseSession, username: CurrentUser):
    return services.read_group(session, group_id, username)
