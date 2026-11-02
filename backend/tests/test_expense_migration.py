from sqlalchemy import Numeric, inspect


def test_migration_creates_expense_tables_with_exact_money_columns(database_engine):
    inspector = inspect(database_engine)
    assert {"expenses", "expense_shares"} <= set(inspector.get_table_names())

    for table in ("expenses", "expense_shares"):
        columns = {column["name"]: column for column in inspector.get_columns(table)}
        amount_type = columns["amount"]["type"]
        assert isinstance(amount_type, Numeric)
        assert (amount_type.precision, amount_type.scale) == (12, 2)
