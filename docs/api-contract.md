# SplitBill API contract

The group endpoints and expense creation are implemented. Expense creation has passed its local POST checks; expense listing remains the **B1a target contract** and is not yet verified. This document does not claim a final B1a handoff, remote CI result, or frontend integration. Use the handoff SHA to select matching code and `docs/openapi.json`.

## Baseline HTTP conventions

- Local API origin: `http://127.0.0.1:8000`.
- Requests select a seeded user through `X-User`.
- Full authentication is outside the assessment scope.
- JSON errors use an `error` object with `code` and `message`; validation errors also include `details`.
- CORS permits the origins configured in `CORS_ORIGINS`, including the example frontend origin `http://localhost:3000`.

### GET /groups

Request:

```http
GET /groups
X-User: alice
```

Expected `200` body:

```json
[{"id":1,"name":"Chiang Mai trip"}]
```

For bob, the list contains groups 1 and 2. Carol can see group 1; dan can see group 2. A list response contains only groups belonging to the selected user.

### GET /groups/{group_id}

Request:

```http
GET /groups/1
X-User: alice
```

Expected `200` body:

```json
{"id":1,"name":"Chiang Mai trip","members":["alice","bob","carol"]}
```

For an unknown group or a group the requester cannot access, return `404`:

```json
{"error":{"code":"group_not_found","message":"Group not found"}}
```

An absent or unknown `X-User` returns `401`:

```json
{"error":{"code":"unauthenticated","message":"A valid X-User header is required"}}
```

An invalid path value such as `/groups/not-an-integer` returns `422` in the same envelope, with code `validation_error` and validation `details`. See the generated schema and implementation tests for that detail structure.

## Implemented: POST /groups/{group_id}/expenses

Required headers:

```http
X-User: alice
Idempotency-Key: 7f3c2a10-dinner-0001
Content-Type: application/json
```

`Idempotency-Key` must contain 1–200 characters and must not be whitespace-only. It is an opaque key scoped to the group, not a UUID requirement. A new expense uses a new key; retries of the same submission retain its key.

Equal-split example from the PDF:

```json
{
  "description": "Dinner at the night market",
  "paid_by": "alice",
  "amount": "1000.00",
  "split": {"type":"equal","members":["alice","bob","carol"]}
}
```

Input contract:

| Field | New-expense rule |
| --- | --- |
| `description` | String trimmed at both ends; nonblank and at most 500 characters after trimming |
| `paid_by` | Strict username string of 1–64 characters belonging to a group member; may differ from `X-User` and need not participate in the split |
| `amount` | Strict string of at most 64 characters containing ASCII digits with an optional decimal point followed by one or two digits; positive and no greater than `9999999999.99` |
| `split.type` | Exactly `equal` or `exact` |
| Equal `split.members` | Nonempty, ordered, unique group usernames; each name is a strict string of 1–64 characters |
| Exact `split.shares` | Nonempty map of group usernames to strict money strings of at most 64 characters; names are 1–64 characters, each share is nonnegative, and the total equals `amount` exactly |

Unknown fields are rejected, including extra fields inside the selected split shape. Money accepts strings such as `"100"`, `"100.0"`, and `"100.00"`. JSON numbers, signs, surrounding spaces, exponent notation, nonfinite values, non-ASCII digits, and more than two fractional digits are rejected. Input is validated before rounding or storage; output always has two decimal places.

An exact split replaces the `split` object with:

```json
{"type":"exact","shares":{"alice":"500.00","bob":"300.00","carol":"200.00"}}
```

Equal allocation distributes remaining satang one at a time in submitted member order. Thus `"100.00"` for alice/bob/carol gives `"33.34"`, `"33.33"`, `"33.33"`. `"0.01"` gives `"0.01"`, `"0.00"`, `"0.00"`; zero shares are valid even though the bill itself must be positive.

### Response

A new expense returns `201`. A replay returns `200` with the original expense. Illustrative body; identifiers and timestamps are assigned by the server:

```json
{
  "id": 1,
  "group_id": 1,
  "description": "Dinner at the night market",
  "paid_by": "alice",
  "amount": "1000.00",
  "split_type": "equal",
  "shares": {"alice":"333.34","bob":"333.33","carol":"333.33"},
  "created_at": "2026-11-02T03:00:00Z",
  "deleted": false
}
```

`shares` preserves the stored allocation order. `created_at` is a UTC ISO timestamp. Replaying an expense preserves its identity, creation time, payer, description, amount, split type, and allocated shares.

### Authorization, validation, and replay order

1. The framework rejects malformed JSON and invalid request shapes with `422`; an idempotency key cannot bypass request parsing or schema validation. Required headers/body fields, string types/lengths, nonblank description, nonempty split collections, and extra-field rejection still apply to a replay.
2. A valid user must belong to the group before any idempotency lookup. Missing/unknown user is `401`; missing/inaccessible group is `404`.
3. An existing key in that group returns the original expense before new-expense business validation. A changed request that passes framework validation does not replace the stored expense and does not return `409`.
4. For a new key, validate payer and participants, monetary values, and exact totals. Business-rule violations return descriptive JSON errors with `422`.
5. Persist the expense and all shares atomically.

For example, an existing authorized key can return the original expense despite a changed `amount` of `"10.005"` or a changed payer of `"dan"` in group 1, because those are business validations. A blank description or empty split collection fails schema validation first and cannot use that replay shortcut.

| HTTP status | Error code | Meaning |
| --- | --- | --- |
| `401` | `unauthenticated` | Missing, empty, or unknown `X-User` |
| `404` | `group_not_found` | Unknown or inaccessible group |
| `422` | `validation_error` | Framework JSON/path/header/body validation, including missing key, incorrect types/lengths, empty split collections, or extra fields |
| `422` | `invalid_idempotency_key` | Whitespace-only idempotency key |
| `422` | `invalid_amount` | Money grammar, precision, sign, or range violation |
| `422` | `invalid_payer` | Payer is not a group member |
| `422` | `invalid_split` | Duplicate/nonmember participants or exact shares that do not total the bill |

The same key in another group is independent, subject to that group's access check. Uniqueness is `(group_id, idempotency_key)` and continues covering retained deleted rows. No delete route exists in B1a; keeping a `deleted` flag does not implement soft deletion.

Concurrent requests use a PostgreSQL transaction at READ COMMITTED: insert with `ON CONFLICT DO NOTHING`, then select the winning expense. Only the winning insertion creates shares; a replay cannot observe a committed partial expense. The local POST checks include a real PostgreSQL overlap using two backend PIDs, complete-share verification, and rollback after a forced write failure. They do not certify the still-pending listing route or remote CI.

## B1a target: GET /groups/{group_id}/expenses

```http
GET /groups/1/expenses
X-User: alice
```

Returns `200` with an array of the expense response objects above, or `[]` when the group has none. This endpoint does not require `Idempotency-Key`.

- The requester must belong to the group; user/group errors match the common contract.
- Include only records where `deleted` is false.
- Sort by `created_at` descending, then `id` descending for stable timestamp ties.
- Keep expenses and shares isolated to the requested group; do not expose another group's records.

## Still planned after B1a

| Endpoint | Remaining behavior |
| --- | --- |
| `DELETE /groups/{group_id}/expenses/{expense_id}` | Payer-only soft deletion, retaining the record and excluding it from balances |
| `GET /groups/{group_id}/balances` | Per-member net balances with positive meaning money owed to that member; exact zero-sum total |

For the dinner example, eventual balances are `+666.66`, `-333.33`, `-333.33` for alice/bob/carol. These values explain the assessment's sign convention; this milestone does not provide a balances response.

Frontend F1 can consume the group APIs. Expense integration must use a verified B1a handoff SHA and the corresponding generated schema. Mocked development checks must be identified and cannot serve as final real-API integration evidence.
