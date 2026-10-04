# Continuous campaign qualification

Part of PER-338, PER-30 and PER-36.

Campaign duration is an explicit captured policy: continuous, or finite with a
positive final period. The standard Michigan presets use continuous duration.
Designed experiments retain their explicit finite endpoints. Opening stocks and
orders remain finite; this change does not itself replenish them. Continuous
campaigns renew installed capacity into current-period budgets through the same
material circuit, including booked future freight reservations.

The observer retains authenticated current and prior material registers, the
latest committed receipt, active orders, and cumulative totals grouped by stable
supplier route or resident/good/unit. Retired order IDs do not accumulate in the
cursor. Cold reads still authenticate the persisted prefix, four records per
page. Their work grows with campaign age; bounded memory does not imply a
constant-time cold start. Historical receipts remain persisted and available
through explicit historical reads.

The new duration formats refuse older captured content, foundation bytes,
protocol messages and database schemas. Existing save data remains untouched;
there is no migration or alternate engine.

## Retained physical qualification

The physical capture is carried forward as a **Derived rebind** after checking
exact dependency equivalence. It is not a road extraction, path calculation, or
new supplier selection. The original full road graph and county path matrix
remain unavailable, as recorded in the September 13 maintenance and organizer
qualification reports.

The before-state is authenticated against Git commit
`f577a13edbf76e5b81e8960dd244194b00c7fd4e`. Removing only `SCHEMA_VERSION` and the
old/new duration fields leaves identical type-preserving canonical parameters,
SHA-256 `b022fe0699c7f88f256a4fbf8e16954b473f6e7f82a5fb6c37d5ced7e82a85db`.
The old duration is exactly 16 periods and the new duration is explicitly
continuous. The finite opening-order coefficient remains unchanged. A direct
negative control changing truck gross weight refuses before publication.

Only the defines binding changes within each decoded commodity and physical
capture. The source manifest also records their new compressed digests. Counts
remain 397 owners, 233 processes, 581 orders, 233 retail final demands, 83
terminals, 7,085 selected physical edges and 1,245 capacity groups.

| Captured input | Before SHA-256 | After SHA-256 |
| --- | --- | --- |
| Defines | `42ddf6cad4efca04201ba81665549583a110b60ef88e40c28a30e52b9b7fabd6` | `7176764f233190164c985ca3847c42e701ba5421824a4277a51e92739b55a2aa` |
| Commodity qualification gzip | `28e4608947c73d9fa95091bb6f32db8875349c17e71dab0ed7429edfea9a902c` | `9147a3461177dd6f6ece532ac53019dca8a8dacd425bb3e9aa7bce9dbed2612f` |
| Physical capture gzip | `b391f261076d58fc72448ec52094beeede5ff9061f7dde6b01554335541bc445` | `095f177b8240f9e9f929673f872abe4b291c5f39e0911d6add9bab903acda1ff` |

Original graph SHA-256:
`d6ec26e347bfabcd3c86c3f9e784c7d9fbb4d32e8a7cb76ae724e53fdc745550`.
Original matrix SHA-256:
`66df8effd50e25fdf5d557ae5a1ae8dcfe7ffda786614adf966ff45ea79945c4`.
The amended terminal pins do not claim reproduction of the original matrix bytes.

The local [dependency-equivalence record](test-results/per338-continuous/source-rebind/dependency-equivalence.json)
retains the exact before/after bytes, original pins and one-off rebind script.
These task artifacts stay outside the published source tree. The existing
synthetic source generator was also rerun against schema 6. Its decoded output
changes only the qualification and physical defines pins; all synthetic geometry
and economic quantities remain identical.

## Verification

The initial duration regression failed because the old content parser rejected
`DURATION`. The focused Python source qualification, capture and protocol tests
pass: 126 tests. The persistence all-target compile passes. Nine focused Rust
checks pass: three duration/cursor tests, five freight projection tests, and one
bounded cumulative-order test. The cursor control uses real committed material
receipts through period 20, restarts at period 17, compares cold and incremental
projections, and refuses an omitted receipt without advancing the retained tail.

The first rolling projection run exposed an existing assumption that future
capacity rows only decrease. The corrected consumer reconciles installed supply,
prior future bookings and actual dispatch receipts. A two-stage route control
rejects changed bookings, unexplained current capacity and changed installed
supply; explicit finite schedule controls still pass.

The full persistence unit suite passes: 241 tests, with 34 live tests excluded
from that unit run. Strict all-target Clippy passes for the kernel, persistence
and client, including the cognitive-complexity check. Both canonical duration
and clock-boundary tests pass. BSL sentinels pass with their existing citation
warnings. Client test execution is
reserved for the integrated normal gate on the root worktree's linked Bevy target.

The exact PostgreSQL 17.11 catalog capture has four role configurations, each
with 110 objects. The 106 unaffected objects have unchanged fingerprints. The
four changed objects are the renamed duration foundation and public header, the
tick foreign-key owner and the dependent material-state view. The fresh-schema
fixtures are unchanged. Schema SHA-256:
`ed9131fb5c1a6a96d66358897d260ccba381eb62d6792609db720fbd6c6d2c66`.
The five live schema checks pass, covering installation, grants, interruption,
ambiguous commit reconciliation and refusal without mutation. Runtime bootstrap
also admits the captured current schema.

The live observer test passes through 18 committed periods of the actual
continuous preset. It checks reopen, cold and incremental projections, historical
navigation without replacing the newer cursor, restricted preview authority,
and refusal of a changed committed register while preserving the last cursor.
The complete live test took 129.27 seconds; this is not a per-period benchmark.

No national runtime performance acceptance or paid native campaign qualification
is claimed. The shipped Michigan capture remains a physical control; the
separately tested recurring monetary circuit is not a paid PostgreSQL campaign
capture. The integrated normal gate owns client test execution and the full
combined Rust/Python qualification.
