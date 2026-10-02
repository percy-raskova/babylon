# Canonical service indexing — 2 October 2026

Part of PER-40. This component removes repeated service lookup scans without changing quantities, prices, capacity, accounting or wire versions.

Service admission uses the already canonical household, need and offer keys. A private order-ID set tracks actual positive appended orders until final canonical sorting. The check still runs for zero-quantity requests; request traversal, sequential cash debits and final receipt duplicate detection keep their order.

Market capture and planning use canonical offer, production and process-output keys. Performance receipts and future orders are grouped as borrowed rows without precomputing sums. Each market still checks requested, admitted and performed sums, then its future commitments, in the original market traversal and original row order. This preserves the first overflow refusal.

Service output capture looks up the published canonical inventory by its complete site/good/unit tuple. Markets are joined using that tuple because market order differs from process order. Household service consumption uses canonical household keys. The existing indexed service validation remains unchanged.

## Exact byte evidence

Before production source edits, five accepted native service openings were exported from existing scenarios: funded multi-stage service, spare capacity, scarce input, direct cost pressure and a future prebooked reserve. `MaterialWorldRegister::prepare_next` produced exact successor-register and receipt baselines. After the change, every complete native successor register and receipt matched those bytes. The fifteen opening/register/receipt files and their SHA-256/length manifest remain under `/tmp/babylon-service-index-equivalence-2026-10-02/`.

Both ignored one-off probes were removed. Original service test sources were restored and checked against the recorded pre-probe hashes. No diagnostic exporter remains in production or tests.

The small fixture preparations measured 264–335 microseconds before and 259–451 microseconds afterward. These single observations verify execution; they establish neither national speed improvement nor p95. The actual national integrated advance, committed p95 target of 10 seconds and county coverage remain for the integrated native qualification.

The full material/tick library and integration pass is GREEN: 851 tests across 82 targets, including services, conformance and replay. Strict all-target material/tick Clippy passes with warnings and cognitive complexity denied. BSL sentinels and formatting pass; existing BSL citation warnings remain. No source-contract or wire-schema change is needed for these indexes.
