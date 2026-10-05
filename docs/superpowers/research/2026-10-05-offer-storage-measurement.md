# National offer storage: measured lossless encoding

This bounded PER-343 change follows the reconstruction repair at `6a79acfdc307`.
It leaves the economic model, canonical material register, receipt and lookup
formats unchanged. The current state storage domain becomes v4. Earlier state
storage domains fail explicitly; retained saves remain data rather than inputs
for a compatibility path. Qualification package claims declare state storage
version 4. The current qualification policy remains v3.

## Representation and accounting

Seller offers contain three typed identities, an exact currency value and one
of three pricing policies. The codec retains the original row order and policy
tags, stores Site/Good/Unit references through the existing immutable lookup,
and separates the common numeric columns from the policy tails. Every numeric
byte remains literal. Reconstruction restores the original canonical bytes.

The candidate cannot add identities or shift later references. An absent
reference selects literal storage after the complete row sequence passes
framing checks. A normalized frame wins only when its compressed payload is
strictly smaller; ties retain the literal frame. This removes the draft's
whole-table candidate clone and prevents frame savings from hiding added
lookup storage. Unchanged opening sections still use the existing elision.

## Measured evidence

The read-only component benchmark authenticated the original retained packets
against the prior full reader evidence, admitted the canonical opening, and
verified exact reconstructed offer bytes. It neither advanced the campaign
nor admitted the old save through the current game decoder.

| Measure | Period 1 | Period 2 |
| --- | ---: | ---: |
| Offer rows | 58,785 | 58,785 |
| Raw offer bytes | 9,610,925 | 9,610,925 |
| Previous compressed offer payload | 2,033,630 | 2,040,571 |
| New compressed offer payload | 456,153 | 460,524 |
| Exact payload saving | 1,577,477 | 1,580,047 |
| Added lookup entries | 0 | 0 |
| Encoding selection, seconds | 0.069105257 | 0.066396891 |
| Reconstruction and byte comparison, seconds | 0.019291053 | 0.019283248 |

Both periods resolve every reference through the opening seed, so references
have the same indices in the later period table. Equal-width frame metadata
and unchanged lookup ownership make the byte reduction exact for this state
package component. PostgreSQL page allocation and total retained growth require
a fresh complete run. These measurements do not pass a storage or play gate.

The benchmark completed its component work in 8.519417767 seconds, excluding
compilation. One-second samples measured a Rust test-process peak of
1,657,982,976 resident bytes and zero swap; this includes opening admission,
not total PostgreSQL, compiler or native game memory. The retained campaign
and the eight implementation source files were unchanged by the benchmark.

Local records remain under `reports/test-results/per342-qualification/2026-10-05/retained-offer-codec001/`.
The original failures and subsequent controls remain under
`reports/test-results/per343-storage/2026-10-05/`.
These operator records are ignored, preserved evidence rather than an
additional qualification authority.

## Controls and limits

Meaningful RED controls reproduced admission of the newly unsupported v3
predecessor and lookup growth from a smaller draft offer frame. The revised
codec passed 27 storage controls, seven material storage/reload controls,
230 qualification evaluator tests, and the required Python gate. Controls
cover original variant order, changed numeric bytes, typed references,
prefixes, parent identity, framing, corruption and canonical admission. A
missing reference cannot conceal a later invalid tag, truncation or trailing
bytes. The first complete Rust test run passed 3,862 of 3,863 tests and
exposed an existing historical employment reader that selected obsolete
workforce names instead of the admitted workplace subjects. The reader now
joins captured site and staffing identities, refuses duplicate or incomplete
series coverage, and preserves the selected series order. The complete
four-profile replay/conservation control passes, including exact first-period
employment counts, date and world identity. The subsequent complete Rust
publication gate passed format, strict all-target Clippy, all 3,863 workspace
tests (112 skipped), doctests and BSL sentinels. Existing citation warnings
remain advisory; no documentation was generated.

The complete retained pre-change growth was 45,809,664 bytes for period 1
and 33,832,960 for period 2. The decimal 40 MB ceiling, 23 MB optimization
target and actual 10 GB/325-period acceptance remain unchanged. No complete
smoke, 52-period, 325-period or native play qualification has passed. The
remaining storage gap requires measured work rather than relabeling this
component result as full save qualification.
