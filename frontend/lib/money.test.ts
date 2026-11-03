import assert from "node:assert/strict";
import test from "node:test";
import {
  formatMoney,
  parseAmount,
  parseBalance,
  splitEqual,
  toDecimal,
} from "./money.ts";

test("100.00 split among three preserves every satang and submitted order", () => {
  const shares = splitEqual(parseAmount("100.00")!, ["alice", "bob", "carol"]);
  assert.deepEqual(shares, { alice: 3334n, bob: 3333n, carol: 3333n });
  assert.equal(Object.values(shares).reduce((sum, share) => sum + share, 0n), 10000n);
  // The remainder follows the submitted participants; there is no payer input.
  assert.deepEqual(splitEqual(10000n, ["carol", "alice", "bob"]), {
    carol: 3334n,
    alice: 3333n,
    bob: 3333n,
  });
});

test("a one-satang expense allows zero shares and exact addition stays decimal", () => {
  assert.deepEqual(splitEqual(1n, ["alice", "bob", "carol"]), {
    alice: 1n,
    bob: 0n,
    carol: 0n,
  });
  assert.equal(toDecimal(parseAmount("0.10")! + parseAmount("0.20")!), "0.30");
  assert.equal(parseAmount("0"), 0n);
  assert.equal(parseAmount("0.00"), 0n);
  assert.equal(toDecimal(0n), "0.00");
  assert.equal(toDecimal(-1n), "-0.01");
});

test("amount inputs enforce the API format, precision, length and range", () => {
  assert.equal(parseAmount("100"), 10000n);
  assert.equal(parseAmount("100.5"), 10050n);
  assert.equal(parseAmount("0001.23"), 123n);
  assert.equal(parseAmount("9999999999.99"), 999999999999n);
  assert.equal(parseAmount("0".repeat(64)), 0n);
  for (const value of [
    "", "-1.00", "+1", "1e2", "1,000.00", "1.001", "1.", ".50",
    " 1", "1 ", "1\n", "1\r", "1\u2028", "NaN", "Infinity", "๑๐.๐๐",
    "10000000000.00", "0".repeat(65),
  ]) {
    assert.equal(parseAmount(value), null, value);
  }
});

test("signed aggregate balances stay exact beyond Number and bill limits", () => {
  const value = "-90071992547409931234567890.12";
  assert.equal(parseBalance(value), -9007199254740993123456789012n);
  assert.equal(toDecimal(parseBalance(value)!), value);
  assert.equal(formatMoney(value), "-90,071,992,547,409,931,234,567,890.12");
  assert.equal(formatMoney("1000.00"), "1,000.00");
  assert.equal(formatMoney(1n), "0.01");
  assert.equal(formatMoney("-0.00"), "0.00");
  for (const invalid of ["1", "1.0", "1.001", "+1.00", "1.00\n", "bad"]) {
    assert.equal(parseBalance(invalid), null);
    assert.equal(formatMoney(invalid), "—");
  }
});

test("invalid splits reject empty/duplicate members and invalid bill totals", () => {
  assert.throws(() => splitEqual(1n, []), RangeError);
  assert.throws(() => splitEqual(1n, ["alice", "alice"]), RangeError);
  assert.throws(() => splitEqual(1n, [""]), RangeError);
  assert.throws(() => splitEqual(0n, ["alice"]), RangeError);
  assert.throws(() => splitEqual(-1n, ["alice"]), RangeError);
  assert.throws(() => splitEqual(1000000000000n, ["alice"]), RangeError);
  assert.deepEqual(splitEqual(1n, ["__proto__"]), { ["__proto__"]: 1n });
});
