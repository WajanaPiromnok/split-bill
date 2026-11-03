# Payer-only deletion and member balances

## Intent and scope

Finish the two remaining required backend endpoints from the SplitBill brief. Retain the existing FastAPI/PostgreSQL architecture and three-branch delivery workflow. Frontend, settlement suggestions, and repayments are outside this milestone.

## Existing foundation

Expenses and shares are stored atomically with Decimal/NUMERIC money and a group-scoped idempotency key. Expense already has a `deleted` flag; listing excludes it and replay retains its key. Group access hides inaccessible groups with 404. No schema migration is needed for these routes.

## Implementation choices

The brief specifies the business behavior but leaves success representations and repeated deletion open. These are implementation choices, not additional requirements attributed to the user:

- DELETE succeeds with 204 and an empty body. Repeating it as the payer also returns 204. A group member other than the payer receives 403 `expense_delete_forbidden`, including after deletion.
- Group authorization precedes expense lookup. Missing/inaccessible groups remain 404 `group_not_found`. An absent expense or an expense from another group is 404 `expense_not_found`.
- Payer means `paid_by`, independently of request creator or inclusion in the split. Deletion only changes `deleted`; shares, identity, original fields, and key remain stored. Same-key POST replay returns that original expense with `deleted: true`.
- Balances return a direct JSON mapping of username to a two-decimal string. Include every member, including zero balances, ordered alphabetically. Positive means paid more than owed; negative means owing money. Zero is `0.00`.
- Both routes require X-User and use the existing JSON error envelope. Neither requires Idempotency-Key.

## Approaches considered

Python aggregation over the existing expense/share queries would be short but would need careful Decimal context control and would expose multiple statement snapshots during concurrent changes. A single SQL statement using UNION ALL of payer credits and participant debits gives one snapshot, exact NUMERIC sums, and no payer-total multiplication through a shares join. Use that approach and outer-join totals to all group members. Do not cast aggregate totals back to NUMERIC(12,2): a balance can exceed one expense's maximum.

An atomic conditional UPDATE or a locked read can support deletion. Existing immutable payer/group fields make a scoped read, payer check, flag update, and transaction commit sufficient. Concurrent repeated payer deletions have the same final state. Preserve the existing session rollback behavior on failures.

## Validation

Use real PostgreSQL 16 fixtures and independently calculated expected values. Cover payer/creator distinctions, inaccessible groups and cross-group IDs, row/share/key retention, replay after delete, failed-commit rollback, all-zero groups, exact/equal and multiple-payer totals, aggregate values exceeding one bill's limit, group isolation, and exclusion after actual DELETE. Verify the whole suite, lint, generated OpenAPI, and real backend/database integration before publishing. Use merge commits and sync both development branches after accepted PR checks.
