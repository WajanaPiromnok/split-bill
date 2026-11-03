---
version: alpha
name: SplitBill — friendly shared expenses
description: Owner-approved design direction based on the reviewed SplitBill Stitch specimen.
---

## Overview

Status: the owner approved this direction on 2026-11-03 and authorized frontend implementation and delivery to dev/frontend. Implementation and verification evidence are recorded separately.

The owner subsequently approved four vertical profile choices and then a group home: choose alice, bob, carol, or dan once, automatically open the only accessible group, or choose from “กลุ่มของฉัน” when several groups are returned by the API. The workspace header shows the current name and “เปลี่ยนผู้ใช้” instead of a user dropdown. The existing palette, typography, SVG logo, and single-page route remain the design authority.

Stitch created [SplitBill Thai Design System](https://stitch.withgoogle.com/projects/16468469070349900352) on 2026-11-03 before frontend implementation. Its first specimen established a light surface, green primary actions, Thai/Latin sans typography, tabular money, 44px controls, split inputs, expense rows, and balance states. The owner confirmed a friendly, readable, quick-to-use personality.

Physical scene: friends checking a shared bill on phones at a bright cafe table, with a laptop used later to review the group. Use a daylight-readable light theme and restrained color: white working surfaces, dark ink, and green reserved for actions and selected states.

This document records the engineering review of that specimen. Stitch's first board contained incorrect business rules and extra payment features; those are explicitly rejected below. A correction prompt was submitted to Stitch and its progress message was observed, but the resulting revision has not yet been verified because browser control became unavailable. Do not treat the first board's “production” or contrast badges as test evidence.

## Colors

The initial Stitch green was `#15803D`, with teal `#0F766E`, debit orange `#C2410C`, and slate ink `#0F172A`. The reviewed primary below follows the impeccable palette seed at hue 160; it was included in the correction prompt. Keep the page white rather than carrying over the specimen's lavender-tinted canvas.

```yaml
colors:
  primary: oklch(0.50 0.119 160)
  primary-hover: oklch(0.44 0.105 160)
  on-primary: oklch(1 0 0)
  canvas: oklch(1 0 0)
  surface: oklch(0.975 0.006 160)
  selected: oklch(0.96 0.025 160)
  ink: oklch(0.24 0.02 250)
  muted: oklch(0.45 0.02 250)
  border: oklch(0.84 0.012 160)
  control-border: oklch(0.65 0.012 160)
  negative: oklch(0.45 0.14 35)
  negative-surface: oklch(0.97 0.015 35)
  focus: oklch(0.44 0.105 160)
```

Use green plus “ต้องได้รับคืน” for a positive balance, a debit tone plus “ต้องจ่ายคืน” for a negative balance, and neutral ink plus “ยอดสุทธิเป็นศูนย์” for zero. Color never replaces the label. Destructive actions use explicit wording and a confirmation.

A local mathematical sRGB/WCAG calculation gave primary/white 5.65:1, ink/white 16.43:1, muted/white 7.42:1, and negative/negative-surface 7.26:1. Interactive control boundaries use the darker control-border token (3.22:1 on white); decorative separators retain the lighter border. These checks apply to these token pairs only; inspect actual rendered component states before claiming accessibility conformance.

## Typography

Use Noto Sans Thai for the interface, including compatible Latin glyphs, with a system sans fallback. The specimen's Inter pairing is optional; one family is sufficient for this small product. Money uses tabular numerals and right alignment where values are compared. Avoid display lettering in form labels.

```yaml
typography:
  heading:
    fontFamily: Noto Sans Thai
    fontSize: 28px
    fontWeight: 650
    lineHeight: 1.4
  section:
    fontFamily: Noto Sans Thai
    fontSize: 20px
    fontWeight: 600
    lineHeight: 1.5
  body:
    fontFamily: Noto Sans Thai
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: Noto Sans Thai
    fontSize: 14px
    fontWeight: 600
    lineHeight: 1.5
  metadata:
    fontFamily: Noto Sans Thai
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.5
```

## Layout

One responsive page with profile entry, group home, and workspace states. Profile entry uses a compact centered heading, “คุณคือใคร?”, followed by four vertical buttons with an initial, username, and chevron. For several accessible groups, show “กลุ่มของฉัน” and native group buttons labelled with API-provided names; do not infer member counts, balances, or metadata from the group list. Open a sole accessible group directly. In the workspace, place the wordmark, current profile/change action, “กลับไปกลุ่มของฉัน”, and selected group above the working area. Expense entry and its live allocation preview stay primary, with a compact member-balance ledger alongside on desktop and below on mobile. Show newest-first expenses in readable rows with optional share detail. Use sections and separators instead of nested cards.

```yaml
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  section: 48px
  content-max: 1200px
```

At 375px, profile and group choices remain full-width rows, the header's current profile and change action stay readable, the group selector and form fields stack, the submit button spans the available width, and expense rows reflow. Check 768px, 1024px, 1440px and increased zoom. Long descriptions and large balances must wrap without horizontal page scrolling.

## Elevation & Depth

Use surface tone, whitespace, and simple separators. Do not combine a decorative border with a wide blurred shadow. Define semantic stacking levels only when an overlay is actually needed; native selects and an inline delete confirmation avoid most overlay complexity.

## Shapes

```yaml
rounded:
  control: 8px
  panel: 12px
```

Controls are at least 44px high with clear keyboard focus. A selected member remains a labelled checkbox; the appearance must not obscure its native semantics.

## Components

- Context: four native profile buttons before entry; current profile and “เปลี่ยนผู้ใช้”; API-authorized group choices on “กลุ่มของฉัน”; a workspace back action and labelled native group selector.
- Form: description, decimal-string THB input, payer, equal/exact radio group, participants, allocation preview, and explicit exact-split remainder.
- Action states: default, hover, focus, pressed, disabled, saving, success, and recoverable or uncertain failure. Explain why saving is disabled.
- Data: member balances with signs and words; newest-first expense rows, payer, time, amount, shares, and payer-only deletion.
- Loading/empty/error: stable skeletons, a useful first-expense message, plain-language Thai errors, and the correct refresh or same-intent retry action.

The API contract defines behavior. Keep technical headers and retry keys out of the normal form. Preserve one frozen unresolved submission for safe retry; never silently reuse its key with edited data.

## Profile entry and exit

- No profile is selected automatically on first entry. Keep the heading, brief instruction, and four choices easy to scan; no extra Continue button is needed.
- Remember the selected profile across reload in the same tab. Reload opens the group home for multiple accessible groups or the sole group's workspace. A restored unresolved expense bypasses group home and returns to its original user and group.
- “เปลี่ยนผู้ใช้” returns to the chooser and removes the old profile's visible workspace data. Stored expenses remain in PostgreSQL.
- An edited draft requires an inline confirmation before changing profiles, switching groups, returning to group home, or using brand navigation. Cancel keeps the values and restores focus to the initiating action; the destination heading receives focus after confirmed navigation.
- Block those context changes during create/delete requests and while a creation result remains uncertain. Keep the original pending key, body, user, and group available for retry.
- Use the same existing `/` page. Profile selection does not add registration, a password flow, or server-side logout.

## Do's and Don'ts

- Remainder satang follows submitted participant order, independent of the payer. With payer bob and participants alice/bob/carol, `100.00` still allocates `33.34/33.33/33.33`.
- Show net balances only. They do not identify bilateral transfers, and zero does not prove a payment occurred.
- No PromptPay, QR, payment requests, notifications, receipt upload, settlement controls, invented group memberships, or decorative charts.
- Use exact integer satang and string formatting; preserve membership, authorization, API errors, and accessible controls when simplifying.
- The behavior and verification plan is in [docs/frontend-plan.md](docs/frontend-plan.md), with setup/check commands in [README.md](README.md) and actual application screenshots in [design-system](design-system/README.md). Revision-specific results belong in the delivery evidence.
