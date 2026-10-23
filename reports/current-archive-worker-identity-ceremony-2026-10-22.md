# Current Archive worker identity ceremony - 2026-10-22

Part of PER-341 and PER-343. This source consolidation retains the existing Archive schema and its historical schema ceremony records. It adds no schema, game mechanism or acceptance claim.

The existing `shared_identity_vectors_match_the_pinned_template_and_worker_contract` contract requires the worker identity to hash the exact current Archive schema and pinned template. An independent invocation of the same domain/schema/template construction failed before this repair: the vector retained the packed-membership schema identity, while later provenance changes changed the current schema. The exact current template digest still matches its pin.

Only the identity row's worker digest changes from `b155203ea07bb0f7005151e5c2e05f17554366d6b4441d893e6bb43f39eb920a` to `7889e80bd5a50430bb4c6e7627ac7d490c0f3cc87bfff973b16d1714b0ad6bec`. All renderer, knowledge, refusal and batch vectors retain their exact bytes. The independent identity witness passes after replacement. The existing Rust vector test and applicable integration gates remain required before merge; this record does not claim they have run or passed.

The repository generator `tools/generate_ceremony_message.py::build_ceremony_message` produced this one-field drift payload from the exact vector change.

```text
test(baselines): pin the current Archive schema worker identity

| file | status | rows (old→new) | changed cells | max \|Δ\| |
| --- | --- | --- | --- | --- |
| contracts/archive_page_v1_vectors.jsonl | modified | 6→6 | 1 | n/a |

Baselines: blessed(current-archive-worker-identity-2026-10-22)
```
