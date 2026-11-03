# SplitBill

## Register

product

## Platform

web

## Users

Friends sharing expenses in a group. The assessment uses the seeded users alice, bob, carol, and dan. Users choose a name on the entry screen before viewing that person's groups and expenses, then use “เปลี่ยนผู้ใช้” to return to the chooser. This selects an assessment profile through `X-User`; it is not account authentication.

## Product Purpose

Record an expense, verify each person's share before saving, and understand every group member's net balance. The required surface is one responsive Next.js / TypeScript / Tailwind page connected to the existing FastAPI backend.

## Positioning

Make shared expenses understandable and account for every satang.

## Brand Personality

The owner confirmed: friendly, readable, and quick to use when splitting bills with friends. Thai interface copy should be direct and considerate; seeded usernames and group names remain unchanged.

## Anti-references

No specific reference product was supplied. Keep the interface focused on the expense workflow defined by the assessment; payment processing and settlement claims are outside that scope.

## Design Principles

- Show the allocation before recording it.
- Explain whether a member owes money or is owed money in words.
- Keep the selected user and group clear throughout every action.
- Confirm before discarding an edited draft when changing users, and retain unresolved submissions until their outcome is known.
- Preserve an uncertain submission so retrying does not create another bill.
- Use the API as the authority for access, saved expenses, and balances.

## Accessibility & Inclusion

Readability is an explicit owner preference. Implementation checks will cover labelled native controls, keyboard operation, visible focus, readable contrast, reduced motion, and layouts that work on narrow screens and at increased zoom. No additional user-specific accessibility needs have been supplied.
