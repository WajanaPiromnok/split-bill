# Backend baseline API contract

This contract distinguishes the baseline group APIs from expense features that are still planned. Use the baseline SHA from the handoff to select matching code and `docs/openapi.json`.

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

## Planned expense contract: not yet available

The following endpoints are required later and are not implemented by this baseline:

| Method and path | Required behavior |
| --- | --- |
| `POST /groups/{group_id}/expenses` | Record one immutable shared expense |
| `GET /groups/{group_id}/expenses` | List expenses in reverse chronological order |
| `DELETE /groups/{group_id}/expenses/{expense_id}` | Payer-only soft deletion |
| `GET /groups/{group_id}/balances` | Per-member net balances; positive means money owed to that member |

The PDF's create-request example is the starting contract:

```http
POST /groups/1/expenses
X-User: alice
Idempotency-Key: 7f3c2a10-dinner-0001
Content-Type: application/json
```

```json
{
  "description": "Dinner at the night market",
  "paid_by": "alice",
  "amount": "1000.00",
  "split": {"type":"equal","members":["alice","bob","carol"]}
}
```

Expected monetary facts are shares `333.34`, `333.33`, `333.33`, and balances `+666.66`, `-333.33`, `-333.33` for alice/bob/carol respectively. These are expected values, not a claim that an expense response currently exists.

An exact split uses:

```json
{"type":"exact","shares":{"alice":"500.00","bob":"300.00","carol":"200.00"}}
```

Implementation requirements for backend B1/B2:

- Money crosses the API as decimal strings. Reject invalid precision before rounding; use Python `Decimal` and database `NUMERIC(12,2)`.
- Preserve the submitted equal-split member order when distributing remaining satang.
- A positive `0.01` expense split three ways can allocate `0.01`, `0.00`, `0.00`; do not accidentally reject an equal-split zero share as a zero expense.
- Payer and split members must belong to the group. Group authorization must be checked before an idempotent response is returned.
- Treat `Idempotency-Key` as group-scoped. Same-key retries return the original expense and do not create duplicates, including concurrent requests.
- Persist the expense and its complete shares atomically. Uniqueness must continue covering soft-deleted expenses.
- Deletion retains the record and excludes it from balances; only the payer can delete it. The expense must belong to the group in the URL.
- Derive balances from active expenses and verify each member's value as well as the zero-sum total.

Before B1, freeze the expense/list/balance response shapes and corresponding success/error examples in the contract and tests. Document decisions about changed-payload retries, replay after deletion, zero/negative exact shares, duplicate/empty split members, and ordering ties. The PDF does not state that `X-User` must equal `paid_by`.

Frontend F1 may consume the real group APIs now. F2 may use explicitly identified mocks during development, but must pass against the B1 API on `main` before its integration PR is accepted. A retry of the same submission must retain its key; a new submission must get a new key.
