import test from "node:test";
import assert from "node:assert/strict";
import { decodePending } from "./pending.ts";

test("an unresolved intent retains its original identity and exact request across reload", () => {
  const intent = {
    key: "frozen-key",
    user: "alice",
    group: 1,
    body: {
      description: "มื้อเย็น",
      paid_by: "bob",
      amount: "100.00",
      split: { type: "equal", members: ["alice", "bob", "carol"] },
    },
  };
  assert.deepEqual(decodePending(JSON.stringify(intent)), intent);
  assert.equal(decodePending("not json"), null);
  assert.equal(
    decodePending(JSON.stringify({ ...intent, user: "unknown" })),
    null,
  );
  assert.equal(
    decodePending(
      JSON.stringify({ ...intent, body: { ...intent.body, amount: "10.005" } }),
    ),
    null,
  );
  assert.equal(
    decodePending(
      JSON.stringify({
        ...intent,
        body: {
          ...intent.body,
          split: { type: "exact", shares: { alice: "99.99" } },
        },
      }),
    ),
    null,
  );
  assert.ok(
    decodePending(
      JSON.stringify({
        ...intent,
        body: {
          ...intent.body,
          amount: "0.30",
          split: {
            type: "exact",
            shares: { alice: "0.10", bob: "0.20", carol: "0.00" },
          },
        },
      }),
    ),
  );
});
