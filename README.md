# SplitBill

SplitBill is a shared-expense take-home project. The backend implements group access, exact expense allocation, idempotent creation, payer-only soft deletion, and zero-sum member balances, with a reproducible handoff for frontend development.

## Current scope

The backend contains PostgreSQL migrations, repeatable seed data, and all six required API endpoints:

| Endpoint | Status |
| --- | --- |
| `GET /groups` | Baseline |
| `GET /groups/{group_id}` | Baseline |
| `POST /groups/{group_id}/expenses` | Implemented; local checks passed |
| `GET /groups/{group_id}/expenses` | Implemented; local checks passed |
| `DELETE /groups/{group_id}/expenses/{expense_id}` | Implemented; payer-only soft deletion |
| `GET /groups/{group_id}/balances` | Implemented; exact paid-minus-owed member totals |
| Next.js frontend | Not implemented |

An existing group that the requester cannot access returns `404`, using the same response as an unknown group. This avoids disclosing group existence. `X-User` selects one of the seeded users; it is an assessment convention, not full authentication.

See [the API contract](docs/api-contract.md) for requests, responses and errors, and [the Git workflow](docs/git-workflow.md) for milestone and handoff rules. The generated [OpenAPI schema](docs/openapi.json) describes implemented endpoints only.

## Requirements

- Python 3.12 or later; use a matching interpreter when creating the virtual environment.
- A running PostgreSQL 16 server, with separate application and test databases.
- Git. Node.js is not required for this backend milestone.

If databases do not exist, connect as a local PostgreSQL administrator and create them. The following credentials are local placeholders; choose a password and put the same value in your untracked `.env`:

```sql
CREATE ROLE splitbill LOGIN PASSWORD 'replace-with-local-password';
CREATE DATABASE splitbill OWNER splitbill;
CREATE DATABASE splitbill_test OWNER splitbill;
```

## Fresh-clone setup

Run from the repository root:

```sh
cp .env.example .env
python3.12 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.lock
backend/.venv/bin/python -m pip install --no-deps -e './backend[dev]'
```

An installed Python 3.13 or newer can replace `python3.12`. Edit `.env` so `DATABASE_URL` and `TEST_DATABASE_URL` match your PostgreSQL credentials. Settings read the root `.env`; environment variables take precedence.

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Application database, using `postgresql+psycopg://` |
| `TEST_DATABASE_URL` | Dedicated PostgreSQL 16 test database |
| `CORS_ORIGINS` | Allowed frontend origins; default example is `http://localhost:3000` |

Apply migrations, seed, and start the API:

```sh
cd backend
.venv/bin/alembic upgrade head
.venv/bin/python -m splitbill.seed
.venv/bin/uvicorn splitbill.app:app --reload
```

Seed users are `alice`, `bob`, `carol`, and `dan`. Group `1`, **Chiang Mai trip**, contains alice/bob/carol; group `2`, **Office lunch**, contains bob/dan. Re-running the seed command must retain this baseline without duplicate memberships.

The API is available at `http://127.0.0.1:8000`; interactive documentation is at `/docs` and the live schema at `/openapi.json`.

```sh
curl -i -H 'X-User: alice' http://127.0.0.1:8000/groups
curl -i -H 'X-User: alice' http://127.0.0.1:8000/groups/1
curl -i -H 'X-User: alice' http://127.0.0.1:8000/groups/2
```

The last request is expected to return `404`. Missing or unknown `X-User` values are expected to return `401`.

## Checks

From the repository root, set `TEST_DATABASE_URL` to your dedicated test database and run the suite with one command:

```sh
export TEST_DATABASE_URL='postgresql+psycopg://splitbill:replace-with-local-password@localhost:5432/splitbill_test'
bash scripts/test-backend.sh
```

The integration fixtures use isolated randomly named schemas in that database. The test database role needs permission to create and drop its schemas. Do not point this command at the application database.

Run lint, formatting, and the generated-schema consistency check:

```sh
bash scripts/check-backend.sh
```

To regenerate OpenAPI after an implemented API change:

```sh
cd backend
.venv/bin/python -m splitbill.openapi
```

Commands in this document describe how to check the backend. Commit-specific local, CI, merge/sync and fresh-clone evidence belongs in the milestone PR/handoff. This README does not substitute for that evidence or pin moving branch heads.

The historical baseline implementation run on Python **3.13.7** and PostgreSQL **16.13** passed **19 baseline tests without warnings**, Ruff lint and formatting checks, the implemented OpenAPI snapshot check, and `pip check`. Against an isolated application database, the real Alembic CLI also passed upgrade, schema-drift check, downgrade to base, upgrade again, and two seed runs. These baseline results do not certify the new expense work. Record B1a checks, fresh-clone results, remote CI, and push/merge evidence separately against the delivered SHA.

## B1a: expense creation and listing

Expense creation implements equal/exact allocation and group-scoped concurrent idempotency. Listing returns active expenses in deterministic newest-first order. The final local PostgreSQL 16 suite passed **115 tests**: 23 money, 19 baseline, one expense-migration, 59 POST, and 13 GET cases. Coverage includes overlapping requests using two database backend PIDs, forced-write-failure rollback, timestamp ordering/ties, group isolation, and retained deleted rows. Ruff lint/format checks over 30 files and the generated OpenAPI consistency check also passed. [The expense plan](docs/superpowers/plans/2026-11-02-expenses.md) records the checkpoints and Git handoff.

A real Uvicorn HTTP check returned `201` for the `1000.00` equal split with shares `333.34/333.33/333.33`, `200` with the unchanged original for a changed-payload replay, and `201` for an exact `0.30` split into `0.10/0.20`. GET returned the newest expense first; unauthorized group access returned `404` and an incorrect exact total returned `422`. The expense migration upgrade, Alembic no-drift check, and seed command also passed locally. Creation/listing were subsequently delivered through [PR #1](https://github.com/WajanaPiromnok/split-bill/pull/1); release evidence is recorded separately against its delivered SHA.

The implemented creation path uses strict API strings, Python `Decimal`, and PostgreSQL `NUMERIC(12,2)`. Plain ASCII digits with zero, one, or two fractional digits are accepted, then output is normalized to two places. Money input strings are limited to 64 characters. Bill amounts must be positive and at most `9999999999.99`; exact shares may be zero. Input precision is checked before rounding or storage.

The requesting user, payer, and participants must all be group members, but the requester may record an expense paid by someone else, and the payer need not be included in the split. Equal splits preserve submitted member order when distributing remaining satang; the service checks that exact shares sum to the bill before saving them atomically. This is not a claim of a database-enforced cross-row aggregate constraint.

The replay policy returns the original expense for a repeated key, including a changed request that passes framework validation. Authorization precedes key lookup; an existing key is resolved before new-expense business validation. Malformed JSON and invalid request shapes still fail with `422`. See the contract for full request, response, and error details.

## Deletion and balances

DELETE retains the expense, shares and key, returns an empty 204 for the payer (including repeated deletion), and returns 403 for another group member, including after deletion. Inaccessible groups remain 404; a missing expense or ID from another group is 404. The creator and payer may differ; the `paid_by` user owns deletion permission and need not participate in the split. The empty/repeated 204 behavior is an implementation choice where the brief is silent.

GET balances returns a direct mapping such as `{"alice":"666.66","bob":"-333.33","carol":"-333.33"}` for the 1000.00 example. This response shape is a documented interpretation of the brief. Every member appears alphabetically, including untouched members with `0.00`. A positive balance is money owed to the member; calculate paid minus allocated share, excluding deleted expenses.

Credits and debits are combined with UNION ALL and aggregated in one PostgreSQL statement, giving a consistent snapshot during concurrent creation/deletion. Totals remain exact NUMERIC values, can exceed one bill's NUMERIC(12,2) range, and are formatted as two-decimal strings. No cached balance rows or new migration are needed.

The six required backend test cases are covered by the full suite. The added DELETE cases check permissions, retained records/replay and failure rollback; balance cases check all-member zeros, both equal-split examples, exact/multiple-payer calculations, cross-group isolation, replay, deletion effects and aggregate limits. See the [implementation plan](docs/superpowers/plans/2026-11-03-delete-balances.md) and milestone handoff for actual verification results.

At the local completion checkpoint, the full PostgreSQL 16 suite passed **151 tests with warnings treated as errors** (115 existing, 16 DELETE, 20 balances). Ruff lint/format over 35 Python files and generated OpenAPI consistency also passed. These local results are distinct from remote CI and delivery evidence.

## Remaining assessment scope

The Next.js frontend and real browser-to-API integration remain to be implemented. Its arithmetic and previews must match the backend without binary floating-point errors.

Full authentication, optional settlement/payment endpoints, and visual polish are outside this backend scope. [AI_NOTES.md](AI_NOTES.md) records AI assistance, detected errors, and corrections. The historical baseline implementation/review estimate was **about 30–45 minutes**, excluding earlier prompt drafting; it does not include the later expense, deletion and balance milestones and is not a precise time log.

The repository remains private. Reading GitHub rulesets returned `403` because of the private-repository plan limitation. The workflow policy and CI configuration are present; server-enforced branch protection is not claimed. Remote CI evidence is attached to each delivered revision. Repository visibility was not changed to work around the limitation.

## Handoff identity

Record the exact remote baseline SHA after pushing. Do not write a commit's own SHA into a tracked file and commit it again, because that creates a different SHA.

```sh
git rev-parse HEAD
git ls-remote --heads origin main dev/backend dev/frontend
```

Frontend work can consume the APIs available in the verified delivered `main` revision. Use its exact SHA and matching OpenAPI snapshot for integration checks.
