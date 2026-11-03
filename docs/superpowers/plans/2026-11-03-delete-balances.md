# Deletion and Balances Implementation Plan

> **For agentic workers:** Use the existing authorized workflow: root integrates production changes, independent agents write focused tests and review the result. Steps use checkbox syntax for tracking.

**Goal:** Complete payer-only soft deletion and exact zero-sum member balances.

**Architecture:** Extend the current expense service/repository for deletion. Add focused balance routing/service/repository modules; aggregate active payer credits and share debits in one PostgreSQL statement.

**Tech Stack:** Python 3.12+, FastAPI, SQLAlchemy, PostgreSQL 16, pytest, Ruff.

**Spec:** [Design](../specs/2026-11-03-delete-balances-design.md), the user-supplied SplitBill brief and current API contract.

This is the local pre-publication checkpoint. Later push, CI, merge/sync and fresh-clone evidence is recorded in the milestone PR and external handoff against the actual delivered SHA.

## Global constraints

- No monetary floats; output monetary values as strings with exactly two decimal places.
- Group access remains 404 for inaccessible/missing groups; preserve the existing error envelope.
- Preserve user-owned `.env.example` changes and do not commit credentials.
- Work on `dev/backend`; retain incremental commits and the three long-lived branches.
- No migration is needed because the deletion flag and immutable shares already exist.

## Review focus

- An expense ID belonging to another group must not be deleted or disclosed.
- Creator and payer can differ; only the payer may delete even when absent from the split.
- A deleted record must retain its shares/key and must not be recreated by replay.
- Balance aggregation must not multiply payer credits by share count or lose inactive members' zero values.
- Aggregate balances may exceed a single NUMERIC(12,2) amount and must remain exact under concurrent deletion.

## Task 1: payer-only soft delete

Files: `backend/tests/test_expenses_delete.py`, `backend/splitbill/expense_repository.py`, `backend/splitbill/expenses.py`, `backend/splitbill/expenses_api.py`, generated `docs/openapi.json`.

Interfaces: `get_group_expense(session, group_id: int, expense_id: int) -> Expense | None`; `delete_expense(session, group_id: int, expense_id: int, username: str) -> None`.

- [x] Write PostgreSQL tests for 204 empty success/retry, 403 nonpayer, 401 authentication, 404 scope, retained rows/shares/key, replay, listing exclusion, and failed-commit rollback.
- [x] Run new tests and observe missing DELETE failures before adding production behavior: 16 new failures, existing 115 passed.
- [x] Implement group authorization, scoped lookup including deleted records, payer check, flag update and commit; add route with explicit 204 Response.
- [x] Run deletion tests and existing applicable tests: 131 passed with the not-yet-implemented independent balances file excluded; Ruff and OpenAPI consistency passed. Independent DELETE review found no material defect.
- [x] Commit the coherent DELETE feature without the independent balance test file: `83f08f1`.

## Task 2: exact member balances

Files: `backend/tests/test_balances.py`, new `backend/splitbill/balance_repository.py`, `backend/splitbill/balances.py`, `backend/splitbill/balances_api.py`, `backend/splitbill/app.py` and generated OpenAPI.

Interfaces: `balances_for_group(session, group_id: int) -> dict[str, Decimal]`; `read_balances(session, group_id: int, username: str) -> dict[str, str]`.

- [x] Write 20 tests with literal expected values for empty/all-member zeros; 100.00 and 1000.00 equal splits; exact shares; multiple payers; duplicate replay; large totals; authorization/isolation; deletion effects.
- [x] Run balance tests and observe 20 absent-route failures.
- [x] Aggregate active expense credits/debits using UNION ALL, SUM and a member outer join in one statement. Format Decimal output without context-dependent arithmetic.
- [x] Register the balances router and verify the complete PostgreSQL suite: 151 passed with warnings treated as errors. Ruff lint/format (35 files) and OpenAPI consistency passed.
- [ ] Update README/API contract and AI_NOTES with assumptions, examples and actual local evidence; obtain independent code review and commit.

## Task 3: publication and handoff

- [ ] Fetch/integrate latest main, preserve existing work, and check the combined code.
- [ ] Push `dev/backend`; verify the actual remote SHA and open a PR to main.
- [ ] Verify CI for that revision, merge with a merge commit and retain branches.
- [ ] Sync origin/main into both dev branches, push and verify refs/upstreams.
- [ ] Verify the delivered remote revision from a fresh checkout/environment and empty database; record results and limits in an external handoff tied to the actual final SHA.
