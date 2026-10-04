# Captured economic catalog schema ceremony — 2026-10-02

Generated with `tools/generate_ceremony_message.py::build_ceremony_message` from the exact live catalog comparison. No immutable fresh-schema fixture changed.

PostgreSQL 17.11; current SQL source digest `13987d17d08effd2113ef2c0f82b489b0b52a85b8c7e400bf82082e29d81de43`. Each current catalog has 110 rows, with six changed object digests and 104 unchanged. The four captured variants are bare, reader, observer and reader+observer.

The permitted changes are `campaign`, `campaign_foundation`, `material_campaign_foundation_v3`, `material_tick_v3`, `v_observer_economy_foundation_v1` and `v_observer_county_economy_v1`. Component byte limits follow the measured native register and foundation; receipt and source limits stay 64 MiB.

| file | status | rows (old→new) | changed cells | max \|Δ\| |
| --- | --- | --- | --- | --- |
| rust/crates/babylon-persistence/src/fixtures/current_schema_census.txt | M | 110→110 | 6 | n/a |
| rust/crates/babylon-persistence/src/fixtures/current_schema_reader_census.txt | M | 110→110 | 6 | n/a |
| rust/crates/babylon-persistence/src/fixtures/current_schema_reader_observer_census.txt | M | 110→110 | 6 | n/a |
| rust/crates/babylon-persistence/src/fixtures/current_schema_observer_census.txt | M | 110→110 | 6 | n/a |
| contracts/persistence_semantic_vectors.jsonl | M | 54→54 | 1 | n/a |

Semantic vector corpus SHA256: `5c8c79847eaea341d57d89814f29f8c792ccf96cd529ab270653895831ab333e`. The changed foundation vector uses layout 3 and the explicit authored-source tag; its independent mutation now refuses layout 2.

Baselines: blessed(captured-economic-catalog-2026-10-02)
