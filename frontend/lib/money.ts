const MAX_AMOUNT = 999_999_999_999n;

/** Parse an API amount into satang; zero is valid for an exact share. */
export function parseAmount(value: string): bigint | null {
  if (
    value.length > 64 ||
    /^[0-9]+(?:\.[0-9]{1,2})?$/.exec(value)?.[0] !== value
  ) {
    return null;
  }
  const [whole, fraction = ""] = value.split(".");
  const satang = BigInt(whole + fraction.padEnd(2, "0"));
  return satang <= MAX_AMOUNT ? satang : null;
}

/** Aggregate balances may be negative and exceed the single-expense limit. */
export function parseBalance(value: string): bigint | null {
  if (
    typeof value !== "string" ||
    /^-?[0-9]+\.[0-9]{2}$/.exec(value)?.[0] !== value
  )
    return null;
  return BigInt(value.replace(".", ""));
}

export function toDecimal(satang: bigint): string {
  const digits = (satang < 0n ? -satang : satang).toString().padStart(3, "0");
  return `${satang < 0n ? "-" : ""}${digits.slice(0, -2)}.${digits.slice(-2)}`;
}

export function formatMoney(value: string | bigint): string {
  const satang = typeof value === "bigint" ? value : parseBalance(value);
  if (satang === null) return "—";
  const [whole, fraction] = toDecimal(satang).split(".");
  return `${whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",")}.${fraction}`;
}

export function splitEqual(
  total: bigint,
  members: string[],
): Record<string, bigint> {
  if (total <= 0n || total > MAX_AMOUNT) {
    throw new RangeError(
      "Expense must be positive and within the amount limit",
    );
  }
  if (
    members.length === 0 ||
    members.some((member) => member.length === 0) ||
    new Set(members).size !== members.length
  ) {
    throw new RangeError("Choose at least one distinct member");
  }
  const count = BigInt(members.length);
  return Object.fromEntries(
    members.map((member, index) => [
      member,
      total / count + (BigInt(index) < total % count ? 1n : 0n),
    ]),
  );
}
