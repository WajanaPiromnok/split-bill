# AI assistance notes

This file records assistance actually used during the backend-baseline work. It does not certify unrun checks or full completion of the take-home assessment.

## Tools and contributions

- OpenAI Codex: repository and environment inspection, backend-baseline implementation, test/tooling preparation, and Git-workflow execution.
- Codex subagents: read-only baseline-readiness inspection, independent schema/tooling review, and drafting `README.md`, this file, the API contract, and Git workflow documentation.
- Human input: the original PDF and the requested three-branch workflow, milestone gates, and evidence requirements.

All generated changes remain the candidate's responsibility. The candidate must understand submitted code and be able to explain and modify it during the interview.

## Prompts used

The user's execution prompt included:

> จัดการ Git workflow ของ SplitBill โดยคงโครงสร้างสาม branch:
> main: ฐานร่วมที่ผ่านการตรวจตาม milestone
> dev/backend: งาน backend
> dev/frontend: งาน frontend

It also required evidence rather than assumed success:

> เริ่มจากตรวจ repository แล้วเสนอขั้นตอนที่ตรงกับสถานะจริง
> ดำเนินงานตาม milestone ที่ได้รับมอบหมายต่อจนเสร็จ
> ห้ามอ้างว่า push, merge หรือ integration สำเร็จโดยไม่มีหลักฐานจากการทำงานจริง

These prompts supplied concrete branch responsibilities and explicit verification requirements. Their outcome is assessed through the baseline checks and remote handoff, not through this note alone.

## Incorrect or unsafe AI output

### Missing Alembic revision template

- AI output: the initial migration environment included the migration setup but omitted `backend/alembic/script.py.mako`.
- Detection: an independent schema review identified that creating the next migration revision would need this missing template. Applying an existing migration alone would not check that workflow.
- Correction: added the standard revision template and a regression test that generates a new revision in a temporary copy of the migration environment.
- Verification: `test_next_developer_can_generate_a_revision` first failed with `FileNotFoundError` for the missing template, then passed after the template was added. The corrected test is included in the passing 19-test local baseline suite. Real Alembic CLI upgrade, drift check, downgrade to base, re-upgrade, and repeat seed checks also passed against an isolated application database.

### Unexpected failures initially escaped the JSON error contract

- AI output: the initial error handling covered known HTTP and validation errors but omitted safe JSON handling of unexpected exceptions.
- Detection: independent review identified the gap; reproducing an unexpected failure returned a non-JSON `500` response that frontend error handling could not consume consistently.
- Correction: added middleware that returns a safe JSON `500` error envelope while preserving CORS behavior for allowed frontend origins.
- Verification: `test_unexpected_failure_returns_safe_json_and_frontend_cors` reproduces the failure path and passes after the correction. The test is part of the passing local baseline suite; this is not a claim of browser integration testing.

### Dependency-freeze command returned an error despite exit status zero

- AI proposal: use `pip freeze --exclude-editable` to generate the lock file before the first Git commit existed.
- Detection: inspecting the command output revealed a `git rev-parse HEAD` failure even though the command exited with status zero. Trusting only that exit status would have missed the failure during editable-project metadata inspection.
- Correction: generate the pinned dependency list with `importlib.metadata`, excluding the editable project itself, instead of relying on that failing freeze path.
- Verification: the root implementation agent generated the dependency list using that method and ran `pip check` successfully. This checks installed dependency consistency; it does not stand in for API or database tests.

## Review before each commit

The required review process is:

1. Inspect the staged diff and confirm it contains only the intended milestone work and no secrets.
2. Compare behavior and assumptions against the PDF and the documented API contract.
3. Run the relevant lint, format, schema-consistency, and tests for the changes being committed.
4. Inspect database and authorization behavior in integration tests; do not substitute mocked results for PostgreSQL evidence.
5. Record actual results and the commit/PR they apply to. Recheck affected behavior after conflict resolution or integration changes.

Commit-specific review evidence belongs in the commit/PR handoff. This process description alone does not claim that every listed review has already happened.

## Local verification record

The implementation agent recorded 19 passing baseline tests without warnings on Python 3.13.7 and PostgreSQL 16.13 after the HTTPX dependency update. Ruff lint/format checks, implemented OpenAPI snapshot consistency, and `pip check` also passed. These are local working-tree results; remote CI, fresh-clone checks, and push/merge results must be recorded separately against the final handoff SHA.

Baseline implementation and review took an estimated 30–45 minutes, excluding the earlier prompt-drafting conversation. This approximate estimate is not a precise time log.

## Equal-split tutoring example (2026-11-02)

The user wrote the starting `100.00 / 3` test and the baht-to-satang conversion while learning. After the explicit request "ลองทำให้ดูเลยก็ได้ครับ", Codex completed `split_equal` and added tests for ordered remainder allocation, small amounts, invalid inputs, and the NUMERIC(12,2) limit. At the end of that lesson the helper was not yet connected to expense API endpoints.

An independent review found that the initial completed helper could lose satang when the caller lowered Decimal precision: `1.23` split between two members returned `0.60, 0.60` at precision 2. A regression test reproduced that failure. The correction isolates arithmetic in `localcontext(Context(prec=28))`; the test then passed and confirms the caller's precision remains unchanged.

Local verification after this change: **42 tests passed**, including 23 money tests and the 19 baseline tests, using the project's temporary PostgreSQL 16 instance. Ruff lint/format and the implemented OpenAPI snapshot check also passed. These local results were recorded before the expense API work; remote CI evidence is reported separately against the delivered commit.

## Expense creation and listing (2026-11-02)

The user requested `POST /groups/{group_id}/expenses` followed by `GET /groups/{group_id}/expenses`. Codex implemented the migration, request/response models, repository, transaction and routes. Separate subagents drafted acceptance tests and documentation; an independent reviewer checked monetary precision, authorization and the concurrent idempotency flow.

The initial migration test failed because the expense tables were absent, and the first POST acceptance test failed with 404 instead of 201. Both were observed before implementing the corresponding behavior. POST is verified with real PostgreSQL 16, including synchronized requests on two distinct backend connections and a forced failure after writing shares to verify full rollback. Exact-share totals use their own Decimal context, following the precision issue found during the earlier tutoring example.

The response contract distinguishes creation (201) from replay (200). Existing keys are checked after group access but before business validation; Pydantic request/header structure is still validated first. The chosen policy returns the original expense for changed valid-shaped payloads and retains keys on deleted rows. No requester/payer equality restriction was added.

Verification and remote delivery results for this milestone are recorded after the GET implementation and CI run; endpoint-specific progress is in the implementation plan. The user's pre-existing `.env.example` edit is excluded from the milestone changes.
