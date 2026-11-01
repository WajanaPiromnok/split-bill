# Three-branch workflow

| Branch | Responsibility |
| --- | --- |
| `main` | Accepted, checked milestones and the common handoff base |
| `dev/backend` | Backend milestones proposed to `main` through PRs |
| `dev/frontend` | Frontend milestones proposed to `main` through PRs |

Every branch contains the whole repository. Branch names define work responsibility, not directory filtering. Keep both dev branches after merges; do not enable automatic deletion for these long-lived branches.

## Inspect first

Inspect working-tree changes, current branch, upstreams, remote URLs, and commit history before changing anything. Fetch remote refs before assuming the remote is empty. Preserve existing work and obey applicable repository rules.

An unborn local `main` is not evidence that remote `main` is empty. An API permission or plan error when reading branch rules is not evidence that no rules exist. Do not bypass rules or change repository visibility to complete a milestone.

## Baseline on main

The one-time bootstrap can go directly to `main` when the remote repository is new and its rules permit this. If `main` already has history or requires PRs, preserve that history and use the permitted PR path.

Create incremental commits from actual reviewed work, for example:

1. Backend packaging, configuration, and environment template.
2. PostgreSQL migrations and repeatable seed.
3. Group APIs, access checks, tests, contract, and CI/tooling.

Adapt boundaries to coherent changes; do not manufacture history retrospectively. Review the staged diff and relevant checks before each commit.

The baseline gate is: documented startup works, migrations and seed work from an empty database, implemented group APIs behave correctly, and their tests/lint/schema checks pass. It does not claim expense or frontend completeness.

After the complete baseline passes, bootstrap push is:

```sh
git push -u origin main
git ls-remote --heads origin main
```

Record the remote baseline SHA in the handoff together with the contract, setup instructions, seed information, checks actually run, and remaining endpoints. A commit cannot contain its own final SHA as tracked content; read it after creating the commit.

## Create both dev branches from one baseline

Use a clean working tree and verify the branch names are not already in use. Capture the accepted remote baseline once:

```sh
git fetch origin
splitbill_baseline_sha="$(git rev-parse origin/main)"
git switch -c dev/backend "$splitbill_baseline_sha"
git push -u origin dev/backend
git switch -c dev/frontend "$splitbill_baseline_sha"
git push -u origin dev/frontend
git ls-remote --heads origin main dev/backend dev/frontend
```

Immediately after creation, both dev heads must refer to that same baseline and track remote branches with matching names. If either branch already exists, inspect and reuse it without reset or force push. No empty commit is needed to create a branch.

For simultaneous work, use separate clones or `git worktree` checkouts. Each participant owns a working tree and branch; never switch another participant's active checkout.

## Development checkpoints

| Milestone | Branch | Acceptance before PR merge |
| --- | --- | --- |
| B1: expenses, allocations, balances, idempotency | `dev/backend` | Money/membership rules, atomic writes, real PostgreSQL concurrency tests, and agreed response/error contract |
| B2: payer-only soft delete | `dev/backend` | Retention, group association, balance updates, replay behavior, and required deletion tests |
| F1: frontend baseline | `dev/frontend` | Buildable frontend, user/group selection against baseline API, money-input/display checks |
| F2: complete required UI | `dev/frontend` | Preview, submit/retry, errors, list/balances, and real browser/API integration after B1 reaches `main` |

B1/B2 and F1/F2 can progress in parallel subject to dependencies. Do not expose expense creation on `main` before money rules and concurrent idempotency work together. Explicitly label mocked checks; F2 cannot use them as its final integration evidence.

## Commit, push, PR, merge, sync

For every milestone after bootstrap:

1. Work on the owning dev branch, review the diff, run relevant checks, and commit coherent changes.
2. Fetch and merge `origin/main` into that dev branch when its working tree is ready. Resolve conflicts by preserving intended behavior, then rerun affected checks.
3. Push to the remote dev branch with the same name.
4. Open or update a PR with that dev branch as head and `main` as base. Explain behavior, dependencies, shared-file changes, and actual verification.
5. Check the combined code against the latest `main`. If `main` moves, update and check the combined result again.
6. Merge with a merge commit only when the necessary checks and repository requirements permit it. Retain the dev branch and its incremental history.
7. Fetch and merge the new `origin/main` into both dev branches in their own working trees; run affected checks and push each branch.

The sync operation, run on each owning dev branch with a ready working tree, is:

```sh
git fetch origin
git merge origin/main
# Run the checks affected by the merge before publishing it.
git push
```

Verify the received `main` SHA is an ancestor of each updated dev branch. Their heads need not equal `main` when they contain additional work. Check the next PR diff contains only work not already accepted.

Use `main` as the normal dependency handoff. Avoid routine rebasing/force pushes of shared history. After bootstrap, accepted work enters `main` through PRs. Do not bypass failing checks, invent reviewer approvals, or claim server-enforced branch protection when it is unavailable.

## Contract changes and evidence

An API change includes examples and tests. If it breaks a frontend already on `main`, update the consumer in the same PR or maintain compatibility during the transition. Coordinate edits to shared files such as configuration, README, generated schemas, and CI.

CI checks the scope that exists: backend baseline first; frontend lint/type/build when added; combined frontend/API/PostgreSQL checks for integration. A skipped or unrun check is not a successful run. Results must apply to the commit or combined revision being accepted.

After each push or merge, report source/destination refs, local and remote SHAs, PR/check links where applicable, exact checks performed, checks not performed, and instructions for the other side to receive that milestone.

For final delivery, fresh-clone the final `main` SHA, install dependencies, migrate/seed an empty database, and run the complete applicable tests/lint/build/integration checks. Any correction returns through the same dev-branch PR cycle; report the final remote SHA only after verification.
