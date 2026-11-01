from pydantic import BaseModel, ConfigDict


class GroupSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class GroupDetail(GroupSummary):
    members: list[str]


class ErrorDetail(BaseModel):
    field: str
    message: str
    type: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody
