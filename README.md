# SplitBill

SplitBill is a shared-expense take-home project. This first milestone provides a backend baseline and a reproducible handoff for frontend development.

## Current scope

The baseline contains PostgreSQL migrations, repeatable seed data, and two group endpoints with membership checks:

| Endpoint | Status |
| --- | --- |
| `GET /groups` | Baseline |
| `GET /groups/{group_id}` | Baseline |
| Create/list/delete expenses | Planned; not available |
| Balances | Planned; not available |
| Next.js frontend | Not implemented |

An existing group that the requester cannot access returns `404`, using the same response as an unknown group. This avoids disclosing group existence. `X-User` selects one of the seeded users; it is an assessment convention, not full authentication.

See [the API contract](docs/api-contract.md) for examples and [the Git workflow](docs/git-workflow.md) for milestone and handoff rules. The generated [OpenAPI schema](docs/openapi.json) describes implemented endpoints only.

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

Commands in this document describe how to check the baseline. Actual results and the SHA checked belong in the milestone handoff or PR; this README alone is not evidence that a command passed.

The local implementation run on Python **3.13.7** and PostgreSQL **16.13** passed **19 baseline tests without warnings**, Ruff lint and formatting checks, the implemented OpenAPI snapshot check, and `pip check`. Against an isolated application database, the real Alembic CLI also passed upgrade, schema-drift check, downgrade to base, upgrade again, and two seed runs. These results describe the local working tree before the final handoff; they do not claim a fresh-clone check, remote CI result, or successful push. Record those separately against the delivered SHA.

## Remaining assessment scope

Expense allocation, exact monetary validation, zero-sum per-member balances, concurrent idempotency, payer-only soft deletion, and the frontend remain to be implemented. The PDF's six required backend cases are not yet complete: only group-read authorization is covered by the baseline; expense creation, write authorization, monetary cases, retry handling, and deletion cases remain for backend B1/B2.

The planned money representation is API decimal strings, Python `Decimal`, PostgreSQL `NUMERIC(12,2)`, and frontend arithmetic that avoids binary floating-point errors. Input precision must be validated before rounding or storage. These are requirements for later milestones, not claims about expense functionality in this baseline.

Before expense APIs are accepted, document the decisions concerning `X-User` versus `paid_by`, changed-payload retries, retries after deletion, empty/duplicate split members, zero/negative exact shares, and stable expense ordering. The PDF does not state that the creator must be the payer.

Full authentication, optional settlement/payment endpoints, and visual polish are outside this baseline. [AI_NOTES.md](AI_NOTES.md) records AI assistance, detected errors, and corrections. Estimated time for baseline implementation and review is **about 30–45 minutes**, excluding earlier prompt drafting; this is an estimate for the current work, not a precise time log.

The repository remains private. Reading GitHub rulesets returned `403` because of the private-repository plan limitation. The workflow policy and CI configuration are present, but this baseline does not claim server-enforced branch protection or a passing remote CI run. Repository visibility was not changed to work around the limitation.

## Handoff identity

Record the exact remote baseline SHA after pushing. Do not write a commit's own SHA into a tracked file and commit it again, because that creates a different SHA.

```sh
git rev-parse HEAD
git ls-remote --heads origin main dev/backend dev/frontend
```

Frontend F1 can start from that baseline and use the real group APIs. Frontend F2 depends on backend B1 reaching `main` and requires real API integration checks.
