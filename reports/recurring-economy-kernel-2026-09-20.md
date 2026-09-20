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

Firm procurement accounts for goods on hand and outstanding inbound orders.
Freight is part of those orders and is not counted again. Delivered sales,
funded unfilled requests and inventories influence later production and
attendance. Captured price policies can change future quotes without repricing
existing reserves. Both outbound passes share remaining physical resources.
Local firm inventory credits occur after both passes, preventing recursive
forwarding during the close.

Households, persons, monetary payments, labor use and physical goods keep
separate units. This implementation does not yet calculate production costs,
profit, class value transfers or investment from those records.

## Executable evidence

`cargo test -p babylon-material-circuit --locked` passes **134 tests**.
`cargo clippy -p babylon-material-circuit --all-targets --locked -- -D warnings
-D clippy::cognitive_complexity` passes. Formatting and the ADR catalog check
also pass. The catalog retains two pre-existing status conflicts and four
missing-status records. Its bounded check returns `status: ok`.

The recurring integration tests cover these behaviors:

- Eight periods match the control's purchases, output, wages, consumption,
  conserved goods, cash, escrow, idle time and uncommitted hours.
- Exact state encoding and decoding occurs between periods.
- Slower delivery suppresses duplicate procurement. Expected arrivals inform
  later plans but cannot supply current production.
- Unfilled funded demand changes the next quote. Escrow keeps the accepted price.
- A late overflowing production target refuses the close without changing any
  opening account.
- State schema 6 refuses the prior version and malformed, `noncanonical` or
  oversized recurring content.
- A pending finite order restores retail attendance when recurring orders stop.
  Actual handoff precedes retirement.
- A producer that also handles sales counts production and handling work once
  each.
- Funded unfilled retail demand can restart a producer with no opening sales.
- Admission refuses a finite household order without a configured recipient stock.

The stock admission regression first failed because the old boundary returned
a funded order. The corrected boundary leaves opening cash and state intact.

The receipt component separately passes **33 focused tests**: ten recurring
wire tests, nine monetary wire tests, six maintenance wire tests and eight
material-world library tests. Receipt schema 7 includes admission, consumption,
procurement, production plans and price decisions. Its limits include two
handling passes, ten monetary movements per bounded principal family, and the
existing complete 64 MiB envelope ceiling. The decoder refuses old schema 6. Independent
vectors include exact prices beyond 64-bit range and invalid accounting
partitions. These component results precede the combined replay/hosted gates.

The observer joins adjacent states with authenticated order admissions,
settlement and retirement. Household stocks and consumption remain separate
from retail fulfillment. The component passes 63 focused projection and
evidence checks, plus a later regression that rejects changed historical
household consumption. Its strict library Clippy check passes. Detailed order
rows cover active orders and the latest period; cumulative totals and order
counts remain explicit. Evidence schema 8 binds the added household fields.

The integrated staffed replay suite passes all 15 tests. Its recurring fixture
refuses a failed database acknowledgement without publishing cash, household
stock, phase cursors, graph state or events. A retry has the same joint identity.
Restoring a checkpoint with raw inputs in transit reproduces later receipt
bytes and material state, including household order retirement and consumption
after arrival. Cash plus reserves remains 1,000 micro-units. Strict all-target
Clippy for the tick crate passes.

## Remaining qualification

Client, live `PostgreSQL`, broader conformance and native checks remain required
after the observer integration. The current fixed-price control
still has finite capacity schedules. This control does not prove activity after a
52-period national campaign.

Source interpretation and the mechanism map remain in
`docs/superpowers/research/2026-09-20-economic-circuit-source-study.md` and
`reports/national-economy-design-2026-09-20.md`. ADR263 records the approved
architecture and its limits. This report does not certify enjoyment or close
the broader Linear issues.
