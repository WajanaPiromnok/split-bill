# SplitBill frontend plan

Status: the owner approved the design direction on 2026-11-03 and authorized full frontend implementation, real backend integration, reference images in design-system, and push to dev/frontend. This plan records intended behavior; actual checks are reported separately.

The owner later approved a vertical profile-entry screen using the same four seeded users, direct entry after clicking a name, and a header action to return to the chooser. This change stays on the existing `/` page and is delivered to dev/frontend after its own checks.

## Design authority and evidence

- Stitch created [SplitBill Thai Design System](https://stitch.withgoogle.com/projects/16468469070349900352) first. Its specimen board is the visual starting point; the root `DESIGN.md` will record the reviewed tokens and components.
- The user confirmed the personality: friendly, readable, and quick when splitting a bill with friends. The product is the single-page Next.js / TypeScript / Tailwind application required by the take-home brief.
- `ui-ux-pro-max` was searched with `--design-system -p SplitBill`, then UX and Next.js queries. Useful findings: Noto Sans Thai, associated labels, keyboard access, visible focus, adequate touch spacing, contrast, reduced motion, and checks at 375/768/1024/1440px.
- Its automatic horizontal-scroll marketing journey, animated block layout, and blue/orange replacement palette were rejected: they do not serve this bill-entry workflow or the Stitch system. Route streaming and Server Action recommendations do not replace loading/error handling for direct browser-to-FastAPI requests.
- `impeccable` governs product consistency, legibility, responsive composition, and complete interaction states. `ponytail` keeps the implementation small: native controls, React state, `fetch`, and exact integer arithmetic before extra libraries.
- Review of Stitch's first board found invented business rules and features. Reject its payer-first remainder rule, inferred bilateral debts, payment-completed claims at zero balance, PromptPay/QR/payment-request actions, receipt uploads, and invented group memberships. The API contract wins; the corrections must carry into the reviewed design and screens.

## One page, one useful workflow

The primary action is recording an expense with a preview the user can verify before saving. Existing expenses and balances provide context alongside that action.

| Area | Desktop | Mobile |
| --- | --- | --- |
| Entry | Compact centered heading and four vertical profile buttons | Same full-width choices with readable spacing |
| Context | Compact wordmark, current profile/change action, group selector | Profile action stays readable; group selector stacks |
| Group | Name and member names, without invented trip metadata | Compact heading above the working area |
| Entry | Main form with allocation rows immediately below split controls | Form first, normal document flow and full-width submit |
| Balances | Adjacent compact member ledger | Below the form, explicit owe/owed labels retained |
| Expenses | Newest-first list with expandable share detail | Reflow each row; amount and payer stay readable |

Use Thai labels and messages with unchanged seeded usernames and group names. Money displays as `1,000.00` with a clear THB unit. Use text alongside semantic color; a sign or green/red alone does not explain who owes whom.

## Profile entry and exit

1. Show “คุณคือใคร?” before any profile is selected. Four native buttons select alice, bob, carol, or dan and enter directly; there is no automatic default or additional Continue action.
2. After entry, show the current name and “เปลี่ยนผู้ใช้” in the header. It returns to the chooser. This changes the `X-User` assessment identity and does not introduce authentication, registration, or a server logout endpoint.
3. Keep the profile in tab-local session storage for reloads. If an unresolved expense is restored, its captured user/group takes precedence over the ordinary saved profile.
4. Before profile exit discards an edited draft, offer inline cancel/confirm actions. Cancel preserves the values. Confirm clears the old visible context, without deleting database records, and focuses the chooser heading.
5. Block profile exit during create/delete requests and while a creation result is uncertain. Preserve the original pending key/body/user/group and same-intent retry. Keep late responses from repopulating a departed profile.
6. Provide loading and recoverable API error states after selection. Preserve the established keyboard, focus, touch-target, contrast, and reduced-motion behavior.

## Expense entry and exact money

1. Description is required, trimmed, and limited to 500 characters. Amount is a string input with decimal keyboard hint; payer is a native select containing current group members.
2. Equal/exact controls are a labelled radio group. Participants are labelled checkboxes in a stable visible order; that same order is submitted. The payer can differ from the requester and need not participate.
3. Parse plain ASCII decimal strings into `BigInt` satang. Reject signs, grouping commas, spaces, exponent notation, and more than two decimals. A bill must be positive and no greater than `9999999999.99`; exact shares may be zero.
4. Equal preview uses integer quotient/remainder and gives extra satang to participants in submitted order: `100.00 → 33.34 / 33.33 / 33.33`; `0.01 → 0.01 / 0.00 / 0.00`.
5. Exact mode shows per-member amount inputs and an explicit remaining/over-allocated amount. Disable submit until the selected shares total the bill exactly. Never round an invalid input into validity.
6. Display formatting groups integer digits and appends two decimal places without converting monetary values to binary floating point. Server balances can exceed the single-bill limit, so format signed aggregate strings without applying that limit.

## API and state ownership

- Fetch `/groups` with `X-User`; use that response as the available group list. Fetch the selected group's detail, expenses, and balances. Balances are a direct member-to-money map, not an array or nested object.
- On confirmed profile exit or group changes, immediately remove the previous context's visible data and reset its editable form. Abort or ignore stale responses. A late response must never populate a different selected context.
- Keep the page shell server-rendered and the interactive workspace a client component. Group-selection requests need their own loading/error state; a route-level loading file cannot represent those subsequent requests.
- After a successful create/delete, refetch expenses and balances from the API. Show a refresh failure separately from mutation failure, so a successfully created expense is not presented as an unsuccessful submission.
- Preserve form values after recoverable validation errors. Map API error codes to plain-language Thai messages with field guidance where possible. Keep unauthorized, unavailable, and empty states distinct.
- Render expense descriptions and names as text. Do not use HTML injection or expose database credentials to the browser. Only the public API origin belongs in frontend environment configuration.

## One submission, safe retries

1. Generate one opaque key on the first valid submit and capture its exact body, user, and group. Disable repeat submission while the attempt is in flight.
2. On an uncertain network/5xx outcome, keep the captured intent and offer **retry the same expense** with the same body/key. Do not let edits silently reuse that key, or create a replacement key for the same uncertain action.
3. Preserve a single unresolved intent across reloads in session storage, with a small validated record; this is not an offline queue. Keep it scoped to the captured user/group and visibly resolve it before starting another expense.
4. A `201` creation or `200` replay resolves the attempt. A replay with `deleted: true` explains that the original was deleted, refreshes the list/balances, and does not resurrect the row.
5. The key and retry machinery stay out of the normal expense form. User-facing feedback describes the outcome and available next action.

## Delete and balance behavior

- Show Delete only when `expense.paid_by` equals the selected user. Use an inline confirmation or native dialog naming the expense; preserve keyboard focus and make Cancel the safe default.
- Wait for the server's empty `204`; do not parse a JSON body or erase a row before authorization succeeds. On error retain the row and provide retry feedback.
- Positive balance: “ต้องได้รับคืน”; negative: “ต้องจ่ายคืน”; zero: “ยอดสุทธิเป็นศูนย์”. Include every member, even when zero. These are balances, not a settlement/payment feature.

## Interaction and quality bar

| State | Expected feedback |
| --- | --- |
| Loading | Stable skeletons plus a readable loading status; no stale member data |
| No groups | Explain that this user has no available groups |
| No expenses | Explain how to add the first expense; do not invent sample transactions |
| Invalid form | Nearby associated message, exact remainder, and reason submit is unavailable |
| Saving/deleting | Action-specific progress; duplicate action blocked |
| Success | Announced confirmation without stealing focus; authoritative data refreshed |
| Failure/uncertain | Keep recoverable data and expose the appropriate refresh or same-intent retry |

All controls have labels, visible focus, logical DOM/tab order, keyboard operation, and generous touch targets. Use 44px control targets and at least 8px between adjacent targets. Body/placeholder text must meet 4.5:1 contrast. Honor reduced motion; use short state transitions rather than page choreography. Long descriptions, large signed amounts, zoom, and narrow widths must wrap without horizontal page scrolling.

## Delivery checkpoints

1. Review the Stitch system and responsive screen direction; record the accepted design in `DESIGN.md` before UI implementation.
2. Commit the minimal Next.js foundation and exact-money checks, then implement user/group loading and the real read views on `dev/frontend`.
3. Commit the equal/exact form and frozen-intent retry handling, then payer-only deletion and server refresh behavior. Push reviewable increments to `origin/dev/frontend`.
4. Run ESLint, TypeScript, production build, money checks, and real browser-to-FastAPI-to-PostgreSQL 16 flows. Distinguish deliberately mocked failure checks from real integration evidence.
5. For this delivery, push to `origin/dev/frontend` as explicitly requested; do not merge into main. A later accepted milestone can follow the documented PR/merge/sync workflow. Record actual local/remote SHAs and checks; never infer success from configuration alone.

Required checks include exact `0.10 + 0.20`, the two equal-split examples, exact mismatch/zero shares, large aggregate formatting, user/group isolation and rapid switching, lost-response same-key retry, payer-only deletion, and post-delete balances. Inspect desktop/mobile screenshots and keyboard paths. Update README setup/limitations and AI_NOTES with actual work and corrections.

For the profile-entry change, adapt the browser user-switch helper instead of retaining the removed dropdown. Add checks for no profile/API load on fresh entry, keyboard selection, saved profile reload, exit, dirty-draft cancel/confirm, pending-owner precedence, and create/delete exit guards. Capture entry and workspace states at desktop/mobile sizes after the real integration run; record the results separately against the delivered SHA.

No chart, global state/query/form library, custom select, full authentication, settlement endpoint, or extra route is needed for this milestone.
