from sqlalchemy.orm import Session

from splitbill import balance_repository, services


def read_balances(session: Session, group_id: int, username: str) -> dict[str, str]:
    services.read_group(session, group_id, username)
    balances = balance_repository.balances_for_group(session, group_id)
    return {member: format(balance, ".2f") for member, balance in balances.items()}
