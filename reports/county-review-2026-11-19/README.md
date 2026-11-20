# The County Review: recorded playthroughs

Four playthroughs of the County Review from one opening, a replay of one of them, and the other
bounds of the declared placement. They are the play proof of design section 9. Every figure below
is read from the record files in this directory. The run is `BABYLON_POSTGRES_LIVE_FOCUS=county_review
mise run test:rust-postgres`, which runs `county_review_playthroughs` in
`rust/crates/babylon-persistence/tests/observer_material_live/county_review_playthroughs.rs`. It
took 1,991 s for the five sessions (33 minutes) and passed on 20 November 2026.

## What was run

Each run is a new `NationalWorld` campaign with the same campaign id
(`00000000-0000-0000-0000-002616317036`) in its own disposable PostgreSQL database. The driver
sends the requests the client sends (`OrganizerStatus`, `PreviewOrganizer`, `SubmitOrganizer`,
`Advance`) through the runtime session. The seed is the foundation digest of the `Ready` reply,
`1d9aec7c8a7941bb9e7c9a45550c65053a5806725d48bbf0c3c058b90582c11e`, equal in all five sessions,
with the replay seed 319. A run stops at period 34, or two periods after its first short session if
that is later, and never past period 40. In every run the county's first short session was period
29, so every run stopped at period 34.

| Record | The player's line | Result at period 34 (world hash, first 16 hex) |
|---|---|---|
| `no-contact.json` | Nothing is chosen in any period | `1d98b5f5e981479d` |
| `one-position.json` | One contact from the period-3 snapshot, never again. Reopened once at the end | `329dccfb092b66f8` |
| `two-positions.json` | The same, and a second contact from the period-10 snapshot | `0d6b400aab1a0bee` |
| `food-runs.json` | Organize local aid in every period, 34 of 34 submitted, none refused | `2803afbf9e477efa` |

The four final records differ. Each record holds the seed, the action log (the choice, its nonce,
its preview and every position tried before a contact was chosen), the county's configuration, the
opening roster and, for every period, the register digest (`tick_content_hash` and `world_hash`),
the county's cash, spending limit and first class, the taxes and public budget lines the full
observer read from the committed receipts, the bands, the session and the engine's facts for the
close. A session holds the money for relief, the units payable and kept back, the household lines
set for the next close, the hour charges and the rows of the positions that hold a reached household.
`placement-bounds.json` is Step 4 below. `wayne-opening-roster.json` is the opening, printed by
Task 9.

**The contacted positions.** Each is chosen by the county's own preview: the first position of the
list, in its order, whose preview reached a household that would ask and find a place open. The
eight positions the period-3 list put first were tried; the first seven had no place open or would
not ask, and every one is logged in the action log.

- First contact, from the snapshot of period 3: Bottom 50%, earning-nonowner, "Wayne County: extraction (5)", wage,
  1 at work, 0 looking, 0 units. It was chosen after 8 positions were tried.
- Second contact, from the snapshot of period 10: Next 40%, earning-nonowner, "Wayne County: food (5)", wage,
  2 at work, 0 looking, 0 units. It was chosen after 1 position was tried (the first of another crew).

## What each playthrough shows

**No contact.** From period 4 the county holds a session every period. Through period 28 it pays
every unit on the roll: 70,993 household units, $20,094,200 for relief, the household lines equal
the roll's own in all 25 sessions the test checked before the county is short, no hour is charged
and nobody is paid off the roll. The county's cash is $747 million after period 1 and peaks at
$1,150.9 million after period 3. It then falls by $18 million in period 4, by $33.8 million in
period 10, by $36.3 million in period 20, by $53.8 million a period from period 22 to period 27 and
by $56.3 million in period 29. At the close of period 29 it holds $149.5 million, less than its
first class of $151.97 million, so the session of period 29 announces no relief: from period 30 the
county pays no household unit. After period 31 the cash stays at $84.0 million. The two Claimants'
Assembly households come to every session from period 29, in the room four hours together, and bring
nobody (the position has no household left to reach).

**One position.** The contact lands in the session of period 4. One household of the first
position asks, finds a place and is paid: the lines for period 5 hold one more unit for the budget
group of earning households without a business share and one fewer for the group with no earner.
The household brings one more, who is reached from period 5. The two reached households belong to a
family of 185 households: the position's own 144 and 41 more at the same workplace. From period 5 the workplace "Wayne
County: extraction (5)" pays no wage (wages $2,273,280 a period through period 3, $242,304 in
period 4, none from period 5), so its households' place falls to the last rank, the two reached
households ask and find no place, and no unit moves again. They ask again in every session through
period 34 and are recorded "no place" in each; the claim stops at one unit a period for one period.
The player makes the contact once and never returns, and nothing else in the run depends on them.

**Two positions.** The first contact runs as above. The second lands in the session of period 11,
at the workplace "Wayne County: food (5)" in the Next 40%. The households that came were 1, 2, 4,
8 and 16 in sessions 11 to 15, each paid a place, so the reached households were 1, 2, 4, 8, 16
and 32. In period 15 the workplace paid $6,918,672 and from period 16 no wage; in the session of
period 16 the 32 reached households asked and found no place. The doubling held through session
15, which is the last session in which a place was open. The family of the position had 2,434
households, so it was not full.

**Food runs.** The local aid run was submitted in every period. The county's household lines equal
those of the no-contact run in every session, and no hour is charged to a household before the
county is short: a food run reaches no household at the county. It does change the engine's
economy: the world hash differs from period 1 on, and the wage tax collected from period 3.

## The same in all four

In every period of the four runs, which all stop at period 34, the first class (the amount and every
public budget line that is not household support), the spending limit and every tax rate, whoever
receives the tax, are identical. The test compares the set of recipient, basis and rate of all the
tax receipts of each period. The county's own taxes, the wage tax and the operating-income tax, are
both at 1,500 basis points. The relief
requested at the close of a period equals the lines announced at the session before it, in every
period of every run. The county keeps its word.

Against the no-contact run the county's cash is lower by at most $39.60 in the one-position run
(from period 7 to period 20) and by at most $165.60 in the two-position run, and higher by at most
$21.60 in the food-run run. The wage tax collected in a period differs by $3.60 or a few multiples
of it. In the two contact runs the difference then returns to zero in period 21: the wage tax
collected exceeds the control's by $39.60 (one position) and by $165.60 (two positions), the sum of
what was short before. Over the 34 periods the wage tax collected is equal in all four runs, and
the county's cash at period 34 is equal in all four.

## Who works

The Director's words for each band are quoted from the table of design section 7.2. Beside each is the
client's own line for the band, which is the client's text, marked Designed in the client and not the
Director's words:

- Top 1%: "do not work they live entirely off investments". The client's text: "Does not work. Lives
  entirely off investments."
- Next 9%: "some work some live off investments or they are retired". The client's text: "Some work. Some
  live off investments or are retired."
- Next 40%: "makes its living from selling wage labor"; "at least who must work"; "can have unemployment
  too, so they can be looking". The client's text: "Lives by selling wage labor. Must work. Can be
  out of work and looking."
- Bottom 50%: "work but are more likely to receive welfare and require aid and they don't own homes". The
  client's text: "Works, but is more likely to receive welfare and to need aid. Does not own a home."

At the opening, from the roster the campaign captured:

| Band | Households | With someone at work | Only looking | Nobody in labor force | At work | Looking | Units |
|---|---|---|---|---|---|---|---|
| Top 1% | 7,006 | 0 | 0 | 7,006 | 0 | 0 | 0 |
| Next 9% | 63,054 | 49,431 | 4,244 | 9,379 | 101,931 | 5,618 | 5,618 |
| Next 40% | 280,236 | 280,236 | 0 | 0 | 470,695 | 13,105 | 13,105 |
| Bottom 50% | 350,295 | 176,296 | 26,538 | 147,461 | 176,296 | 52,270 | 52,270 |

In every period of every run each band holds exactly its opening households (700,591 in all: no
household left Wayne in 34 periods), no household of the top 1% is in the labor force, and the
bands add back to the engine's closing households. The count for every period of every run is in
the record. The no-contact run in six periods:

Period 1.

| Band | Households | With someone at work | Only looking | Nobody in labor force | At work | Looking | Units |
|---|---|---|---|---|---|---|---|
| Top 1% | 7,006 | 0 | 0 | 7,006 | 0 | 0 | 0 |
| Next 9% | 63,054 | 49,434 | 4,241 | 9,379 | 101,934 | 5,615 | 5,618 |
| Next 40% | 280,236 | 280,236 | 0 | 0 | 470,702 | 13,098 | 13,105 |
| Bottom 50% | 350,295 | 176,301 | 26,533 | 147,461 | 176,315 | 52,251 | 52,270 |

Period 4, the first session.

| Band | Households | With someone at work | Only looking | Nobody in labor force | At work | Looking | Units |
|---|---|---|---|---|---|---|---|
| Top 1% | 7,006 | 0 | 0 | 7,006 | 0 | 0 | 0 |
| Next 9% | 63,054 | 10,185 | 43,490 | 9,379 | 11,292 | 96,257 | 5,618 |
| Next 40% | 280,236 | 129,732 | 150,504 | 0 | 199,215 | 284,585 | 13,105 |
| Bottom 50% | 350,295 | 86,296 | 116,538 | 147,461 | 86,310 | 142,256 | 52,270 |

Period 10.

| Band | Households | With someone at work | Only looking | Nobody in labor force | At work | Looking | Units |
|---|---|---|---|---|---|---|---|
| Top 1% | 7,006 | 0 | 0 | 7,006 | 0 | 0 | 0 |
| Next 9% | 63,054 | 10,185 | 43,490 | 9,379 | 11,296 | 96,253 | 5,618 |
| Next 40% | 280,236 | 134,973 | 145,263 | 0 | 204,456 | 279,344 | 13,105 |
| Bottom 50% | 350,295 | 89,792 | 113,042 | 147,461 | 89,806 | 138,760 | 52,270 |

Period 20.

| Band | Households | With someone at work | Only looking | Nobody in labor force | At work | Looking | Units |
|---|---|---|---|---|---|---|---|
| Top 1% | 7,006 | 0 | 0 | 7,006 | 0 | 0 | 0 |
| Next 9% | 63,054 | 10,185 | 43,490 | 9,379 | 11,300 | 96,249 | 5,618 |
| Next 40% | 280,236 | 135,668 | 144,568 | 0 | 205,151 | 278,649 | 13,105 |
| Bottom 50% | 350,295 | 90,255 | 112,579 | 147,461 | 90,269 | 138,297 | 52,270 |

Period 29, the first short session.

| Band | Households | With someone at work | Only looking | Nobody in labor force | At work | Looking | Units |
|---|---|---|---|---|---|---|---|
| Top 1% | 7,006 | 0 | 0 | 7,006 | 0 | 0 | 0 |
| Next 9% | 63,054 | 10,185 | 43,490 | 9,379 | 11,303 | 96,246 | 5,618 |
| Next 40% | 280,236 | 135,781 | 144,455 | 0 | 205,264 | 278,536 | 13,105 |
| Bottom 50% | 350,295 | 90,330 | 112,504 | 147,461 | 90,344 | 138,222 | 52,270 |

Period 34.

| Band | Households | With someone at work | Only looking | Nobody in labor force | At work | Looking | Units |
|---|---|---|---|---|---|---|---|
| Top 1% | 7,006 | 0 | 0 | 7,006 | 0 | 0 | 0 |
| Next 9% | 63,054 | 10,185 | 43,490 | 9,379 | 11,304 | 96,245 | 5,618 |
| Next 40% | 280,236 | 135,603 | 144,633 | 0 | 205,086 | 278,714 | 13,105 |
| Bottom 50% | 350,295 | 90,225 | 112,609 | 147,461 | 90,239 | 138,327 | 52,270 |

The opening and the Director's two checks agree: the next 40% are all in the labor force, and
nobody in the top 1% is. What the engine does in periods 2 and 3 is large. The households with
someone at work in the next 40% fall from 280,236 to 127,432 by period 3, and the people at work
in the bottom 50% fall from 176,296 to 84,648. They recover slightly and move little after period 20.

## The Archive

The one-position run was stopped and reopened once at the end. The campaign stood at the same tail.
Through the owner connection the Archive's `archive_knowledge_grant_witness_v1` held, for the
campaign, 31 rows with grant keys `county-review-4` to `county-review-34`, exactly one for each of
the 31 periods in which a session was held, each on an organization, each with `granted_tick` equal
to its period. The Archive holds each session's public record.

## The replay

The one-position run was replayed from its action log, in a new database with the same campaign id
and no observer. The register digest (`tick_content_hash` and `world_hash`) is the same in every
one of the 34 periods.

## The other bounds

Step 4 replays the one-position record's opening roster and its recorded facts and contact through
the kernel under the three placements of design 7.2. The declared placement reproduces the run
exactly in every period (the test asserts it). This is a report for the Director, not a pass or a
fail. The figure is the units held by households with no wage after each period: no crew, nobody at
work, a crew that is not paid a wage, or a crew whose wages accrued to nothing in that period.

| Period | Declared | Holders first | Holders last |
|---|---|---|---|
| 1 | 32,156 | 32,156 | 32,156 |
| 2 | 43,584 | 51,372 | 36,189 |
| 3 | 68,364 | 70,927 | 55,744 |
| 4 | 68,364 | 70,927 | 55,744 |
| 5 | 67,283 | 69,846 | 54,663 |
| 6 | 67,040 | 69,603 | 54,420 |
| 7 | 67,024 | 69,587 | 54,404 |
| 8 | 69,572 | 69,572 | 69,572 |
| 9 | 69,557 | 69,557 | 69,557 |
| 10 | 69,546 | 69,546 | 69,546 |
| 11 | 69,532 | 69,532 | 69,532 |
| 12 | 69,519 | 69,519 | 69,519 |
| 13 | 69,506 | 69,506 | 69,506 |
| 14 | 69,493 | 69,493 | 69,493 |
| 15 | 69,482 | 69,482 | 69,482 |
| 16 | 69,470 | 69,470 | 69,470 |
| 17 | 69,458 | 69,458 | 69,458 |
| 18 | 69,447 | 69,447 | 69,447 |
| 19 | 69,436 | 69,436 | 69,436 |
| 20 | 69,425 | 69,425 | 69,425 |
| 21 | 70,993 | 70,993 | 70,993 |
| 22 | 70,993 | 70,993 | 70,993 |
| 23 | 70,993 | 70,993 | 70,993 |
| 24 | 70,993 | 70,993 | 70,993 |
| 25 | 70,993 | 70,993 | 70,993 |
| 26 | 70,993 | 70,993 | 70,993 |
| 27 | 70,993 | 70,993 | 70,993 |
| 28 | 70,993 | 70,993 | 70,993 |
| 29 | 70,993 | 70,993 | 70,993 |
| 30 | 70,993 | 70,993 | 70,993 |
| 31 | 70,993 | 70,993 | 70,993 |
| 32 | 70,993 | 70,993 | 70,993 |
| 33 | 70,993 | 70,993 | 70,993 |
| 34 | 70,993 | 70,993 | 70,993 |

The three agree in period 1. In period 2 holders first puts 7,788 more units with households that
have no wage than the declared placement does, and holders last 7,395 fewer. From period 3 to
period 7 the differences are 2,563 more and 12,620 fewer. From period 8 to period 34 the three
agree. From period 21 every one of the 70,993 units on the roll is held by a household with no wage.

## Time

A close took 8.5 to 10.2 s (mean 9.1 s over 136 closes) and about 308 s for 34 periods. The full
observer's read of a committed period took 6 s at period 1 and 12 s at period 34; the driver reads
on its own thread while the next period closes, so a run waited 62 to 65 s for the reads after
its last close. A campaign opened in 27 to 28 s and its opening was read in 4 s. The five sessions
took 1,991 s together. The wall time of every close is in the `close_seconds` of each period.

## The windowed run

The windowed models of `tools/devtools/national_windowed_qualification.py` now parse every reply the
Rust client emits after a roster slot is chosen: the review contact choice, the contact preview, the
six new county actions and `choose_roster_slot`. A windowed run needs a released native profile that
reaches the close of period 4 with a review contact in period 3. Neither `smoke-01` (2 periods) nor
`walk-01` (10 periods, pinned decisions) does, and the pair refuses outside the released checkout.
Run from this worktree, `tools/run_rust_postgres.sh --wayne-native-pair smoke-01` exits with status 2
and prints:

```text
usage: national_native_pair.py [-h]
                               {path,admit,member,verify-member,qualify,next}
                               {smoke-01,walk-01}
national_native_pair.py: error: missing released native expectation reference
```

No `native-controls.json` is promised.

## What was not shown

- One county. Geographic and sector variation, which Article VIII asks for, is recorded as blocked
  (record 12).
- Runs of 34 periods, not longer. The county is short from period 29 in all four.
- A real window. The driver sends the client's requests through the session; the windowed run
  did not run (see above).
- The Director's wealth law. Homes and wealth are not in this slice.
- The tutorial chapter, which design section 9 names as the acceptance script, is not written here.
- The gates. `mise run rust:check-no-docs`, `mise run check` and `mise run check:ceremony` are run
  by the lead on the final commit of the branch. This file lists no gate result.
