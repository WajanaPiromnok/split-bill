# Backend baseline and Git handoff implementation plan

> Execution follows the user's supplied milestone and three-branch workflow. Native implementation with independent documentation/CI tasks and a final review.

**Goal:** Publish a verified backend baseline on `main`, then publish `dev/backend` and `dev/frontend` from that exact commit with matching upstreams.

**Architecture:** FastAPI routes call group access rules backed by SQLAlchemy queries. Alembic owns the PostgreSQL 16 schema; an idempotent seed command provides the brief's users/groups. No expense endpoints or frontend are represented as implemented.

**Spec:** The user's workflow and the SplitBill PDF supplied in this chat. The baseline uses `GET /groups` and `GET /groups/{group_id}`; non-members and nonexistent groups both receive 404. Missing/unknown `X-User` receives 401. Array responses list group summaries; detail responses include ordered usernames.

**Global constraints:** Python >=3.12; PostgreSQL 16; FastAPI; Alembic; pytest; Ruff; no secrets; real incremental commits; no history rewrite. The repository and remote were empty at the audit. The remote is private; GitHub reports rulesets unavailable on its current plan.

## Tasks

- [x] Establish packaging/configuration and an executable test harness. Install dependencies in `backend/.venv` and pin resolved versions.
- [x] Write migration/seed tests, observe missing behavior, then create the users/groups/memberships migration and idempotent seed command. Verify on an isolated PostgreSQL 16 schema.
- [x] Write API/access tests, observe missing endpoints/auth behavior, then implement routing, access rules and database queries. Verify both allowed and denied cases.
- [x] Generate the implemented OpenAPI schema and document the planned expense contract separately. Add setup, handoff, AI usage and three-branch workflow documentation.
- [x] Validate lint/format, the complete baseline suite, migration round-trip, seed replay and the real HTTP server. Review diff and create meaningful incremental commits.
- [ ] Push `main`, verify remote SHA, and validate a fresh clone of that commit. Confirm CI checks refer to that commit.
- [ ] Create and push both dev branches from the verified baseline SHA, set matching upstreams, and verify all three remote refs. No empty PRs are needed at bootstrap.

At this document's commit, local checks passed: 19 tests on Python 3.13.7 / PostgreSQL 16.13, Ruff/format, OpenAPI consistency, dependency checks, migration upgrade/check/downgrade/upgrade, seed replay, and real Uvicorn HTTP responses (200/401/404). The two remote steps are deliberately left for the post-push handoff; this commit cannot contain its own final SHA.

## Review focus

- Missing/unknown user must not gain access, and malformed IDs need the same error envelope.
- Alice must not read group 2; bob must see both groups and the correct memberships.
- Tests must run against PostgreSQL 16 and must not erase application data; they own randomly named schemas only.
- Alembic and seed commands must work from a fresh database without relying on ORM `create_all`.
- The handoff must distinguish implemented group APIs from planned expense APIs; the immutable SHA is reported after commit, not embedded into itself.
