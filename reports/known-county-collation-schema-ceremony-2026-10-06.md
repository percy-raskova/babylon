# Index collation for county knowledge — 2026-10-06

Part of `PER-342` and `PER-343`. This query repair selects the collation of an existing index. It adds no table, index, capability or economic mechanism.

The native opening acknowledged period two. The restricted county query then exceeded its five-second deadline (`SQLSTATE 57014`). The county mapping uses `C` collation. The grant primary key uses the database default. That difference prevented use of the index. [Postgres 17 explains this index restriction](https://www.postgresql.org/docs/17/indexes-collations.html).

An independent inline query returned all 3,144 rows in 196 milliseconds. The permanent regression uses a captured control campaign, 3,144 synthetic county identities and 12,576 timed grants. It reads the production view through a restricted login under the production deadline. Only two selected grants are effective at period zero. Every future grant remains hidden, and the view discloses no mutable observation.

The original source failed at the intended timeout in 17.20 seconds of test execution. The corrected source passed in 12.30 seconds. Both runners verified cleanup of their exact database, role, template, container and volume. This control tests query scale, not national geography qualification.

The four comparisons explicitly select the grant index collation for ASCII county identities. Every lookup still checks campaign, subject kind, exact subject ID, grant key and effective period. The repair preserves the security barrier, permission masks, fields and source observations.

A transaction temporarily installed the corrected view in the retained national game and selected its actual confined reader role. It returned all 3,144 rows in 160 milliseconds. The plan used eight index scans with exact subject keys. Mutable fields and grant flags remained absent. The probe rolled back all DDL. Before and after checks matched the original view definition, privileges, owner, schema identity and committed period-two marker.

An owned fresh Postgres 17.11 capture measured all four privilege configurations with the bounded catalog query. Each had 154 objects. Exactly one view signature changed, and the other 153 signatures matched. Capture took six seconds and verified cleanup completed in ten seconds. The captured catalogs supply the new fixture signatures and source provenance.

The repair preserves immutable fresh-schema fixtures and Archive worker vectors. The supported schema identity now binds the new view source. Older schemas fail current admission. No compatibility code accompanies this repair.

The existing economic foundation, committed-history and individual-grant control passed in 29.24 seconds. The schema identity, owner, shape and privilege-drift control passed in 33.44 seconds. It refused a disabled security barrier and preserved canonical state after rollback. All three schema-source unit controls, Rust formatting and strict persistence/client Clippy with all targets passed.

Evidence remains under `reports/test-results/per342-native-runner/opening001`. `known-scale001` contains RED/GREEN results and sources. `known-view-census001` contains original and captured catalogs. `known-view003` contains the retained-reader result and plan. Native opening, complete memory capture, smoke, 52-period and separate 325-period qualification remain incomplete.

The repository generator `tools/generate_ceremony_message.py::build_ceremony_message` produced this payload from the measured object changes. It did not stage files or change the index.

```text
test(baselines): pin indexed county knowledge comparisons after the live timeout regression

| file | status | rows (old→new) | changed cells | max \|Δ\| |
| --- | --- | --- | --- | --- |
| rust/crates/babylon-persistence/src/fixtures/current_schema_census.txt | modified | 154→154 | 1 | n/a |
| rust/crates/babylon-persistence/src/fixtures/current_schema_reader_census.txt | modified | 154→154 | 1 | n/a |
| rust/crates/babylon-persistence/src/fixtures/current_schema_observer_census.txt | modified | 154→154 | 1 | n/a |
| rust/crates/babylon-persistence/src/fixtures/current_schema_reader_observer_census.txt | modified | 154→154 | 1 | n/a |

Baselines: blessed(known-county-index-collation-2026-10-06)
```
