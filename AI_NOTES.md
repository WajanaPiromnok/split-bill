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

The GET contract test was observed failing with 405 before adding the route, then passed. An independent test agent added listing cases with independently controlled timestamps, including an older high-ID expense and newer low-ID expense, group isolation, ordered exact shares and retained soft-deleted rows. The GET implementation fetches shares in bulk and orders active expenses by `created_at DESC, id DESC`.

Final local milestone verification: **115 tests passed** on PostgreSQL 16, including 59 POST cases and 13 GET cases. Ruff lint/format and the generated OpenAPI check passed. Real HTTP checks against Uvicorn confirmed create 201, replay 200 with the original record, exact split creation, newest-first listing, group denial 404 and invalid exact total 422. These are local results; remote CI, merge and final SHA are recorded separately in the milestone handoff.

## Payer-only deletion and balances (2026-11-03)

The user authorized the two remaining backend routes. Codex compared the original brief with the existing model and API contract, documented the unspecified response choices, and implemented deletion. Independent agents wrote real PostgreSQL acceptance tests and reviewed the design and DELETE diff. The user's `.env.example` changes remain excluded.

Before implementing DELETE, a suite run observed **16 new DELETE failures caused by the absent route and 115 existing tests passing**. After implementation all 16 DELETE cases passed, including payer/creator distinction, a payer omitted from the split, retained expense/share/key data, no resurrection on POST replay, cross-group IDs, nonpayer denial even after deletion, and rollback after a forced failure following a real flush. The independent review found no material DELETE defect. The chosen empty 204 response and repeat-204 behavior are assumptions documented in README/API contract, not status codes prescribed by the brief.

The DELETE checkpoint passed **131 tests** (existing 115 plus 16 DELETE), Ruff lint/format and OpenAPI consistency. The separately drafted balances test file was explicitly excluded from this checkpoint because that route had not been implemented; it is not claimed as a passing full milestone suite.

The 20 new balance cases were observed failing against the absent route before implementation. Codex then implemented one-statement PostgreSQL UNION ALL credit/debit aggregation, outer-joined to all group members, and direct two-decimal string serialization. Independent expected values cover the brief's equal splits, exact shares, several payers, deletion, idempotency, group isolation and totals larger than one stored expense's NUMERIC limit. A separate reviewer found no material authorization, transaction, precision or snapshot-consistency defect in the combined code; the review itself did not execute tests.

The first full run passed 151 tests but emitted 18 SQLAlchemy deprecation warnings from an AI-generated `.tuples()` call. The warning identified that Row already behaves like a tuple in the installed SQLAlchemy version. Removing the deprecated conversion retained behavior; the suite was rerun with warnings treated as errors. Ruff also caught an overlong API description, which was shortened before the final checks. These detections and corrections are part of review, not hidden as a pristine first attempt.

Final local completion checkpoint: **151 passed with `-W error`**, no warnings; Ruff lint/format checked 35 files, and the implemented OpenAPI snapshot was current. Remote CI and delivered SHA are reported separately in the PR/handoff. Frontend/browser integration remains outside this milestone.

## Architecture diagram (2026-11-03)

At the user's explicit request, Codex used the local stack-diagram skill to create an offline HTML architecture diagram and derive light/dark PNGs using headless Chromium. A separate agent checked stack/flow accuracy and another drafted the Thai architecture guide. The diagram marks Next.js/TypeScript/Tailwind CSS as planned, keeps Alembic/seed/CI outside runtime traffic, and does not invent a hosting provider or production authentication service.

The first logo download attempt failed because the standalone Python certificate store lacked trusted roots; the correction used the already-installed truststore package with macOS trust rather than disabling TLS verification. Logos were fetched from the skill's approved sources and the official Ruff repository. Alembic reuses its parent SQLAlchemy project's mark, disclosed in NOTICE. Both PNG themes were rendered from the same HTML and visually reviewed for clipping, text/arrow intersections and logo visibility. The template/font licenses and asset-source notices accompany the files. Rendering dependencies were installed in temporary directories, outside application dependencies. No app behavior or credentials were changed.

## Backend simplification (2026-11-03)

The user approved the three ponytail-review recommendations and requested a push to dev/backend. Codex consolidated the GET/balance test request setup into one helper retaining the existing description/status options, flattened the balance aggregate into a direct member outer join with SUM/GROUP BY, and removed the unused B008 lint suppression. No test cases were removed. A separate reviewer compared the remaining test functions at AST level and confirmed their calls/assertions were unchanged; the SQL still uses one statement, exact NUMERIC aggregation, group isolation and zero balances for untouched members.

The complete PostgreSQL 16 suite passed **151 tests with warnings treated as errors** both before and after the refactor. Ruff lint/format over 36 Python files and the unchanged generated OpenAPI snapshot also passed. The change is delivered to the backend branch; remote SHA and CI evidence are reported after the actual push.

## Frontend design and planning (2026-11-03)

The user requested Stitch to establish the design system first, followed by ui-ux-pro-max planning, impeccable quality control, and ponytail implementation constraints. The owner confirmed a friendly, readable, quick-to-use personality. Codex created the actual Stitch project `16468469070349900352` and inspected its generated specimen. An independent agent checked the raw assessment and API contract; another ran the ui-ux-pro-max design-system, UX, and Next.js searches and drafted the frontend plan.

Review caught incorrect AI-generated design behavior: payer-first remainder allocation, bilateral payment claims derived from net balances, zero-balance payment-completed wording, invented group memberships, and unrequested PromptPay/QR/receipt actions. These were rejected in DESIGN.md and a corrective prompt was submitted in Stitch. The last verified Stitch update reported that it was applying those corrections; the corrected board itself has not yet been verified because browser control became unavailable. No screenshots of a corrected result, app implementation, frontend test pass, push, or merge are claimed.

PRODUCT.md records confirmed product context; DESIGN.md is an explicitly proposed design; docs/frontend-plan.md describes real API integration, exact BigInt money, frozen-intent retry handling, access/stale-response isolation, payer-only deletion, and milestone checks. Mathematical contrast calculations were run for the proposed token pairs. This is a design/planning checkpoint awaiting the design-direction gate, not a completed frontend milestone.

The owner subsequently approved this direction and requested implementation, backend integration, example images in design-system, and push to dev/frontend only. The first implementation checkpoint adds exact BigInt money primitives. Five native Node tests passed for ordered remainders, exact decimal addition, strict input rules, signed aggregate formatting beyond Number limits, and invalid participant sets. Later UI/build/browser checks are separate checkpoints.

## Frontend implementation and review (2026-11-03)

Codex implemented the Next.js/TypeScript/Tailwind single-page workspace against the six existing FastAPI endpoints, with native controls, self-hosted Noto Sans Thai, BigInt allocation, plain-language errors, payer-only deletion and server-authoritative refreshes. A single frozen intent is persisted before POST and retried unchanged after uncertain results or reload; no runtime form/state/query library was added. TypeScript and package versions are pinned with the npm lockfile. Formatting used a temporary Prettier CLI, not an application dependency.

Independent review caught two real money/state bugs before delivery: a successful manual retry left the original form populated, allowing a new-key duplicate; and a delayed old snapshot could overwrite post-mutation data. The fixes reset the form on every successful create/replay and sequence all snapshot loads. Browser regressions reproduce both situations with the real API. Review also improved exact-share error associations, control value sizes, control-border contrast, stale completion feedback and deletion focus. Generated Stitch transfer/QR features were not implemented.

The first dependency resolution stalled with ESLint10 peer overrides; the implementation pinned the compatible ESLint9 line instead of forcing peer resolution. Turbopack builds failed on the environment's CSS-worker port restriction, including an escalated attempt. The documented Next Webpack compiler then passed production compilation, TypeScript and static generation. The browser harness initially imported httpx, while the backend uses httpx2; replacing the health probe with urllib removed that unnecessary dependency. Locator issues were corrected to reflect native control labels; they were not hidden as passing tests. Full-page failure evidence was retained in temporary directories during diagnosis.

Local verification on the final formatted UI source: ESLint, TypeScript, six native Node money/pending-intent tests, and a fresh production Webpack build passed. The real Chromium/FastAPI/PostgreSQL16 runner passed nine acceptance groups, including equal/exact/zero-share calculations, group and payer authorization, frozen-key replay across reload after a real commit with a simulated lost response, post-delete balances, and delayed responses within/across contexts. Overflow checks passed at375/390/768/1024/1440px; reduced-motion mode and uncaught-browser-error checks passed. Backend regression checks separately passed151 tests with warnings as errors, Ruff over36 files and OpenAPI consistency. Remote CI/push identity is reported only after actual delivery.

Actual desktop/mobile screenshots use friendly synthetic expenses in the runner's random schema. The schema and owned processes were cleaned after the run. The later Stitch asset pass could not obtain a verified source export, so no application screenshot is labelled as a Stitch image. Approximate frontend implementation/local-review time was about an hour, including dependency/tooling retries and excluding the earlier design session; this is an estimate, not a precise time log.
