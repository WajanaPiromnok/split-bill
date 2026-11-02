from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

MemberName = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=64)]
MoneyInput = Annotated[str, StringConstraints(strict=True, max_length=64)]


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EqualSplitRequest(RequestModel):
    type: Literal["equal"]
    members: list[MemberName] = Field(min_length=1)


class ExactSplitRequest(RequestModel):
    type: Literal["exact"]
    shares: dict[MemberName, MoneyInput] = Field(min_length=1)


SplitRequest = Annotated[EqualSplitRequest | ExactSplitRequest, Field(discriminator="type")]


class ExpenseCreateRequest(RequestModel):
    description: Annotated[
        str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=500)
    ]
    paid_by: MemberName
    amount: MoneyInput
    split: SplitRequest


class ExpenseResponse(BaseModel):
    id: int
    group_id: int
    description: str
    paid_by: str
    amount: str
    split_type: Literal["equal", "exact"]
    shares: dict[str, str]
    created_at: datetime
    deleted: bool
