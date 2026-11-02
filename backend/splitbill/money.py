from decimal import Context, Decimal, localcontext

MAX_AMOUNT = Decimal("9999999999.99")


def split_equal(
    amount: Decimal,
    members: list[str],
) -> dict[str, Decimal]:
    if not isinstance(amount, Decimal):
        raise TypeError("amount must be a Decimal in baht")
    if not amount.is_finite() or amount <= 0:
        raise ValueError("amount must be finite and greater than zero")
    if amount.as_tuple().exponent < -2:
        raise ValueError("amount must have at most two decimal places")
    if amount > MAX_AMOUNT:
        raise ValueError("amount exceeds the NUMERIC(12,2) database range")
    if not members:
        raise ValueError("members must not be empty")
    if len(set(members)) != len(members):
        raise ValueError("members must not contain duplicates")

    # Isolate money arithmetic from any Decimal settings changed by the caller.
    with localcontext(Context(prec=28)):
        # Work in whole satang so dividing cannot lose a fraction of a satang.
        amount_in_satang = amount * 100
        total_in_satang = int(amount_in_satang)

        member_count = len(members)
        base_share = total_in_satang // member_count
        remainder = total_in_satang % member_count

        shares: dict[str, Decimal] = {}
        for index, member in enumerate(members):
            member_satang = base_share
            if index < remainder:
                member_satang += 1

            shares[member] = (Decimal(member_satang) / 100).quantize(Decimal("0.01"))

        return shares
