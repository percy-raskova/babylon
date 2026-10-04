# National dynamic admission bounds — 2 October 2026

Part of PER-40. These Designed limits admit independently bounded data; they do not create goods, money, workers or production capacity.

## Scope

Delivery orders and their exact backlog have a named 131,072-row limit. Period-service orders have a separate 131,072-row limit; retail orders remain limited to 65,536. The common purchase-principal limit is their sum, 327,680. Native admission, the monetary book and canonical wire use the same family limits. Three obsolete delivery prefix scans were removed, so backlog validation, rebuilding and outbound allocation process every admitted row.

The private working inventory ledger permits 393,216 rows. It temporarily combines finite stock, freight, production and service grants, or stock, future freight, prebooked services and service-input policies during planning. Service quantities still expire before final admission. Durable inventory remains limited to 131,072 rows in both state admission and wire decoding.

Freight, shifts, receipt families, receipt bytes and complete envelopes are unchanged. They remain independent refusal boundaries. No current wire layout or schema version changes merely to reject a still-current retained capture.

## Evidence

The actual input is the qualified captured v15 foundation: 278,865,968 bytes, SHA-256 `c5f76064bfc3f5da923f21ea344297e967c8467efcbac7bd700642087ef73e70`. The changed source-contract checksum is a conformance pin, not an encoded state-header field; the exact retained capture continues to pass ordinary source admission.

Actual staffed `MaterialReplaySession::prepare_advance` runs, using the same opening and empty action batch, exposed these distinct limits:

| Refusal | Evidence |
| --- | --- |
| Combined order count | Parent run reached delivery 0 + retail 6,324 + service 59,212 before the next request. |
| Service family | Logged proposed delivery 0, retail 6,324, service 65,537; close refused after 37.005873142 seconds. |
| Working inventory | Logged 131,072 current rows and proposed row 131,073, housing-service output quantity 86,080; close refused after 56.286854938 seconds. |
| Delivery family | Exact guard and stack identify `recurring::firms::replenish` adding the next delivery order after 65,536; proposed 65,537 is derived from that checked one-row insertion, not an independently logged complete census. Close refused after 87.304848945 seconds. |
| World record | With both order-family repairs, the complete staffed attempt reached `Graph(MaterialBase(World(ByteLimit)))` after 277.156905502 seconds. The earlier material row guards no longer fired. This error alone does not distinguish receipt-row, receipt-byte and register-byte limits. |

Every refused run verified unchanged opening tick, register digest and world hash. Temporary refusal-only diagnostics were restored against exact before/after SHA manifests; none are production source.

Focused RED/GREEN checks cover each named bound, N+1 refusal, late duplicate detection, exact monetary conservation, the complete delivery/backlog tail, transient service expiry and an oversized durable successor's atomic refusal. The latest focused run passes 72 cases: 30 library, 10 monetary wire, three principal, 19 service and ten freight/conformance cases. It includes 131,072 actual local transfers and complete zero backlog, without claiming that independently bounded tick receipts admit that synthetic maximal case.

Evidence logs are under `reports/test-results/national-order-principals/2026-10-02/`. The final retained retry admitted its foundation in 93.842655621 seconds and ran for 372.41 seconds total, after a 2 minute 29 second compile. It produced no accepted successor bytes. The material contract checksum is `c329e1efb4d8ff646b0fda3a88a574f2066e9a24bd66f083eacf15cdb9f9f064`.

The unchanged retail control additionally passes its public N=65,536 admission, canonical byte roundtrip, N+1 refusal and unchanged accepted bytes after refusal. The complete material/tick library and integration pass is GREEN: 851 tests across 82 targets, including conformance and replay; compilation took 3 minutes 55 seconds. Strict all-target material/tick Clippy passes with warnings and cognitive complexity denied. BSL sentinels pass with existing citation warnings; Rust formatting passes after a layout-only correction in the new retail control.

Full national-close qualification remains pending; opening admission or a detached physical helper is not a completed national advance, durable PostgreSQL commit or gameplay qualification.
