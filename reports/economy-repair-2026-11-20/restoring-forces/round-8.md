# Restoring forces, round eight: work and pay

Measured on 22 November 2026 on the small test economy, from head `a35b0d5b7` of the branch. Round eight put the third
part of the approved design (`docs/superpowers/specs/2026-11-21-how-the-economy-adjusts-design.md`) on the bench: people
who look for work in their place (rule A14), pay that moves by steps (A15), and the order in which a workplace lets
people go and cuts its price (A3). After a first pass it added two rules of other parts that the third part leans on:
the first sentences of A17 (a workplace with no money and no credit stops, and its people become seekers) and A5 (plans
made through the chain of supply).

All of it is throwaway code behind switches, on the scratch branch `spike/r8-all` (`84d5a56b0`). Nothing of this round
is in the engine.

**How to read the figures.** A set is 25 runs of the test economy: 8 calm and 17 pushed. Each set was run in four forms,
and the four figures of a row are always in this order: the small figures for 200 periods, the small figures for 400,
the national figures for 200, the national figures for 400. *Stops* is the number of pushed runs, of 17, in which a
workplace made or sold nothing in each of the last ten periods. *Hours* are the hours people attended and were paid for,
of 480 a period: the mean of the last 20 periods, over the 17 pushed runs. *Used* is the part of them that was worked.
Each set is judged against the same economy without this round's rules under the same credit: no credit, the bank as the
design worded it before 22 November (round 7b), or the owners' top-ups, the stand-in of rounds four to seven, which the
design calls a stabilizer that hides the economy.

Every figure was counted from the rows by the lead's own scripts, one run in memory at a time, except where a sentence
names the measuring agent or a reader. The final measurement is 128 sets, 3,200 runs.

## 1. The answer

- **The third part, as built, does not bring the test economy back. It makes it worse.** With all of it on, a workplace
  stops for good in 15, 15, 14, 14 of the 17 pushed runs with no credit and in 15, 15, 10, 12 with the bank. Without it
  the counts are 8, 9, 1, 7 and 7, 9, 1, 6.
- **Fewer hours are worked under every credit, in every form.** Hours used with all of it on, against the same economy
  without it: 290, 232, 316, 310 against 360, 308, 428, 386 with no credit; 258, 212, 339, 290 against 354, 277, 423,
  363 with the bank; 424, 418, 406, 415 against 453, 453, 432, 434 under the top-ups.
- **The owners' top-ups hide the harm.** Under them no workplace stops with all of it on, and still fewer hours are
  worked than without it. The stand-in pays for whatever the rules break.
- **Nothing that stops starts again.** In no set under no credit or under the bank, with or without this round's rules,
  does a workplace make anything again after ten periods of making nothing. It happens only under the top-ups (17 times
  over 4 sets), where the owner pays.
- **The harm starts at the farm and the shop, in the first ten periods.** In those periods only farms and shops take on
  more people than they opened with: no utility and no clinic does, in any of the 128 sets. With all of it on and the
  bank, 21 of the 34 farms do at the small figures, and all 21 have stopped for good at the end; 17 of the 34 shops do,
  and all 17 have stopped. In those ten periods the farms pay for 3,253 hours that nobody works, against 350 without the
  rules. At the national figures 20 farms do, and 13 of them have stopped after 200 periods and 16 after 400. Under the
  top-ups farms take on hands about as often (20, 20, 20, 20 of 34) and none stops, because the owner pays.
- **What happens, as the measuring agent traced it in the harvest that fails and returns:** the harvest fails; the
  farm's plan still asks for the hours of the food that was asked of it; with seekers of the place it now gets the
  hands; it pays them and can use only part of them; its money is gone by period 4 to 6, before the harvest returns in
  period 11. The shop follows. Without this round's rules a farm cannot take on hands from another workplace, so it
  cannot do this.
- **The money ends with the owners.** With all of it on and the bank, at the small figures, each of the 60 workplaces
  stopped at the end of 200 periods holds less than $10. An owner holds $2,300 on average, against $640 or $800 in the
  calm run. Nothing on the bench sends that money back to work.
- **Rule by rule** (section 4): seekers of the place add stops when a workplace may take hands it cannot use; the pay
  rule holds its floor and moves both ways, and its cut and its raise each cost hours in some forms; the workplace still
  cuts its price before it lets people go in most cases; the service price rule with the bet reading saves runs at the
  national figures; the stop rule frees every parked person and keeps no workplace open; plans down the chain help under
  the bank.
- **The design's own tests.** The calm runs are exactly still in every set. Money is exact in every period of every run,
  and so is the count of people. A shock that ends is not survived: no set with any rule of this round beyond seekers
  alone has a returning-harvest run back by period 76.
- **Two faults of mine, corrected inside the round** (section 11): the brief left out two rules the third part leans on,
  and the script skipped its measuring step after the first pass.
- **What follows** (section 13): a workplace's call for hands needs a bound by what its inputs and its money can use;
  then what carries a workplace through a loss and what brings a stopped one back, as ruled on 22 November (ADR318) and
  as the design's fourth part has it.

## 2. What was on the bench

Five rules, each a prototype behind its own switch:

- **People who look for work belong to their place (A14), `SPIKE_SEEK`.** After the engine's own staffing, a workplace
  still short of people for its plan takes whole persons from those looking for work in its copy of the economy. The
  workplace that pays most takes first. The person moves to the new workplace for good and is paid its rate.
  `SPIKE_SEEKERS=2` opens each copy with two people looking for work. They sit in the utility workers' household and
  have no need of their own, which is a limit of the bench.
- **Pay moves by steps (A15), `SPIKE_PAY`.** Each workplace has a standing rate and each place a going rate for new
  hands. The going rate steps against the change in the number looking for work. A workplace still short raises its rate
  a step and draws people, first seekers, then people at lower-paying workplaces. A workplace at a loss with a seeker in
  its place cuts a step. The floor is $7 an hour, and the opening rate is $10. Each clause has a switch that takes it
  away.
- **Letting people go before cutting the price (A3), `SPIKE_O`.** A workplace keeps people for its current request only,
  where the engine keeps them for the larger of its last two. With it go the service price rule (`SPIKE_R`) and its bet
  reading (`SPIKE_O_BET`), chosen in round 7b.
- **A workplace with no money stops, and its people become seekers (A17's first sentences), `SPIKE_STOP`.** A workplace
  that could not pay the hours its plan asked keeps only the people it paid and takes nobody on. It stays held until it
  pays everyone it employs for a whole period, and while held it takes on only as many as its money would pay.
  `SPIKE_STOP_WHOLE` is the literal reading: the same, only for a workplace that paid nobody.
- **Plans down the chain (A5), `SPIKE_D`.** Round seven's prototype: a supplier takes its buyers' plans into its own. A
  buyer's plan is not lowered when its supplier cannot fill it.

*The whole third part* is all five, with two people looking for work at the opening. Each other set takes one piece
away. *Lent hands* is the stand-in of rounds six and seven: hours move between workplaces and people do not.

## 3. The whole third part against the same economy without it

Hours attended / hours used (runs of 17 with a stop).

| No credit | Small, 200 | Small, 400 | National, 200 | National, 400 |
| --- | --- | --- | --- | --- |
| Without this round's rules | 370 / 360 (8) | 316 / 308 (9) | 443 / 428 (1) | 396 / 386 (7) |
| Lent hands | 321 / 316 (8) | 308 / 302 (8) | 388 / 364 (6) | 320 / 296 (11) |
| Seekers of the place alone | 257 / 253 (12) | 214 / 211 (13) | 399 / 376 (7) | 311 / 306 (9) |
| Seekers, two looking at the opening | 233 / 230 (14) | 200 / 196 (14) | 325 / 293 (13) | 303 / 278 (13) |
| The whole third part | 300 / 290 (15) | 244 / 232 (15) | 322 / 316 (14) | 317 / 310 (14) |
| The whole, nobody looking at the opening | 290 / 286 (15) | 254 / 248 (15) | 336 / 325 (14) | 312 / 303 (14) |

| The bank | Small, 200 | Small, 400 | National, 200 | National, 400 |
| --- | --- | --- | --- | --- |
| Without this round's rules | 370 / 354 (7) | 286 / 277 (9) | 438 / 423 (1) | 382 / 363 (6) |
| Lent hands | 292 / 287 (8) | 286 / 282 (8) | 333 / 317 (10) | 227 / 226 (11) |
| Seekers of the place alone | 243 / 236 (13) | 220 / 218 (13) | 406 / 387 (6) | 339 / 326 (7) |
| Seekers, two looking at the opening | 244 / 242 (14) | 207 / 204 (14) | 337 / 324 (12) | 272 / 261 (14) |
| The whole third part | 262 / 258 (15) | 222 / 212 (15) | 363 / 339 (10) | 302 / 290 (12) |
| The whole, nobody looking at the opening | 302 / 298 (15) | 266 / 259 (15) | 325 / 313 (12) | 296 / 288 (14) |

| The top-ups | Small, 200 | Small, 400 | National, 200 | National, 400 |
| --- | --- | --- | --- | --- |
| Without this round's rules | 465 / 453 (0) | 466 / 453 (0) | 444 / 432 (0) | 446 / 434 (0) |
| Lent hands | 473 / 458 (0) | 469 / 453 (0) | 465 / 448 (0) | 462 / 444 (0) |
| Seekers, two looking at the opening | 458 / 437 (1) | 448 / 427 (1) | 449 / 417 (0) | 430 / 396 (1) |
| The whole third part | 450 / 424 (0) | 445 / 418 (0) | 446 / 406 (0) | 458 / 415 (0) |
| The whole, nobody looking at the opening | 441 / 422 (0) | 429 / 404 (1) | 448 / 405 (0) | 441 / 397 (0) |

Runs better and worse than without the rules, by more than an hour attended, for the whole third part: 5 / 11 | 7 / 8 |
1 / 14 | 3 / 12 with no credit; 6 / 10 | 7 / 8 | 3 / 12 | 6 / 9 with the bank; 1 / 12 | 3 / 11 | 8 / 7 | 9 / 6 under the
top-ups.

No set with a rule of this round has fewer runs with a stop than the same economy without the rules, in any form, under
no credit or the bank. Lent hands, the stand-in of earlier rounds, have one fewer at the small figures for 400 periods
under both (8 against 9) and more at the national figures.

By a stricter count, nothing made or sold in each of the last 20 periods, the figures are the same in 120 of the 128
sets. The 8 that differ are all at the national figures, each lower by one or two. One of them is the bank without the
rules for 200 periods: its single stop is shorter than 20 periods (a reader counted 12, at the end of the run), so it is
not a stop by the stricter count.

## 4. Rule by rule

Under the bank, each set against the whole third part. Hours attended (runs of 17 with a stop).

| Under the bank | Small, 200 | Small, 400 | National, 200 | National, 400 |
| --- | --- | --- | --- | --- |
| The whole third part | 262 (15) | 222 (15) | 363 (10) | 302 (12) |
| Nobody looking at the opening | 302 (15) | 266 (15) | 325 (12) | 296 (14) |
| Without pay by steps | 248 (15) | 206 (15) | 360 (10) | 335 (11) |
| Without the cut of pay | 296 (15) | 246 (15) | 353 (10) | 334 (11) |
| Without the raise | 247 (14) | 207 (14) | 367 (10) | 352 (10) |
| Without the going rate | 306 (15) | 238 (15) | 354 (12) | 306 (14) |
| Without letting go at once, the service price rule and its bet reading | 270 (15) | 233 (15) | 320 (14) | 274 (15) |
| Without the service price rule and its bet reading | 290 (15) | 233 (15) | 302 (15) | 266 (15) |
| Without the bet reading | 250 (15) | 192 (15) | 319 (15) | 296 (15) |
| Without the stop rule | 303 (15) | 255 (15) | 367 (10) | 330 (12) |
| The stop rule in its literal reading | 300 (15) | 238 (15) | 357 (10) | 325 (12) |
| Without plans down the chain | 249 (15) | 189 (15) | 335 (13) | 297 (14) |
| With the cap on orders | 289 (15) | 232 (15) | 368 (10) | 339 (13) |

| With no credit | Small, 200 | Small, 400 | National, 200 | National, 400 |
| --- | --- | --- | --- | --- |
| The whole third part | 300 (15) | 244 (15) | 322 (14) | 317 (14) |
| Nobody looking at the opening | 290 (15) | 254 (15) | 336 (14) | 312 (14) |
| Without pay by steps | 201 (15) | 178 (15) | 307 (15) | 277 (15) |
| Without the cut of pay | 264 (15) | 232 (15) | 316 (14) | 298 (15) |
| Without the stop rule | 304 (15) | 250 (15) | 341 (14) | 336 (14) |
| Without plans down the chain | 280 (15) | 220 (15) | 323 (14) | 300 (15) |

- **Seekers of the place (A14).** Alone, the rule adds stops in every form under no credit and under the bank: 12, 13,
  7, 9 and 13, 13, 6, 7 with nobody looking at the opening, 14, 14, 13, 13 and 14, 14, 12, 14 with two. Lent hands,
  which move hours and not people, stop 8, 8 and 8, 8 runs at the small figures, about as many as without them. The rule
  is not to be built as it is.
- **Pay by steps (A15).** The floor holds: no standing rate ends under $7 in any set. Pay moves both ways (section 7).
  Taking the whole rule away changes hours by -13, -16, -4, +33 with the bank and -100, -66, -15, -40 with no credit.
  Taking only the cut away: +35, +23, -10, +31 and -36, -12, -6, -19. Taking only the raise away, with the bank: -14,
  -15, +4, +50. Taking the going rate away, with the bank: +44, +16, -10, +4. No clause changes the count of stops at
  the small figures by more than one. On this bench every wage opens equal to its household's need, so a cut of pay is
  at once a need unmet; the bench cannot say what a cut does where pay stands above need. With no credit the pay rule
  adds hours in every form, and so does its cut alone. With the bank both are mixed.
- **Letting people go before cutting the price (A3).** The prototype lets people go at once when the plan falls. It does
  not make the layoff come first (section 6).
- **The service price rule with the bet reading.** Without either, 15 runs stop in every form under the bank, against
  15, 15, 10, 12 with them: 5 and 3 runs saved at the national figures, as many as or more than by any other piece, and
  none at the small figures.
- **The stop rule (A17's first sentences).** It frees every parked person: none is left at a stopped workplace at the
  end of any run, against 185, 182, 144, 168 people without the rule under the bank and 185, 176, 181, 168 with no
  credit. It changes the count of stops in no form. Over the 17 runs it lets 535, 617, 314, 479 people go for want of
  pay under the bank. They stay in their place, looking for work, to the end: 459, 522, 282, 383 people are looking at
  the last close, against 204, 295, 124, 164 without the rule, where the rest sit unpaid at their stopped workplace. In
  its literal reading (only a workplace that paid nobody) the hours are 300, 238, 357, 325 against 262, 222, 363, 302
  and the stops are the same. The rule costs hours: with it, fewer hours are attended in every form than without it
  (262, 222, 363, 302 against 303, 255, 367, 330 under the bank; 300, 244, 322, 317 against 304, 250, 341, 336 with no
  credit). A workplace it holds takes nobody on, and nothing gives it money again.
- **Plans down the chain (A5).** Taking them away changes hours by -13, -33, -28, -5 with the bank and -20, -24, 0, -17
  with no credit, and the stops from 15, 15, 10, 12 to 15, 15, 13, 14 and from 15, 15, 14, 14 to 15, 15, 14, 15. So they
  help under the bank: more hours in every form, and 3 and 2 runs saved at the national figures. The cap on orders adds
  hours in every form with the bank (+27, +10, +5, +37) and changes the stops to 15, 15, 10, 13.
- **People looking for work at the opening.** With nobody looking, hours change by +40, +44, -38, -6 with the bank and
  -10, +10, +14, -4 with no credit, and the stops are 15, 15, 12, 14 and 15, 15, 14, 14. The two opening seekers have no
  need and no account of their own, so their wages pile up in the utility workers' household. Results with them lean on
  that limit of the bench.

## 5. Where the harm starts: the first ten periods

For each kind of workplace there are 34 cases in a set: 17 pushed runs, two copies of the economy. *Took on hands*
counts the cases in which the workplace employs more people than at the opening at some close of periods 1 to 10. *Of
them stopped* counts those that made or sold nothing in each of the last ten periods of the run. *Idle hours* are the
hours paid and not worked in periods 1 to 10, summed over the 34 cases.

| Farms: took on hands / of them stopped; idle hours | Small, 200 | Small, 400 | National, 200 | National, 400 |
| --- | --- | --- | --- | --- |
| Without the rules, no credit | 0 / 0; 380 | 0 / 0; 380 | 0 / 0; 380 | 0 / 0; 380 |
| Seekers alone, no credit | 10 / 10; 745 | 10 / 10; 745 | 6 / 1; 434 | 6 / 4; 434 |
| Seekers, two at the opening, no credit | 20 / 20; 3,484 | 20 / 20; 3,484 | 20 / 17; 3,791 | 20 / 17; 3,791 |
| The whole third part, no credit | 23 / 23; 3,179 | 23 / 23; 3,179 | 20 / 20; 4,575 | 20 / 20; 4,575 |
| Without the rules, the bank | 0 / 0; 350 | 0 / 0; 350 | 0 / 0; 380 | 0 / 0; 380 |
| Seekers alone, the bank | 12 / 12; 708 | 12 / 12; 708 | 6 / 3; 434 | 6 / 3; 434 |
| Seekers, two at the opening, the bank | 22 / 22; 4,270 | 22 / 22; 4,270 | 20 / 17; 3,520 | 20 / 17; 3,520 |
| The whole third part, the bank | 21 / 21; 3,253 | 21 / 21; 3,253 | 20 / 13; 3,280 | 20 / 16; 3,280 |
| Without the rules, the top-ups | 0 / 0; 240 | 0 / 0; 240 | 0 / 0; 380 | 0 / 0; 380 |
| Seekers, two at the opening, the top-ups | 22 / 0; 1,806 | 22 / 0; 1,806 | 20 / 0; 2,742 | 20 / 0; 2,742 |
| The whole third part, the top-ups | 20 / 0; 1,850 | 20 / 0; 1,850 | 20 / 0; 2,220 | 20 / 0; 2,220 |

| Shops: took on hands / of them stopped; idle hours | Small, 200 | Small, 400 | National, 200 | National, 400 |
| --- | --- | --- | --- | --- |
| Without the rules, no credit | 0 / 0; 154 | 0 / 0; 154 | 0 / 0; 242 | 0 / 0; 242 |
| Seekers alone, no credit | 4 / 4; 483 | 4 / 4; 483 | 3 / 0; 242 | 3 / 1; 242 |
| Seekers, two at the opening, no credit | 17 / 15; 2,102 | 17 / 15; 2,102 | 5 / 2; 890 | 5 / 2; 890 |
| The whole third part, no credit | 17 / 17; 4,619 | 17 / 17; 4,619 | 20 / 20; 2,388 | 20 / 20; 2,388 |
| Without the rules, the bank | 0 / 0; 185 | 0 / 0; 185 | 0 / 0; 242 | 0 / 0; 242 |
| Seekers alone, the bank | 4 / 4; 257 | 4 / 4; 257 | 3 / 0; 242 | 3 / 0; 242 |
| Seekers, two at the opening, the bank | 17 / 15; 1,597 | 17 / 15; 1,597 | 8 / 5; 468 | 8 / 5; 468 |
| The whole third part, the bank | 17 / 17; 4,599 | 17 / 17; 4,599 | 20 / 13; 1,152 | 20 / 16; 1,152 |
| Without the rules, the top-ups | 0 / 0; 270 | 0 / 0; 270 | 0 / 0; 242 | 0 / 0; 242 |
| Seekers, two at the opening, the top-ups | 14 / 0; 263 | 14 / 0; 263 | 8 / 0; 432 | 8 / 0; 432 |
| The whole third part, the top-ups | 11 / 0; 200 | 11 / 0; 200 | 20 / 0; 819 | 20 / 0; 819 |

No utility and no clinic takes on hands in the first ten periods in any set. The 200-period and 400-period sets agree in
these columns because their first ten periods are the same runs.

Which input binds when a farm leaves its hands idle was not isolated in the rows. The first pass's reader of the code
found that a workplace's call for hands is its whole staffing request, and that this request includes the hours the
spare-money rule adds for what was asked and not paid for. The second pass's reader put it this way: the measured harms
rest mainly on the choice, shared by the prototypes, that "needs hands" is read from the request.

## 6. The order of layoff and price cut

For each workplace of each pushed run: which came first, the first close at which it let people go, or the first close
at which it cut its price. Letting go is read from the seekers rule's own record of people let go, so a person drawn
away by another workplace's raise does not count. Cases of 34, as let go first / same close / price cut first / price
cut and nobody let go / neither.

| Clinics, under the bank | Small, 200 | Small, 400 | National, 200 | National, 400 |
| --- | --- | --- | --- | --- |
| Without the rules | 0 / 0 / 16 / 15 / 3 | 0 / 0 / 17 / 14 / 3 | 0 / 0 / 15 / 16 / 3 | 0 / 0 / 19 / 12 / 3 |
| Seekers, two at the opening | 0 / 0 / 19 / 11 / 4 | 0 / 0 / 25 / 5 / 4 | 0 / 0 / 23 / 9 / 2 | 0 / 0 / 25 / 7 / 2 |
| The whole third part | 0 / 0 / 12 / 18 / 4 | 0 / 0 / 25 / 5 / 4 | 0 / 0 / 26 / 5 / 3 | 0 / 0 / 26 / 5 / 3 |
| Without letting go at once and the price rule | 0 / 0 / 11 / 19 / 4 | 0 / 0 / 23 / 7 / 4 | 0 / 0 / 17 / 14 / 3 | 0 / 0 / 19 / 12 / 3 |

| Utilities, under the bank | Small, 200 | Small, 400 | National, 200 | National, 400 |
| --- | --- | --- | --- | --- |
| Without the rules | 0 / 0 / 23 / 7 / 4 | 0 / 0 / 24 / 6 / 4 | 0 / 0 / 15 / 12 / 7 | 0 / 0 / 19 / 8 / 7 |
| Seekers, two at the opening | 0 / 0 / 25 / 5 / 4 | 0 / 0 / 25 / 5 / 4 | 0 / 0 / 22 / 5 / 7 | 0 / 0 / 24 / 4 / 6 |
| The whole third part | 2 / 1 / 24 / 3 / 4 | 2 / 1 / 24 / 3 / 4 | 4 / 2 / 20 / 0 / 8 | 4 / 2 / 20 / 0 / 8 |
| Without letting go at once and the price rule | 0 / 0 / 27 / 3 / 4 | 0 / 0 / 27 / 3 / 4 | 0 / 0 / 27 / 0 / 7 | 0 / 0 / 27 / 0 / 7 |

The design says a shop or a service lets people go before it cuts its price (A3). The clinic is the bench's service of
that kind; power is among the goods whose price swings (A2). No clinic lets anyone go before its first price cut, in any
of the 60 sets counted this way, with or without this round's rules. A shop never cuts its price in these runs; it only
lets people go. A utility, with the whole third part, lets people go first in 2, 2, 4, 4 of 34 cases and cuts its price
first in 24, 24, 20, 20. So the prototype lets people go at once when a plan falls, and at the clinic the price still
falls first.

## 7. Pay

Over the 17 pushed runs. Steps down are counted from the standing rates themselves; raises and people drawn are the
rule's own counts.

| The whole third part | Small, 200 | Small, 400 | National, 200 | National, 400 |
| --- | --- | --- | --- | --- |
| Steps down, no credit | 270 | 309 | 687 | 771 |
| Raises, no credit | 72 | 72 | 164 | 164 |
| People drawn by a raise, no credit | 90 | 90 | 190 | 190 |
| Runs with a standing rate still moving in the last 20 periods, no credit | 4 | 0 | 0 | 2 |
| Runs with the going rate still moving, no credit | 8 | 15 | 3 | 11 |
| Steps down, the bank | 282 | 319 | 829 | 968 |
| Raises, the bank | 74 | 74 | 209 | 287 |
| People drawn by a raise, the bank | 103 | 103 | 287 | 370 |
| Runs with a standing rate still moving in the last 20 periods, the bank | 0 | 0 | 2 | 1 |
| Runs with the going rate still moving, the bank | 12 | 11 | 8 | 4 |
| Steps down, the top-ups | 197 | 232 | 1,061 | 1,422 |
| Raises, the top-ups | 23 | 37 | 230 | 580 |
| People drawn by a raise, the top-ups | 21 | 35 | 207 | 534 |
| Runs with a standing rate still moving in the last 20 periods, the top-ups | 0 | 2 | 7 | 8 |
| Runs with the going rate still moving, the top-ups | 14 | 13 | 13 | 14 |

The lowest standing rate at the end of a run is $7, the floor, in every set that has the cut of pay, and $10, the
opening rate, in the sets without it. The highest standing rate at the end of any run of the whole third part is $12.
With nobody looking for work at the opening it reaches $20, the highest of the round. Steps down outnumber raises in
every form under every credit.

## 8. The bank under the third part

| Over the 17 pushed runs | Small, 200 | Small, 400 | National, 200 | National, 400 |
| --- | --- | --- | --- | --- |
| Lent, without the rules | $731,905 | $841,405 | $1,928,729 | $2,523,626 |
| Written off, without the rules | $2,293 | $4,363 | $9 | $997 |
| Businesses taken, without the rules | 10 | 17 | 1 | 7 |
| Periods in which a workplace drew a loan, and of them cleared at the same close, without the rules | 1,768, 1,717 | 2,464, 2,391 | 2,304, 2,261 | 4,839, 4,731 |
| Refused by the bound of last sales, without the rules | $615,573 | $2,634,148 | $5,299 | $571,276 |
| Lent, the whole third part | $93,644 | $98,138 | $128,830 | $190,932 |
| Written off, the whole third part | $4,322 | $4,322 | $10,581 | $13,617 |
| Businesses taken, the whole third part | 17 | 17 | 17 | 22 |
| Periods in which a workplace drew a loan, and of them cleared at the same close, the whole third part | 674, 647 | 1,188, 1,161 | 434, 380 | 748, 667 |
| Refused by the bound of last sales, the whole third part | $6,888,840 | $11,806,576 | $2,844,416 | $6,788,472 |

With the whole third part the bank lends less than a seventh of what it lends without it, in every form, and it refuses
far more by the bound of last sales. It takes no business that sold anything in the three periods before, its cash never
reaches $0, and nothing is owed at the end of any run. The sums refused count a stopped workplace again in every period
in which it asks. The bound by last sales was dropped by the Director on 22 November (ADR318); it is in these rows as
the design worded it before.

## 9. The design's own tests

- **Still when nothing pushes.** In every one of the 175 sets counted, the two quiet runs hold the same hours in every
  period and no posted price moves. The measuring agent compared every column of all eight calm runs of each set with
  the same economy without the rules and found none that differs.
- **Money exact.** In the 85 sets without a bank the total of money is the same in every period of all 25 runs. In the
  90 sets with one, the gap between the money and what the bank's books explain is $0 in every period.
- **People exact.** In the 149 sets whose rows carry the count of people, each copy's count never changes. Sets without
  the seekers rule carry no such columns.
- **A shock that ends.** By the test of rounds six and seven (in every period from 76 to the end, the hours attended and
  every account's needs met are at nineteen twentieths of the opening or more), 12 of the 128 sets have a
  returning-harvest run that passes. It is the same run each time, the taxed harvest that fails in one copy, and the
  same sets at 200 and at 400 periods: without the rules, with lent hands and with seekers alone, under no credit and
  under the bank, at the small figures. No set passes at the national figures or under the top-ups, and no set with pay,
  the order of layoff, the stop rule or two people looking at the opening passes in any form.
- **Settled after a lasting loss.** Not reached. With the whole third part and the bank a posted price still moves in
  the last 20 periods in 17, 17, 14, 14 of the 17 runs. A stopped shop's posted price climbs a step every period without
  end, in the sets without the rules too (the measuring agent's finding), so this count alone does not show unrest; the
  hours do: section 10.

## 10. 200 periods do not show where it rests

With the whole third part and the bank, the mean hours of the last 20 periods differ by more than 5 between the
200-period and the 400-period run in 10 of the 17 pushed runs at the small figures and in 6 at the national. At the
small figures: fund-P2 246 to 148; fund-P4 50 to 42; fund-P4a 108 to 78; fund-P5 248 to 179; fund-P6a 250 to 161;
fund-P8 246 to 148; plain-P2 250 to 157; plain-P2a 368 to 322; plain-P8 250 to 157; plain-P8a 368 to 322. The same
economy without the rules drifts too, in 7 runs at the small figures. So a figure at 200 periods is a state on the way
down, not a resting place.

## 11. What the readers corrected, and two faults of mine

Two readers checked each pass. One recounted the measuring agents' claims from the rows. One read the prototypes' code
against what their builders said.

- **First pass** (three steps, the small figures): of 26 claims recounted, 17 held, 4 were refuted and 5 were unclear.
  Of 21 claims about the code, 19 held and 2 were refuted.
- **Second pass** (the fourth step and the 128 sets): of 27 claims recounted, 20 held, 5 were refuted and 2 were
  unclear. Of 26 claims about the code, 25 held and 1 was unclear.
- **The prototypes are honest.** Each rule sits behind its own switch, names no workplace, product or period, uses
  whole-number arithmetic, and neither makes nor loses money or people. With every switch off the rows equal those of
  the bench before the round, byte for byte.

What they corrected, each of which this record counts in its own way:

- The agents' hours are hours attended, which include paid hours nobody worked, and their stops are ten periods of
  nothing, not twenty. This record gives both hours and names the sets where the stricter count differs (section 3).
- "No set has fewer stops than without the rules" was wrong for lent hands (section 3).
- "The cut of pay harms under both credits" was wrong: with no credit it helps (section 4).
- The going rate still moves in the last 20 periods in 11 of 17 runs of the whole third part under the bank at the small
  figures for 400 periods, not in 6 (section 7).
- In the first pass the bet reading cut the utility's price cuts by 36 hundredths under the bank and 41 with no credit,
  not by half.
- The rule that nobody takes work below their benefit never fires on this bench. It is untested, not shown to work.
- By a looser count (no hours for three periods, then hours again) a reader found brief restarts in four of the sets
  with a piece taken away. Each ends in a stop again.

What the readers of the code found that the builders had not said:

- A workplace's call for hands is its whole staffing request, with the hours the spare-money rule adds and hours that
  inputs cannot feed (section 5).
- The bank's bound on what people can work reads each workplace's whole pool of people. The pools now change as people
  move, and people who were let go still count.
- A person called back is paid the place's going rate, which has no ceiling. It can raise or cut their pay with no act
  of the workplace.
- The cut of pay counts anyone looking for work as someone who could take the job: people covered by the benefit, and
  the opening seekers who have no needs.
- At the national figures a step of pay is the price step's share of the opening rate, 25 cents.

**Two faults of mine.** (1) My brief for the round left out two sentences of the design that the third part cannot work
without: A17's "Its people become seekers" and A5's plans through the chain, which I had set aside after round seven
measured them under the top-ups. Without the first, people sat unpaid at stopped workplaces where nobody could take them
on. Both went onto the bench in the second pass (the stop rule and plans down the chain). (2) After the first pass my
script skipped its measuring step: it looked for the label `S` in what a builder returned, and the builder had returned
`r8-S`. I corrected the script to keep its own record of what was built, proved that the three finished steps would be
replayed unchanged, and resumed. No step was built twice.

## 12. The steps at the small figures

Each step was first measured alone, at the small figures for 200 periods. Hours attended (runs of 17 with a stop).

| Step set | No credit | The bank | The top-ups |
| --- | --- | --- | --- |
| Without the rules | 370 (8) | 370 (7) | 465 (0) |
| Seekers of the place | 257 (12) | 243 (13) | 470 (0) |
| Seekers, two at the opening | 233 (14) | 244 (14) | 458 (1) |
| Lent hands | 321 (8) | 292 (8) |  |
| Lent hands, two at the opening | 179 (15) | 213 (15) |  |
| Seekers and pay | 305 (16) | 268 (16) | 426 (2) |
| Seekers and pay, nobody at the opening | 288 (15) | 221 (15) | 351 (9) |
| Pay without the cut |  | 280 (14) |  |
| Pay without the raise |  | 260 (15) |  |
| Pay without the going rate |  | 253 (16) |  |
| Pay without drawing people |  | 268 (16) |  |
| Pay, people called back at their old rate |  | 266 (16) |  |
| Letting go at once, with seekers | 238 (14) | 243 (14) | 470 (0) |
| The same with the service price rule and the bet reading | 249 (14) | 250 (15) | 462 (0) |
| The same without the bet reading | 226 (14) | 243 (14) |  |
| The same without the service price rule | 215 (14) | 256 (14) |  |
| Seekers, pay and the order of layoff | 326 (15) | 272 (15) | 445 (1) |
| With the stop rule | 280 (15) | 249 (15) |  |
| With the stop rule in its literal reading | 281 (15) | 264 (15) |  |
| With the stop rule and plans down the chain | 300 (15) | 262 (15) | 450 (0) |
| The same, nobody at the opening | 290 (15) | 302 (15) |  |
| The same without pay | 201 (15) | 248 (15) |  |
| Plans down the chain without the stop rule | 304 (15) | 303 (15) |  |

The step set with the stop rule and plans down the chain is the whole third part: its figures equal those of section 3
at the small figures for 200 periods. An empty cell is a set that was not run.

## 13. What follows

1. **A workplace's call for hands needs a bound.** The next rule to prove: a workplace asks for hands only for the hours
   that its inputs, on hand and on order, and its money can use. I read it as part of two rules the design already has.
   A6 lets a workplace plan beyond what was paid for "as far as its spare money carries". A5 has plans made through the
   chain "until the plans rest", and a buyer's plan that its suppliers cannot fill is not at rest. It is my call within
   those two rules, and it is proven on the bench before anything else. Seekers of the place (A14) go back on the bench
   on top of it.
2. **What carries a workplace through a loss,** as the Director ruled on 22 November (ADR318): a loan to keep running
   that is bounded by the bank's capital and has a term, and an owner's own money for as long as that workplace is the
   best use the owner has. The term is to be measured. The bench has no small owner yet.
3. **What brings a stopped workplace back:** the design's fourth part, a buyer for a shut workplace (A17) and a founding
   where buyers are (A18). The money for it is on the bench already, at rest with the owners.
4. **Pay (A15) stays as designed for now.** Its floor holds and it moves both ways. Whether its cut helps turns on the
   credit, on a bench where every wage equals need. It is measured again with 1 to 3 on the bench.
5. **The order of layoff and price cut (A3) is not reached at the clinic.** The service price rule with its bet reading
   is kept. The order needs a rule of its own, after 1.
6. **The bench is mended first** where its limits bent these results: people looking for work at the opening get a
   household and a need of their own; a seller that offers nothing no longer moves its price (my call within A1: a price
   test needs something offered); the bank's bound on what people can work reads the people a workplace employs or can
   call back; and every run goes to 400 periods.

Round nine measures 1, 2 and 3 together. The effort is bounded: either the tests of section 9 pass on the bench, or
rounds nine and ten are both recorded and the question goes back to the Director.

