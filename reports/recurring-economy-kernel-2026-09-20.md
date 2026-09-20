# Recurring economy kernel evidence — 20 September 2026

The integrated material engine reproduces the independent eight-period
fixed-price control. This qualifies a small accounting loop, not a national or
playable campaign. Current Michigan campaign content still selects the physical
control. The active delivery continues through national compilation, rolling
capacity, investment, finite foreign economies and aid/solidarity play.

## Implemented connection

The existing detached material close owns both physical and monetary controls.
Captured household needs generate affordable reserved purchases after wages.
Actual retail handoffs credit household stock, consumption debits it, and unmet
needs remain dated evidence. Unfilled recurring requests expire and refund.
Resolved physical orders and escrow retire together.

Firm procurement accounts for goods on hand and outstanding inbound orders;
freight is part of those orders and is not counted again. Delivered sales,
funded unfilled requests and inventories influence subsequent production and
attendance. Captured price policies can change future quotes without repricing
existing reserves. Both outbound passes share remaining physical resources.
Local firm inventory credits occur after both passes, preventing recursive
forwarding during the close.

Households, persons, monetary payments, labor use and physical goods retain
separate units. This implementation does not yet calculate production costs,
profit, class value transfers or investment from those records.

## Executable evidence

`cargo test -p babylon-material-circuit --locked` passes **134 tests**.
`cargo clippy -p babylon-material-circuit --all-targets --locked -- -D warnings
-D clippy::cognitive_complexity` passes. Formatting and the ADR catalog check
also pass. The catalog retains two pre-existing status conflicts and four
missing-status records; its bounded check returns `status: ok`.

The recurring integration tests establish:

- Eight periods match purchases, production, wages, cash/escrow, consumption,
  paid idle time, uncommitted hours and conserved goods from the independent
  control. Exact state encoding/decoding occurs between periods.
- Slower delivery suppresses duplicate procurement; expected arrivals can
  inform subsequent planning but cannot supply current production.
- Unfilled funded demand changes the next quote; existing escrow retains the
  accepted price.
- A late overflowing production target refuses the close without changing any
  opening account.
- State schema 6 refuses the prior version and malformed, noncanonical or
  oversized recurring content.
- A pending finite purchase restores retail attendance even when recurring
  purchases are disabled, then retires only after actual handoff.
- A producer that also handles sales counts production and handling work once
  each. Funded unfilled retail demand can restart a producer with no opening
  sales.
- A finite household purchase without a configured recipient stock is refused
  at admission. Its regression first failed because the old boundary returned
  a funded order; the corrected boundary leaves opening cash and state intact.

The receipt component separately passes **33 focused tests**: ten recurring
wire tests, nine monetary wire tests, six maintenance wire tests and eight
material-world library tests. Receipt schema 7 includes admission, consumption,
procurement, production plans and price decisions. Its limits include two
handling passes, ten monetary movements per bounded principal family, and the
existing complete 64 MiB envelope ceiling. Old schema 6 is refused. Independent
vectors include exact prices beyond 64-bit range and invalid accounting
partitions. These component results precede the combined replay/hosted gates.

## Remaining qualification

Projection consumers previously assumed that order identities never changed.
They are being connected to authenticated admission/retirement receipts and
explicit household stock balances. Combined replay, PostgreSQL and native
checks remain required after that integration. The current fixed-price control
still has finite capacity schedules; it is not evidence for activity after a
52-period national campaign.

Source interpretation and the mechanism map remain in
`docs/superpowers/research/2026-09-20-economic-circuit-source-study.md` and
`reports/national-economy-design-2026-09-20.md`. ADR263 records the approved
architecture and its limits. This report does not certify enjoyment or close
the broader Linear issues.
