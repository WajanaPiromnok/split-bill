# SplitBill

SplitBill is a shared-expense take-home project with a Thai responsive Next.js interface and a FastAPI/PostgreSQL backend. It supports exact expense allocation, safe creation retries, payer-only soft deletion, and zero-sum member balances.

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
| Next.js frontend | Implemented: user/groups, equal/exact previews, creation/retry, list, balances, payer deletion |

An existing group that the requester cannot access returns `404`, using the same response as an unknown group. This avoids disclosing group existence. `X-User` selects one of the seeded users; it is an assessment convention, not full authentication.

See [the API contract](docs/api-contract.md) for requests, responses and errors, and [the Git workflow](docs/git-workflow.md) for milestone and handoff rules. The generated [OpenAPI schema](docs/openapi.json) describes implemented endpoints only.

## System stack

The [architecture guide](docs/architecture/README.md) explains the stack. Its diagram is the historical backend-milestone snapshot, when the frontend was still planned. The implemented Next.js / TypeScript / Tailwind CSS browser UI calls FastAPI directly over HTTP/JSON. PostgreSQL stores the application data; a separate database supports integration tests. Hosting has not been selected.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/architecture/stack-dark.png">
  <img alt="SplitBill stack: planned frontend, implemented FastAPI backend, PostgreSQL, setup tools and GitHub Actions checks" src="docs/architecture/stack.png">
</picture>

[Open the self-contained HTML](docs/architecture/stack.html) · [Light PNG](docs/architecture/stack.png) · [Dark PNG](docs/architecture/stack-dark.png)

## Requirements

- Python 3.12 or later; use a matching interpreter when creating the virtual environment.
- A running PostgreSQL 16 server, with separate application and test databases.
- Node.js 24 LTS or a supported newer version (24–26), npm, and Git. Python/PostgreSQL alone are sufficient when working only on the backend.

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

Frontend setup and browser integration checks are documented below. The following checks cover the backend.

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

## Frontend

Start the backend using the commands above. In a second terminal, from the repository root:

```sh
cd frontend
cp .env.example .env.local
npm ci
npm run dev
```

Open **http://localhost:3000**. The default public API URL is `http://127.0.0.1:8000`; change `NEXT_PUBLIC_API_URL` in `frontend/.env.local` if needed, then restart Next. The backend's `CORS_ORIGINS` must include the browser origin (the default is `http://localhost:3000`). Database URLs and passwords belong only in the ignored root `.env`, never in frontend configuration.

The first screen asks “คุณคือใคร?”. Click alice, bob, carol, or dan to enter directly, then choose an accessible group. The workspace header shows the current name and “เปลี่ยนผู้ใช้” to return to the chooser. Profile selection is remembered across reload in the same tab; a restored unresolved expense takes precedence and restores its original user and group. This is the assessment's `X-User` profile selection, not account login or server-side logout.

Changing users asks for confirmation before discarding an edited draft. Cancelling keeps the draft. The change action is unavailable during create/delete requests and while a creation result is uncertain, so exiting cannot discard a pending expense. Leaving a profile clears its visible workspace state, not its stored expenses.

Add a description and amount, select the payer and participants, and inspect the allocation before saving. Exact mode displays the unallocated/over-allocated amount and blocks submission until all shares sum to the bill. Expense details show stored shares; only the payer sees the delete action. Balances label money owed to a member, money the member owes, or zero net balance; no transfer/payment capability is implied.

Amounts stay decimal strings at the API boundary. The frontend parses them into `BigInt` integer satang, divides with quotient/remainder in visible member order, and formats integer digits with two decimal places. No money passes through `Number`, `parseFloat`, or binary floating-point multiplication. Exact shares may be zero; signed aggregate balances are formatted without the single-expense limit. Thus `0.10 + 0.20` stays `0.30`, and `100.00 / 3` becomes `33.34 / 33.33 / 33.33` independently of who paid.

One frozen submission body and key are retained in tab-local session storage before POST. A lost/uncertain response offers retry of that same intent, including after reload, and blocks another bill until it resolves. Successful creation or replay resets the form; deleted replays remain deleted. Failed validation preserves editable values. Data is refreshed from the server after mutations; a refresh failure is distinct from a failed write. Requests from an old user/group and superseded refreshes cannot replace newer data.

The app uses native form controls, React state, and fetch. Tailwind 4 provides theme tokens/preflight with semantic component CSS. Noto Sans Thai is self-hosted under its bundled OFL license; the browser/build does not fetch Google Fonts. The supported Webpack compiler is selected explicitly because Turbopack's CSS worker could not bind its local port in the development environment. No form/state/query library, settlement API, custom select, or extra route is added.

For a production build, set the intended API URL **before building** because Next inlines public environment values:

```sh
cd frontend
npm run lint
npm run typecheck
npm test
npm run build
npm start
```

The [approved design](DESIGN.md), [implementation plan](docs/frontend-plan.md), and [design references/screenshots](design-system/README.md) record the design choices and source limitations. The examples below are actual application screenshots captured against a disposable PostgreSQL test schema; they are not Stitch exports or production transaction data.

![SplitBill desktop interface](design-system/frontend-desktop.png)

[Mobile screenshot](design-system/frontend-mobile.png)

## Real browser/API/PostgreSQL checks

Use the backend environment plus separately installed browser test tooling (not backend runtime dependencies):

```sh
backend/.venv/bin/python -m pip install playwright==1.64.1
backend/.venv/bin/python -m playwright install chromium
backend/.venv/bin/python scripts/test-frontend-integration.py
```

The runner reads `TEST_DATABASE_URL` from the environment or ignored root `.env`, requires PostgreSQL 16 and a separate test database, creates a randomly named schema, migrates/seeds it, builds Next for test API port 8059, and starts its own API8059/frontend3001. It drops only that schema and stops its own processes on completion. Keep those two ports free. It never seeds or deletes application data. Port overrides are available with `--api-port` and `--web-port`.

The checks exercise real group access, ordered equal splits, exact totals/zero shares, creation/list/balances, payer deletion, authorization, and zero-sum totals. Failure simulations delay real responses or discard one response after the real backend commits; they do not replace the API or database with fake success data. They verify frozen-key retry across reload and protection against old responses. Responsive screenshots are written to `design-system`; failed browser checks leave diagnostic evidence in a temporary directory. The [frontend CI workflow](.github/workflows/frontend.yml) runs lint/type/native tests, production build and these browser checks with PostgreSQL 16.

At the profile-entry local checkpoint, ESLint, TypeScript, six native Node tests, the production Webpack build, and all 13 Chromium/FastAPI/PostgreSQL 16 acceptance groups passed. Added coverage includes first-entry and keyboard selection, same-tab reload and fresh-tab behavior, draft cancellation/confirmation, pending-owner restoration, blocked exit during writes, and profile-storage failure after a real committed POST. These are local results; remote CI and delivered SHA are recorded separately.

The runner's build points to its temporary API port. Rebuild with your normal API configuration before using `npm start` afterward; `npm run dev` reads your normal environment independently. Commit-specific local/remote check results belong in the delivery record, not an assertion inferred from this workflow file.

## Remaining scope

Deployment/hosting, production authentication, and optional settlement/payment endpoints remain outside this assessment implementation. The current UI is the single-page assessment workflow; it does not create users or groups or edit expenses.

Full authentication, optional settlement/payment endpoints, and visual polish are outside this backend scope. [AI_NOTES.md](AI_NOTES.md) records AI assistance, detected errors, and corrections. The historical baseline implementation/review estimate was **about 30–45 minutes**, excluding earlier prompt drafting; it does not include the later expense, deletion and balance milestones and is not a precise time log.

The repository remains private. Reading GitHub rulesets returned `403` because of the private-repository plan limitation. The workflow policy and CI configuration are present; server-enforced branch protection is not claimed. Remote CI evidence is attached to each delivered revision. Repository visibility was not changed to work around the limitation.

## Handoff identity

Record the exact remote baseline SHA after pushing. Do not write a commit's own SHA into a tracked file and commit it again, because that creates a different SHA.

```sh
git rev-parse HEAD
git ls-remote --heads origin main dev/backend dev/frontend
```

Frontend work can consume the APIs available in the verified delivered `main` revision. Use its exact SHA and matching OpenAPI snapshot for integration checks.
