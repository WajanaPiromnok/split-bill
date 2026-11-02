from decimal import Decimal, localcontext

import pytest

from splitbill.money import split_equal


def test_split_equal_100_among_three_members():
    amount = Decimal("100.00")
    members = ["alice", "bob", "carol"]

    share = split_equal(amount, members)
    assert share == {
        "alice": Decimal("33.34"),
        "bob": Decimal("33.33"),
        "carol": Decimal("33.33"),
    }


@pytest.mark.parametrize(
    ("amount", "members", "expected"),
    [
        (
            Decimal("10.00"),
            ["alice", "bob"],
            {"alice": Decimal("5.00"), "bob": Decimal("5.00")},
        ),
        (
            Decimal("0.01"),
            ["alice", "bob", "carol"],
            {"alice": Decimal("0.01"), "bob": Decimal("0.00"), "carol": Decimal("0.00")},
        ),
        (
            Decimal("0.05"),
            ["alice", "bob", "carol"],
            {"alice": Decimal("0.02"), "bob": Decimal("0.02"), "carol": Decimal("0.01")},
        ),
        (
            Decimal("0.30"),
            ["alice", "bob", "carol"],
            {"alice": Decimal("0.10"), "bob": Decimal("0.10"), "carol": Decimal("0.10")},
        ),
        (
            Decimal("100.00"),
            ["carol", "alice", "bob"],
            {"carol": Decimal("33.34"), "alice": Decimal("33.33"), "bob": Decimal("33.33")},
        ),
        (Decimal("12.34"), ["bob"], {"bob": Decimal("12.34")}),
        (
            Decimal("9999999999.99"),
            ["alice", "bob"],
            {"alice": Decimal("5000000000.00"), "bob": Decimal("4999999999.99")},
        ),
    ],
)
def test_split_equal_preserves_money_and_member_order(amount, members, expected):
    shares = split_equal(amount, members)

    assert shares == expected
    assert list(shares) == members
    assert all(isinstance(share, Decimal) for share in shares.values())
    assert sum(shares.values(), Decimal("0.00")) == amount


@pytest.mark.parametrize(
    "amount",
    [
        Decimal("0"),
        Decimal("-1.00"),
        Decimal("10.005"),
        Decimal("10.000"),
        Decimal("NaN"),
        Decimal("sNaN"),
        Decimal("Infinity"),
        Decimal("-Infinity"),
        Decimal("10000000000.00"),
    ],
)
def test_split_equal_rejects_invalid_amounts(amount):
    with pytest.raises(ValueError):
        split_equal(amount, ["alice", "bob"])


@pytest.mark.parametrize("amount", [100, 100.0, "100.00"])
def test_split_equal_requires_decimal_input_in_baht(amount):
    with pytest.raises(TypeError):
        split_equal(amount, ["alice", "bob"])


@pytest.mark.parametrize("members", [[], ["alice", "alice"]])
def test_split_equal_requires_nonempty_unique_members(members):
    with pytest.raises(ValueError):
        split_equal(Decimal("100.00"), members)


def test_split_equal_keeps_money_exact_when_caller_changes_decimal_precision():
    with localcontext() as context:
        context.prec = 2
        shares = split_equal(Decimal("1.23"), ["alice", "bob"])
        assert context.prec == 2

    assert shares == {"alice": Decimal("0.62"), "bob": Decimal("0.61")}
