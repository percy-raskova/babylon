# What brings the small economy back: round four

Measured 21 November 2026. The Director approved the design of how the economy adjusts that day (ADR314).
Round four puts the core of its first part on the small test economy, as throwaway prototypes behind
switches, and adds a push that ends. The rules, by the letters used below:

- **f**: a workplace that holds more cash than one period of what it pays out plans for what was asked of
  it, not only for what was paid for (the design's rule A6; from round two).
- **d2**: owners put cash into a workplace that holds less than its coming wages and inputs (from round
  two; the design replaces it with credit, which is not built here).
- **lent workers** (rule a, from round one): a workplace short of hands is lent the idle hands of another.
- **D**: suppliers plan for their buyers' new plans, at the close (A5; one pass, services only).
- **R**: a service cuts its price only when it performed less than it planned (A1, for services).
- **e-kept**: a goods price steps down when what was offered went unsold and nobody waited (A1, down).
- **S**: a goods price steps up when the seller's stock stands under its buffer (A1, up).
- **W**: raw goods and power move in steps four times as large, and open the next period where a short
  market closed (A2).

"The core" is all eight. Rule A4, a buyer taking from the cheapest of several sellers, needs a second
seller on the test economy and was not built. The pushes: P2 a poor harvest, P4 higher pay at the clinic,
P5 a cut in the fund's taxes, P6 scarcer power, and the new **P8, a poor harvest for ten periods that then
returns**. Each run is 200 periods, the core 400, at the small world's own figures and at the national
figures (steps of 2.5%, two periods of cash). Hours are out of 240. Unmet is food/utility/care out of 40,
the mean of the last 20 periods. This file is written by the lead from the round's structured results
(`round-4-result.json`) and its independent check; the rows are under `out/r4-*`.

## 1. The answer

- **No. The core does not bring the small economy back,** at either set of figures, by the design's own
  test: work and the needs met in each band back to nineteen twentieths within 65 periods of a shock that
  ends, and staying there.
- **One run does come back, for the first time in four rounds.** After the harvest returns, the taxed
  world at the small figures reaches full work at period 97 and meets every need from period 109. Its
  whole state is still from about period 128, at other prices and other cash than it opened with. The
  test's deadline is period 76. The plain world recovers its hours and leaves the owner without care. At
  the national figures neither world returns: 226 and 210 hours at period 200.
- **With no rule at all, ending the cause does not undo the damage.** Both worlds are in ruin at period
  200 (21 and 17 hours of 240), although the harvest is back at period 11. A workplace that has run out
  of cash has no way back.
- **What carries the core is about quantities, not prices.** Without f the small world is ruined and the
  national figures fall to 174 to 195 hours. Without lent workers several runs are ruined at both. D holds
  the clinic when power is scarce and holds the taxed world's returning harvest; it harms the plain
  world's poor harvest.
- **The new price rules do not help as built.** With today's prices in their place (f, d2, lent workers
  and D), every pushed run at the small figures rests at 234 to 240 hours. At the national figures the
  pushes on the side of demand and the returning harvest rest at 240, and the lasting shortages at 198 to
  237. That is the best set measured. At the small figures it costs the owners $8,000 to $18,000 of
  top-ups in the runs of shortage, and in every run some band still goes short of care.
- **S does the most harm,** because no buyer answers the price. The shop restocks what it lacks whatever
  the price. So the farm's price climbs $4 a period while its stock drains just the same, the shop's cash
  goes from $1,400 to $20 in six periods, the shop's price follows on cost, and the clinic and the owner
  are starved. Hours fall further after the harvest is back (141 at period 26) than while it was poor.
  Taking S away raises most runs to full hours. It lowers three (the taxed world under scarce power at
  both figures, the plain world's poor harvest at the national ones) and leaves needs unmet in the taxed
  world's returning harvest, the one run the core mends.
- **W is mixed. R and e-kept were never measured apart.**
- **Against round three's pair (f and d2).** At the small figures the core is worse: three of its runs
  end in or near ruin by period 400. At the national figures the core is better on every lasting shortage
  (211 to 234 hours against 174 to 216, with no workplace closed in 400 periods) and worse on the pushes
  on the side of demand and on the returning harvest.
- **Who goes without.** At the small figures the owner, drained by top-ups that are never paid back. At
  the national figures the workers, in every pushed run but one, while the owner holds $2,000 to $3,300
  and the taxed world's treasury $1,900 to $2,700. The shop's food rests near $100 (it opened at $38): a
  resting price set by who holds the money, in a market that is short about a third of the time.
- **Top-ups never stop in 12 of the 400-period runs.** Owners' cash is standing in for credit, and it runs
  out.
- **Nothing measured in four rounds passes the design's test.** What the rows point to, none of it
  measured: a price works only where a buyer can answer it, by buying less or by going to another seller
  (rule A4); a step up needs its step down, for a seller back at its buffer; credit in place of owners'
  top-ups; and "cut work first" (rule A3) has not been tried.

## 2. The runs

### No rule (the baseline), the new push P8, 200 periods

| world | run | class | hours p34 / p100 / last | last 20: hours | unmet | closes | prices U/F/C/S | owner's cash | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plain | P8 | runs away | 170 / 124 / 20 | 20-30, mean 21.30 | 40/19.20/40 | clinic from 35, farm from 164, shop from 168 | 10/35/187/125 | 1.90-61.90 | Rows equal plain-P2's through p10 and first differ at p11. Hours never come back after the harvest: the highest after p10 is 205 (p22), there are 0 periods at 228 or more, and the mean of p66-75 is 130.2. The clinic stops earlier than in P2 (p35 against p74). Money is conserved: the total is 5160 in every period. |
| fund | P8 | runs away | 150 / 103 / 16 | 14-25, mean 17.30 | 40/23.40/40 | clinic from 13, shop from 147, farm from 149 | 10/28/215/153 | 6.91-156.91 | Rows equal fund-P2's through p10 and first differ at p11. It is worse than P2 for good: hours at p34 and p100 are 150/103 against P2's 197/177, the clinic closes from p13 (in P2 it never closes), and the end is 17.3 hours against P2's 114.65. The highest hours after p10 is 197 (p13), with 0 periods at 228 or more. Money is conserved: the total is 6120 in every period. |

### The core, small world's figures, 200 periods

Set: core: f at 100, d2, a, D, R, e-kept, S, W; small world's figures ($1 steps, one period of cash); 200
periods. Quiet run still: True. Money conserved: True.

| world | run | class | hours p34 / p100 / last | last 20: hours | unmet | closes | prices U/F/C/S | owner's cash | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plain | P2 | slides | 146 / 214 / 144 | 123-240, mean 185.30 | 7.90/14.40/30.65 | none | 14/30.22/25/42 | 0-1196.13 | top-ups $12,149 (last 20 $2,121); 400 periods: slides at 222 |
| plain | P4 | settles near target | 240 / 240 / 240 | 240-240, mean 240 | 0/0/4.85 | none | 12/25/27/38 | 628.64-666.39 | top-ups $88 |
| plain | P6 | still moving | 162 / 214 / 221 | 181-234, mean 207.75 | 9.60/10.50/19.55 | none | 12.09/25.63/25/33 | 0-212.31 | top-ups $6,868; at 400 periods the farm and shop stop (ruin) |
| plain | P8 | settles near target in hours (3-period cycle), not the opening | 164 / 240 / 240 | 240-240, mean 240 | 0/0/10 | none | 10/28/24/38 | 503.67-503.67 | hours stay >=228 only from p103; top-ups $4,316 (none after p130) |
| fund | P2 | runs away | 240 / 142 / 190 | 117-190, mean 153.95 | 13.30/17.70/40 | clinic from 159 | 10/27.11/65/36 | 0-0 | owner drained by $11,222 of top-ups; at 400 periods all three goods workplaces stop by p381 |
| fund | P4 | settles near target | 240 / 240 / 240 | 240-240, mean 240 | 0/0/1.10 | none | 12/25/30/38 | 609.41-637.41 | top-ups $76 |
| fund | P5 | still moving | 193 / 207 / 214 | 205-240, mean 227.85 | 5.70/8/13.85 | none | 10/20/22/31 | 0-571.89 | top-ups $4,453 (last 20 $1,390) |
| fund | P6 | slides | 240 / 228 / 184 | 184-238, mean 212.50 | 6.80/11.55/19.10 | none | 15.25/25.25/26/34 | 0-459.18 | top-ups $11,690; 400 periods: slides at 195.5 |
| fund | P8 | settles near target (exactly still from about p110; not the opening) | 163 / 235 / 240 | 240-240, mean 240 | 0/0/0 | none | 10/24/36/34 | 655.28-655.28 | hours stay >=228 from p97, all needs within 2 from p109; top-ups $3,527 |

### The core, national figures, 200 periods

Set: core: f at 100, d2, a, D, R, e-kept, S, W; national figures (2.5% steps, two periods of cash); 200 periods.
Quiet run still: True. Money conserved: True.

| world | run | class | hours p34 / p100 / last | last 20: hours | unmet | closes | prices U/F/C/S | owner's cash | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plain | P2 | still moving | 231 / 239 / 234 | 220-240, mean 233.75 | 10.30/11.35/26.50 | none | 10/22.22/20.25/105.45 | 3157.93-3436.47 | shop price held near $100; top-ups $2,977 |
| plain | P4 | settles near target (3-period cycle) | 240 / 240 / 240 | 240-240, mean 240 | 0/0/1.30 | none | 12/25/30/38 | 762.86-782.86 | no top-ups |
| plain | P6 | holds a band | 232 / 221 / 233 | 222-240, mean 231.65 | 10.20/14.70/27.95 | none | 11.34/23.61/21.75/105.45 | 2736.68-2987.98 | top-ups $702 |
| plain | P8 | slides | 237 / 233 / 228 | 210-240, mean 226.25 | 10.50/12.75/27.75 | none | 10/20/21.75/104.5 | 2677.22-3420.10 | shop $38 to $104.5; owner affluent |
| fund | P2 | slides | 227 / 206 / 205 | 192-233, mean 211.40 | 7.75/17.20/29.45 | none | 10/22.22/20.25/97.85 | 1932.14-2077.92 | top-ups $5,287; treasury holds $2,435 at the end |
| fund | P4 | holds a band | 240 / 215 / 222 | 196-236, mean 216.10 | 8/11.90/27.80 | none | 12.4/21.2/21.75/100.7 | 2046.42-2355.03 | worse than the pair (240) |
| fund | P5 | slides | 210 / 197 / 204 | 187-228, mean 207.40 | 8.80/18.25/30 | none | 11.2/22.5/20.25/96.9 | 2026.00-2598.05 | worse than the pair (231.5) |
| fund | P6 | slides | 230 / 227 / 211 | 195-240, mean 216.20 | 7.65/17.25/29.90 | none | 11.11/21.25/23.25/98.8 | 1885.11-2143.78 | top-ups $1,643 |
| fund | P8 | slides | 217 / 202 / 199 | 197-230, mean 209.55 | 8.40/14.10/28.75 | none | 11.2/22.5/22.5/99.75 | 2021.94-2174.09 | never back at 228 to stay; treasury $2,693, fund $400 (opened $960) |

### The core, small world's figures, 400 periods

Set: core, small world's figures, 400 periods. Quiet run still: True. Money conserved: True.

| world | run | class | hours p34 / p100 / last | last 20: hours | unmet | closes | prices U/F/C/S | owner's cash | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plain | P2 | slides | 146 / 214 / 230 | 187-240, mean 222.15 | 9.20/9.45/14.65 | none | 10/22.22/23/33 | 0-224.37 | top-ups $18,923, never stop |
| plain | P4 | settles near target | 240 / 240 / 240 | 240-240, mean 240 | 0/0/5.05 | none | 12/25/27/38 | 629.13-667.13 |  |
| plain | P6 | runs away | 162 / 214 / 145 | 86-145, mean 106.85 | 40/12.80/31.35 | farm from 347, shop from 314 | 29.02/182.73/124/128 | 1510.26-2276.02 | from p281-320 the clinic runs dry, then all prices run away; top-ups $46,868 |
| plain | P8 | settles near target in hours (3-period cycle), not the opening | 164 / 240 / 240 | 240-240, mean 240 | 0/0/10 | none | 10/28/24/38 | 503.67-503.67 | same rest as at 200 |
| fund | P2 | runs away | 240 / 142 / 34 | 34-94, mean 42.95 | 40/16.15/40 | farm from 381, clinic from 371, shop from 375 | 10/1/110/62 | 0-0 | w_utility ends with $5,174 |
| fund | P4 | settles near target | 240 / 240 / 240 | 240-240, mean 240 | 0/0/1.05 | none | 12/25/30/38 | 609.41-637.41 |  |
| fund | P5 | holds a band | 193 / 207 / 220 | 200-240, mean 228.65 | 6.75/8.10/15.35 | none | 10/20/21/34 | 0-482.04 | top-ups $8,699, never stop |
| fund | P6 | slides | 240 / 228 / 128 | 128-233, mean 195.50 | 10.35/13/26.60 | none | 24.05/38.05/34/40 | 0-250.83 | farm holds $2,900-3,300 |
| fund | P8 | settles near target (exactly still from about p110; not the opening) | 163 / 235 / 240 | 240-240, mean 240 | 0/0/0 | none | 10/24/36/34 | 655.28-655.28 | identical rest from p110 to p400 |

### The core, national figures, 400 periods

Set: core, national figures, 400 periods. Quiet run still: True. Money conserved: True.

| world | run | class | hours p34 / p100 / last | last 20: hours | unmet | closes | prices U/F/C/S | owner's cash | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plain | P2 | slides | 231 / 239 / 235 | 225-240, mean 235.45 | 10.20/11.55/26.50 | none | 11.2/24.72/21/105.45 | 3064.22-3268.83 | top-ups $7,950 |
| plain | P4 | settles near target (3-period cycle) | 240 / 240 / 240 | 240-240, mean 240 | 0/0/1.35 | none | 12/25/30/38 | 762.86-782.86 |  |
| plain | P6 | still moving | 232 / 221 / 234 | 222-240, mean 230.95 | 10.15/15.80/28.10 | none | 11.22/21.22/21.75/106.4 | 2782.95-3181.79 |  |
| plain | P8 | holds a band | 237 / 233 / 228 | 207-240, mean 225.70 | 10.40/13/27.65 | none | 10/20/19.5/104.5 | 2582.56-3463.21 | windows of 50 hold 222-226 from p101 |
| fund | P2 | holds a band | 227 / 206 / 230 | 204-230, mean 218 | 7.80/14.15/28.15 | none | 10/22.22/21/100.7 | 1973.55-2145.24 | top-ups $11,429, never stop |
| fund | P4 | still moving | 240 / 215 / 192 | 179-215, mean 196.75 | 7.85/18.55/31.25 | none | 10/20/21/97.85 | 1905.85-2134.68 |  |
| fund | P5 | slides | 210 / 197 / 196 | 173-240, mean 202.75 | 9.05/15.90/30.10 | none | 10/21.2/21/89.3 | 1829.92-2778.04 |  |
| fund | P6 | still moving | 230 / 227 / 220 | 193-237, mean 209 | 7.65/18.10/30.80 | none | 11.69/24.21/22.5/100.7 | 1972.02-2134.80 |  |
| fund | P8 | still moving | 217 / 202 / 194 | 187-216, mean 202.90 | 7.90/16/30.55 | none | 10/22.5/20.25/99.75 | 2031.52-2323.94 | top-ups $9,917 |

### Without the four price rules (f, d2, lent workers, D), small figures, 200 periods

Set: f at 100, d2, a, D (prices as the engine has them); small world's figures; 200 periods. Quiet run still:
True. Money conserved: True.

| world | run | class | hours p34 / p100 / last | last 20: hours | unmet | closes | prices U/F/C/S | owner's cash | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plain | P2 | settles elsewhere (3-period cycle) | 240 / 240 / 240 | 240-240, mean 240 | 4/7/10 | none | 10/25/24/38 | 332.43-332.43 | top-ups $15,982, $1,400 in the last 20 |
| plain | P4 | settles near target | 240 / 240 / 240 | 240-240, mean 240 | 0/0/4.10 | none | 12/25/28/38 | 652.73-705.66 |  |
| plain | P6 | slides | 231 / 235 / 230 | 226-240, mean 233.80 | 5/9/11.45 | none | 12/21/21/40 | 151.82-344.86 |  |
| plain | P8 | holds a band | 240 / 240 / 240 | 230-240, mean 237.55 | 1.15/8.55/10 | none | 10/21/24/38 | 274.81-491.96 |  |
| fund | P2 | settles elsewhere | 240 / 240 / 240 | 240-240, mean 240 | 3.95/6.60/9.40 | none | 10/25/23/38 | 207.79-265.21 | top-ups $13,072 |
| fund | P4 | settles near target | 240 / 240 / 240 | 240-240, mean 240 | 0/0/1.10 | none | 12/25/30/38 | 609.56-637.56 |  |
| fund | P5 | settles near target | 240 / 240 / 240 | 240-240, mean 240 | 0/0/4.35 | none | 12/25/27/40 | 652.52-701.97 |  |
| fund | P6 | holds a band | 240 / 100 / 240 | 230-240, mean 239.05 | 0.70/7.45/13.75 | none | 15/26/26/50 | 707.34-891.34 | top-ups $18,039 |
| fund | P8 | settles elsewhere (3-period cycle) | 240 / 240 / 240 | 240-240, mean 240 | 0/6/8 | none | 10/25/24/38 | 392.66-392.66 | top-ups $11,402 |

### Without the four price rules, national figures, 200 periods

Set: f at 100, d2, a, D; national figures; 200 periods. Quiet run still: True. Money conserved: True.

| world | run | class | hours p34 / p100 / last | last 20: hours | unmet | closes | prices U/F/C/S | owner's cash | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plain | P2 | still moving | 236 / 223 / 240 | 214-240, mean 237 | 10.60/11.10/27.65 | none | 10.5/23.13/20.25/110.2 | 2939.53-4153.55 |  |
| plain | P4 | settles near target (3-period cycle) | 240 / 240 / 240 | 240-240, mean 240 | 0/0/1.30 | none | 12/25/30/38 | 762.86-782.86 |  |
| plain | P6 | slides | 222 / 223 / 240 | 221-240, mean 231.20 | 10.80/15/28.15 | none | 11.7/21.25/21/109.25 | 3298.75-4017.00 |  |
| plain | P8 | settles elsewhere | 240 / 240 / 240 | 240-240, mean 240 | 0/1.15/9.85 | none | 9.9/25/24.75/38 | 420.87-525.12 | no top-ups; the same rows as the pair |
| fund | P2 | still moving | 240 / 222 / 207 | 184-220, mean 198.45 | 11.55/11.15/29.70 | none | 10.2/23.13/21/107.35 | 1798.78-1983.07 |  |
| fund | P4 | settles near target | 240 / 240 / 240 | 240-240, mean 240 | 0/0/1.85 | none | 10.2/25/24.75/45.6 | 575.87-644.12 |  |
| fund | P5 | settles elsewhere | 240 / 240 / 240 | 240-240, mean 240 | 0/0.25/6.90 | none | 10.2/20.63/20.25/53.2 | 757.70-780.07 |  |
| fund | P6 | slides | 230 / 230 / 206 | 203-239, mean 218.05 | 9.05/13.65/29.80 | none | 11.7/22.5/23.25/108.3 | 2179.16-2561.42 |  |
| fund | P8 | settles elsewhere | 240 / 240 / 240 | 240-240, mean 240 | 0/1.10/7.95 | none | 10.2/25/23.25/38 | 355.86-432.65 | no top-ups; the same rows as the pair |

### The core without S, small figures, 200 periods

Set: core without S; small world's figures; 200 periods. Quiet run still: True. Money conserved: True.

| world | run | class | hours p34 / p100 / last | last 20: hours | unmet | closes | prices U/F/C/S | owner's cash | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plain | P2 | settles elsewhere | 240 / 240 / 240 | 240-240, mean 240 | 4/8.05/10 | none | 10/33/20/43 | 330.88-408.16 | top-ups $17,405 |
| plain | P4 | settles near target | 240 / 240 / 240 | 240-240, mean 240 | 0/0/4.85 | none | 12/25/27/38 | 628.64-666.39 |  |
| plain | P6 | slides | 222 / 200 / 221 | 217-240, mean 228.35 | 4.55/9.35/13.10 | none | 15.36/22.17/27/35 | 0-425.16 |  |
| plain | P8 | settles elsewhere | 240 / 240 / 240 | 240-240, mean 240 | 0/6.85/10 | none | 10/25/26/35 | 426.01-480.65 | top-ups $13,012, $1,360 in the last 20 |
| fund | P2 | settles elsewhere | 223 / 240 / 240 | 240-240, mean 240 | 4/6.85/9.60 | none | 10/26.22/24/37 | 76.96-299.32 |  |
| fund | P4 | settles near target | 240 / 240 / 240 | 240-240, mean 240 | 0/0/1.10 | none | 12/25/30/38 | 609.41-637.41 |  |
| fund | P5 | settles near target | 240 / 240 / 240 | 240-240, mean 240 | 0/0/4.30 | none | 12/29/29/39 | 644.80-698.20 |  |
| fund | P6 | still moving | 229 / 172 / 216 | 113-221, mean 190.05 | 10.70/15.75/33.60 | none | 15.24/25.24/61/35 | 0-557.39 |  |
| fund | P8 | settles elsewhere | 240 / 240 / 240 | 240-240, mean 240 | 0/3.75/8.10 | none | 10/25/26/35 | 343.68-393.29 |  |

### The core without S, national figures, 200 periods

Set: core without S; national figures; 200 periods. Quiet run still: True. Money conserved: True.

| world | run | class | hours p34 / p100 / last | last 20: hours | unmet | closes | prices U/F/C/S | owner's cash | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plain | P2 | slides | 240 / 224 / 225 | 217-240, mean 231.40 | 10.30/12.90/26.80 | none | 10/22.22/20.25/104.5 | 3325.94-4047.04 |  |
| plain | P4 | settles near target (3-period cycle) | 240 / 240 / 240 | 240-240, mean 240 | 0/0/1.30 | none | 12/25/30/38 | 762.86-782.86 |  |
| plain | P6 | slides | 234 / 224 / 232 | 221-240, mean 232.45 | 10.10/14.95/28.45 | none | 11.70/24.20/23.25/105.45 | 2550.10-3170.05 |  |
| plain | P8 | settles elsewhere | 240 / 240 / 240 | 240-240, mean 240 | 0/0/8.70 | none | 10/25/27.75/35.15 | 472.29-534.48 |  |
| fund | P2 | still moving | 240 / 229 / 240 | 196-240, mean 211.70 | 7.55/18.15/29.55 | none | 10/24.72/21/99.75 | 2002.23-2168.13 |  |
| fund | P4 | settles near target | 240 / 240 / 240 | 240-240, mean 240 | 0/0/1.40 | none | 11.2/25/24/45.6 | 613.76-653.22 |  |
| fund | P5 | settles elsewhere | 240 / 240 / 240 | 240-240, mean 240 | 0/0/5.85 | none | 10/25/21/49.4 | 653.16-708.08 |  |
| fund | P6 | slides | 230 / 219 / 205 | 193-221, mean 205.85 | 8.15/20.30/29.85 | none | 12.45/22.45/23.25/99.75 | 1985.84-2173.59 |  |
| fund | P8 | settles elsewhere | 240 / 240 / 240 | 240-240, mean 240 | 0/0/6.30 | none | 10/25/26.25/38 | 418.74-454.61 |  |

### The core without W, small figures, 200 periods

Set: core without W; small world's figures; 200 periods. Quiet run still: True. Money conserved: True.

| world | run | class | hours p34 / p100 / last | last 20: hours | unmet | closes | prices U/F/C/S | owner's cash | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plain | P2 | still moving | 240 / 240 / 240 | 221-240, mean 234.85 | 6.05/8.50/11.40 | none | 10/30/24/39 | 0-410.09 |  |
| plain | P4 | settles near target | 240 / 240 / 240 | 240-240, mean 240 | 0/0/4.85 | none | 12/25/27/38 | 628.64-666.39 |  |
| plain | P6 | still moving | 240 / 228 / 240 | 189-240, mean 209.55 | 8.10/10.35/19.60 | none | 15/26/25/33 | 0-608.09 |  |
| plain | P8 | holds a band | 210 / 240 / 240 | 235-240, mean 239.75 | 0.10/2.05/7.55 | none | 10/40/20/48 | 335.17-770.30 | farm at $40 and shop at $48 at the end |
| fund | P2 | slides | 230 / 209 / 197 | 175-199, mean 187.70 | 6.30/14.25/28.55 | none | 10/49/22/62 | 759.06-1333.99 |  |
| fund | P4 | settles near target | 240 / 240 / 240 | 240-240, mean 240 | 0/0/1.10 | none | 12/25/30/38 | 609.41-637.41 |  |
| fund | P5 | slides | 214 / 193 / 195 | 192-228, mean 205.75 | 7.30/12.40/31.60 | none | 10/20/20/91 | 1803.48-2072.71 |  |
| fund | P6 | runs away | 230 / 240 / 128 | 98-205, mean 157.95 | 12.90/15.30/40 | clinic from 142 | 12/26/80/37 | 0-0 |  |
| fund | P8 | slides | 240 / 186 / 224 | 223-240, mean 235.20 | 2.05/5.15/9.80 | none | 10/47/20/59 | 808.70-1179.28 |  |

### The core without W, national figures, 200 periods

Set: core without W; national figures; 200 periods. Quiet run still: True. Money conserved: True.

| world | run | class | hours p34 / p100 / last | last 20: hours | unmet | closes | prices U/F/C/S | owner's cash | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plain | P2 | still moving | 239 / 228 / 233 | 217-240, mean 235.10 | 10.20/11.40/26.25 | none | 10.2/25.63/19.5/104.5 | 3283.91-4158.54 |  |
| plain | P4 | settles near target (3-period cycle) | 240 / 240 / 240 | 240-240, mean 240 | 0/0/1.30 | none | 12/25/30/38 | 762.86-782.86 |  |
| plain | P6 | slides | 232 / 232 / 233 | 231-240, mean 234.20 | 10.05/16/28.15 | none | 11.4/21.25/21.75/106.4 | 2759.38-3752.80 |  |
| plain | P8 | slides | 240 / 218 / 194 | 194-240, mean 226.30 | 10.50/12.20/26.50 | none | 9.9/20.63/19.5/102.6 | 3365.35-4214.04 |  |
| fund | P2 | slides | 230 / 218 / 205 | 194-225, mean 209.20 | 8/17.90/29.20 | none | 10.2/21.88/20.25/100.7 | 1993.80-2146.92 |  |
| fund | P4 | slides | 240 / 229 / 223 | 200-240, mean 217.55 | 8.30/10.40/27.95 | none | 10.2/21.88/22.5/101.65 | 2123.29-2645.93 |  |
| fund | P5 | still moving | 240 / 221 / 220 | 179-240, mean 211.65 | 8.55/16.45/30.20 | none | 10.8/21.25/21.75/100.7 | 2154.38-3187.09 |  |
| fund | P6 | holds a band | 230 / 229 / 221 | 208-237, mean 221.90 | 8.15/11.90/27.90 | none | 12/22.5/22.5/103.55 | 2076.17-2343.82 |  |
| fund | P8 | still moving | 240 / 216 / 208 | 185-216, mean 202.60 | 8.70/15.90/29.60 | none | 9.9/20/19.5/100.7 | 2067.09-2208.26 |  |

### The core without lent workers, small figures, 200 periods

Set: core without a; small world's figures; 200 periods. Quiet run still: True. Money conserved: True.

| world | run | class | hours p34 / p100 / last | last 20: hours | unmet | closes | prices U/F/C/S | owner's cash | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plain | P2 | runs away (hours under half) | 207 / 130 / 74 | 68-201, mean 139.50 | 18.90/24.25/34.95 | none | 10/26.94/19/80 | 0-2482.53 | top-ups $44,226 |
| plain | P4 | settles near target | 240 / 240 / 240 | 240-240, mean 240 | 0/0/4.85 | none | 12/25/27/38 | 628.64-666.39 |  |
| plain | P6 | runs away | 217 / 166 / 182 | 131-217, mean 174.85 | 14.40/15/34.80 | clinic from 185 | 11.48/22.5/40/36 | 0-4.31 |  |
| plain | P8 | still moving | 103 / 235 / 220 | 216-240, mean 224.45 | 8.45/9.50/12.35 | none | 10/20/25/30 | 8.62-481.64 |  |
| fund | P2 | slides | 193 / 129 / 187 | 173-206, mean 193.50 | 9.75/15.15/30.35 | none | 14/82.22/22/104 | 1744.73-2288.42 | top-ups $51,401 |
| fund | P4 | settles near target | 240 / 240 / 240 | 240-240, mean 240 | 0/0/1.10 | none | 12/25/30/38 | 609.41-637.41 |  |
| fund | P5 | still moving | 208 / 240 / 235 | 189-235, mean 211.15 | 7.25/11/16.15 | none | 14/28/25/34 | 0-523.08 |  |
| fund | P6 | slides | 126 / 165 / 161 | 129-229, mean 168.30 | 12.75/17.45/30.25 | none | 12.5/25.23/32/36 | 2.69-857.67 |  |
| fund | P8 | runs away | 187 / 76 / 31 | 29-40, mean 32.55 | 40/20.80/40 | farm from 109, clinic from 103, shop from 111 | 14/422/122/154 | 0-0 |  |

### The core without lent workers, national figures, 200 periods

Set: core without a; national figures; 200 periods. Quiet run still: True. Money conserved: True.

| world | run | class | hours p34 / p100 / last | last 20: hours | unmet | closes | prices U/F/C/S | owner's cash | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plain | P2 | runs away | 223 / 217 / 40 | 40-76, mean 58.85 | 40/20/40 | farm from 163, clinic from 123, shop from 171 | 10/143.05/45.75/99.75 | 0-0 |  |
| plain | P4 | settles near target (3-period cycle) | 240 / 240 / 240 | 240-240, mean 240 | 0/0/1.30 | none | 12/25/30/38 | 762.86-782.86 |  |
| plain | P6 | runs away | 221 / 40 / 0 | 0-0, mean 0 | 40/40/40 | utility from 89, farm from 88, clinic from 73, shop from 98 | 150.63/332.55/104.25/177.65 | 0-0 |  |
| plain | P8 | runs away | 229 / 123 / 115 | 102-201, mean 120.20 | 20.15/32.45/39.60 | clinic from 182 | 18.27/29.47/52.5/51.3 | 8.49-1204.13 |  |
| fund | P2 | runs away | 219 / 173 / 40 | 40-40, mean 40 | 40/16/40 | farm from 134, clinic from 113, shop from 142 | 10/202.22/69/139.65 | 0-0 |  |
| fund | P4 | runs away | 240 / 218 / 177 | 98-184, mean 128.90 | 16.15/24.35/39.20 | clinic from 185 | 10.45/27.5/34.5/38.95 | 0-230.15 |  |
| fund | P5 | slides | 240 / 124 / 210 | 206-240, mean 218.70 | 5.25/8.20/27.90 | none | 10/67.5/21.75/67.45 | 1540.01-1770.89 |  |
| fund | P6 | still moving | 221 / 90 / 240 | 225-240, mean 233.65 | 4.35/6.35/12.90 | none | 23.45/51.5/31.5/42.75 | 0-1550.72 |  |
| fund | P8 | still moving | 228 / 101 / 230 | 212-240, mean 226.70 | 7.30/7.75/10.70 | none | 10/20.2/25.5/32.3 | 0-222.61 |  |

### The core without D, small figures, 200 periods

Set: core without D; small world's figures; 200 periods. Quiet run still: True. Money conserved: True.

| world | run | class | hours p34 / p100 / last | last 20: hours | unmet | closes | prices U/F/C/S | owner's cash | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plain | P2 | slides | 109 / 240 / 203 | 195-240, mean 220.60 | 2.25/3.80/19.50 | none | 10/22.22/25/40 | 16.27-1221.58 |  |
| plain | P4 | settles near target | 240 / 240 / 240 | 240-240, mean 240 | 0/0/4.85 | none | 12/25/27/38 | 628.64-666.39 |  |
| plain | P6 | runs away | 166 / 137 / 140 | 83-208, mean 139 | 15.60/22.30/39.10 | clinic from 185 | 15.11/37.11/97/37 | 0-367.50 |  |
| plain | P8 | slides | 178 / 218 / 200 | 196-210, mean 207.60 | 10/10/11.60 | none | 10/20/20/30 | 2.25-2.32 |  |
| fund | P2 | slides | 230 / 125 / 226 | 216-240, mean 229.35 | 3.35/5.60/25 | none | 14/50.22/25/71 | 1014.58-1843.40 |  |
| fund | P4 | settles near target | 240 / 240 / 240 | 240-240, mean 240 | 0/0/1.10 | none | 12/25/30/38 | 609.41-637.41 |  |
| fund | P5 | still moving | 193 / 225 / 230 | 209-240, mean 227.25 | 6.25/8.75/15.85 | none | 14/28/23/36 | 0-630.29 |  |
| fund | P6 | runs away | 212 / 220 / 156 | 127-190, mean 153.25 | 12.70/17.55/40 | clinic from 162 | 12.31/33.11/62/35 | 0-102.93 |  |
| fund | P8 | still moving | 203 / 216 / 240 | 220-240, mean 237.60 | 1.45/1.90/5.25 | none | 14/24/29/34 | 40.53-655.71 |  |

### The core without D, national figures, 200 periods

Set: core without D; national figures; 200 periods. Quiet run still: True. Money conserved: True.

| world | run | class | hours p34 / p100 / last | last 20: hours | unmet | closes | prices U/F/C/S | owner's cash | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plain | P2 | still moving | 231 / 240 / 240 | 214-240, mean 233.85 | 10.30/12.35/27.10 | none | 10/29.72/22.5/105.45 | 2798.77-3624.80 |  |
| plain | P4 | settles near target (3-period cycle) | 240 / 240 / 240 | 240-240, mean 240 | 0/0/1.30 | none | 12/25/30/38 | 762.86-782.86 |  |
| plain | P6 | slides | 232 / 233 / 235 | 214-240, mean 231.05 | 10.20/15.80/28.20 | none | 12.31/21.11/22.5/105.45 | 2725.63-3141.39 |  |
| plain | P8 | slides | 240 / 216 / 210 | 210-240, mean 226.10 | 10.30/13.60/27.40 | none | 10/20/20.25/100.7 | 2478.84-3402.78 |  |
| fund | P2 | slides | 230 / 232 / 198 | 198-230, mean 213.05 | 8/15.60/29.15 | none | 10/22.22/21/100.7 | 1891.22-2173.51 |  |
| fund | P4 | still moving | 240 / 194 / 211 | 196-219, mean 210 | 8.50/12.45/28.85 | none | 10/25/22.5/100.7 | 2043.33-2493.26 |  |
| fund | P5 | slides | 219 / 202 / 234 | 187-240, mean 215.45 | 8.70/14.95/29.25 | none | 11.2/23.7/22.5/100.7 | 2057.48-2774.09 |  |
| fund | P6 | still moving | 230 / 227 / 206 | 194-225, mean 210.20 | 8.30/15.30/30.40 | none | 12.43/22.43/24.75/99.75 | 1981.61-2359.82 |  |
| fund | P8 | slides | 222 / 215 / 205 | 191-222, mean 205.50 | 8.10/17.30/30.10 | none | 10/20.44/21/99.75 | 2002.47-2208.73 |  |

### The core without f, small figures, 200 periods

Set: core without f (d2, a, D, R, e-kept, S, W); small world's figures; 200 periods. Quiet run still: True.
Money conserved: True.

| world | run | class | hours p34 / p100 / last | last 20: hours | unmet | closes | prices U/F/C/S | owner's cash | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plain | P2 | runs away | 7 / 23 / 4 | 3-4, mean 3.45 | 40/37.20/40 | farm from 105, clinic from 114, shop from 117 | 10/409/32/148 | 0-0 |  |
| plain | P4 | settles near target | 240 / 240 / 240 | 240-240, mean 240 | 0/0/4.40 | none | 12/25/28/38 | 643.44-698.81 |  |
| plain | P6 | runs away | 108 / 20 / 20 | 20-30, mean 27.50 | 40/39.40/40 | farm from 59, clinic from 62, shop from 61 | 456.21/694/188/231 | 0-3517.70 | top-ups $375,354: owners' money goes round and round |
| plain | P8 | runs away | 4 / 2 / 2 | 2-2, mean 2 | 40/38/40 | farm from 60, clinic from 20, shop from 63 | 10/1/28/42 | 7.11-7.11 |  |
| fund | P2 | runs away | 85 / 54 / 4 | 4-4, mean 4 | 40/36/40 | farm from 94, clinic from 102, shop from 110 | 10/449.77/34/165 | 0-0 |  |
| fund | P4 | runs away | 240 / 237 / 62 | 3-62, mean 9.65 | 38.95/36.50/40 | clinic from 166 | 14/17/30/43 | 2.61-227.31 |  |
| fund | P5 | still moving | 196 / 150 / 150 | 103-165, mean 136.60 | 12.10/19.60/32.75 | none | 14/24/25/73 | 759.84-1294.91 |  |
| fund | P6 | runs away | 131 / 51 / 50 | 50-50, mean 50 | 40/37.10/40 | farm from 133, clinic from 131, shop from 145 | 379.67/523.18/169/232 | 2046.16-2653.63 | top-ups $234,756 |
| fund | P8 | runs away | 8 / 14 / 21 | 19-58, mean 33.65 | 40/16.90/40 | farm from 73, clinic from 96, shop from 101 | 10/469.15/125/161 | 0-310.23 |  |

### The core without f, national figures, 200 periods

Set: core without f; national figures; 200 periods. Quiet run still: True. Money conserved: True.

| world | run | class | hours p34 / p100 / last | last 20: hours | unmet | closes | prices U/F/C/S | owner's cash | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plain | P2 | slides | 166 / 179 / 178 | 145-206, mean 175.80 | 4.30/20.95/30.50 | none | 27.8/43.33/39/56.05 | 1167.67-2024.99 |  |
| plain | P4 | settles near target (3-period cycle) | 240 / 240 / 240 | 240-240, mean 240 | 0/0/1.30 | none | 12/25/30/38 | 762.86-782.86 |  |
| plain | P6 | slides | 192 / 187 / 188 | 168-220, mean 185.30 | 2.45/20.70/30 | none | 28.7/38.7/39.75/57 | 1375.19-2108.74 |  |
| plain | P8 | holds a band | 188 / 154 / 161 | 161-206, mean 182.90 | 4.75/18.15/29.70 | none | 10.73/21.93/24.75/64.6 | 1202.50-1584.65 |  |
| fund | P2 | still moving | 184 / 196 / 228 | 174-228, mean 195.25 | 7.20/16.90/31.45 | none | 12.92/31.56/28.5/91.2 | 1710.70-2030.18 |  |
| fund | P4 | still moving | 240 / 182 / 176 | 146-198, mean 174.20 | 8/19.95/32 | none | 13.92/25.33/30.75/83.6 | 1587.36-2081.01 |  |
| fund | P5 | slides | 185 / 181 / 159 | 158-206, mean 182.60 | 8.75/15/31.60 | none | 10/21.39/28.5/83.6 | 1731.16-2088.66 |  |
| fund | P6 | settles elsewhere | 192 / 186 / 186 | 186-186, mean 186 | 6/19.80/32 | none | 19.1/29.1/32.25/79.8 | 1793.23-1808.13 |  |
| fund | P8 | slides | 185 / 185 / 180 | 166-210, mean 186.85 | 7.70/14.20/31.30 | none | 11.2/21.01/31.5/87.4 | 1849.03-2020.89 |  |

### Round three's pair (f and d2), small figures, 200 periods

Set: f at 100 with d2 only; small world's figures; 200 periods. Quiet run still: True. Money conserved: True.

| world | run | class | hours p34 / p100 / last | last 20: hours | unmet | closes | prices U/F/C/S | owner's cash | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plain | P2 | holds a band | 238 / 239 / 231 | 230-240, mean 234.25 | 3.95/8.65/10 | none | 11/25/23/38 | 148.68-323.90 | top-ups $322 |
| plain | P4 | settles near target | 240 / 240 / 240 | 240-240, mean 240 | 0/0/4.10 | none | 12/25/28/38 | 652.73-705.66 |  |
| plain | P6 | still moving | 237 / 235 / 239 | 226-240, mean 235.25 | 4.35/9.05/10.70 | none | 13/22/22/38 | 61.34-542.92 | top-ups $7,120 |
| plain | P8 | holds a band | 230 / 240 / 232 | 230-240, mean 235.65 | 2.05/8.40/10 | none | 10/21/23/38 | 272.21-449.59 | hours never under 228 after p1; top-ups $2,693 and still paid |
| fund | P2 | holds a band | 232 / 234 / 240 | 232-240, mean 235.65 | 4/6.90/10.15 | none | 10/26/21/38 | 115.43-214.58 |  |
| fund | P4 | settles near target | 240 / 240 / 240 | 240-240, mean 240 | 0/0/1.10 | none | 12/25/30/38 | 609.56-637.56 |  |
| fund | P5 | settles near target | 240 / 240 / 240 | 240-240, mean 240 | 0/0/4.35 | none | 12/25/27/40 | 652.52-701.97 |  |
| fund | P6 | holds a band | 227 / 228 / 228 | 225-234, mean 228.65 | 0/0.40/13.65 | none | 14/30/25/40 | 412.28-569.60 |  |
| fund | P8 | holds a band | 240 / 236 / 240 | 235-240, mean 238.15 | 0/3.55/8.45 | none | 10/25/23/38 | 325.38-396.35 | top-ups $329 |

### Round three's pair, national figures, 200 periods

Set: f at 100 with d2 only; national figures; 200 periods. Quiet run still: True. Money conserved: True.

| world | run | class | hours p34 / p100 / last | last 20: hours | unmet | closes | prices U/F/C/S | owner's cash | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plain | P2 | holds a band | 220 / 219 / 238 | 188-240, mean 215.70 | 14.30/18.75/29.60 | none | 10.2/114.38/21/129.2 | 3487.87-5277.11 |  |
| plain | P4 | settles near target (3-period cycle) | 240 / 240 / 240 | 240-240, mean 240 | 0/0/1.30 | none | 12/25/30/38 | 762.86-782.86 |  |
| plain | P6 | settles elsewhere | 210 / 200 / 201 | 200-201, mean 200.20 | 10/24.70/30 | none | 12/25.63/21.75/96.9 | 2585.67-2643.87 |  |
| plain | P8 | settles elsewhere | 240 / 240 / 240 | 240-240, mean 240 | 0/1.15/9.85 | none | 9.9/25/24.75/38 | 420.87-525.12 | no top-ups; hours never under 228 |
| fund | P2 | still moving | 210 / 197 / 179 | 161-189, mean 173.60 | 15.70/11.40/30.65 | none | 10.2/31.88/19.5/119.7 | 1670.57-2170.31 |  |
| fund | P4 | settles near target | 240 / 240 / 240 | 240-240, mean 240 | 0/0/1.85 | none | 10.2/25/24.75/45.6 | 575.87-644.12 |  |
| fund | P5 | holds a band | 240 / 240 / 233 | 229-233, mean 231.50 | 0.05/2.05/8 | none | 9.9/21.25/21.75/51.3 | 679.37-731.91 |  |
| fund | P6 | still moving | 211 / 210 / 200 | 190-221, mean 207.25 | 9.20/14.50/27.85 | none | 12/22.5/23.25/100.7 | 1965.99-2208.77 |  |
| fund | P8 | settles elsewhere | 240 / 240 / 240 | 240-240, mean 240 | 0/1.10/7.95 | none | 10.2/25/23.25/38 | 355.86-432.65 | no top-ups; hours never under 228 |

## 3. The new push and the four rules, as built

### P8, a poor harvest that ends

P8 = Push::PoorHarvestEnds in tests/small_world/support.rs. It sets farm_output_per_batch = 9, as P2 does, plus
a new World field farm_yield_returns_at = Some(HARVEST_RETURNS), with HARVEST_RETURNS = 11. A new
World::catalogs() builds two catalogs, each admitted by MaterialCatalog::try_new: the world's own (yield 9), and
the same world with farm_output_per_batch = OPENING_FARM_YIELD (10) and no return. Catalogs::at(period) gives
the own catalog for periods 1-10 and the returned one from period 11 on. So the yield is poor for exactly 10
periods.

run_staffed now picks the catalog of each period and passes it to close_material_period, staffing_requests,
finish_with_staffing and snapshot. snapshot reads per-batch output from the catalog, so it must get the period's
catalog. spike.rs write_run does the same for line(), which reads input coefficients. The state carried between
periods is never touched.

Admission: each close runs canonical_state(catalog, opening) on the state it is given (catalog.validate, row
limits, services, merchants, routes). So period 11's close admits the carried state under the returned catalog,
and it did, in both worlds, for all 200 periods.

Nothing else had to change. The opening state does not depend on the pushed yield: the farm's output_buffer,
stock (40) and carrying values all use OPENING_FARM_YIELD, and only process_outputs carries the yield.

A new check in spike_rows, assert_harvest_returns, runs before any rows are written:
- P8's catalog at periods 1 and 10 equals P2's.
- From period 11 to u64::MAX it equals the quiet world's.
- P8 and P2 both open in exactly the quiet world's state (MaterialCircuitState equality).

P8 was added to the baseline pushes, so it runs in both worlds. summarize.py has P8 targets of 240 hours and
0/0/0 unmet, plus OPENING_STATE_TARGET = {"P8"}. That reports every price_next_ and cash_ column that differs
from the opening at the last period ("opening_state_distance_last" in summary.json). The full-state "returns to
opening" class is unchanged. The old script is kept as summarize-before-r4.py; for the old runs the new
summary.json entries equal r3-base-200's exactly.

The farm's plan in period 10 is made under the poor yield: the farm is not told in advance.

What today's engine does with it, as the measuring agent read the rows:

Nothing recovers by itself. In both worlds the run is ruined by period 200 even though the harvest comes back at
period 11. By the design's own test (back to 19/20 of the opening, 228 hours, within 65 periods and staying
there) both runs fail outright: after period 10 no period reaches 228 hours, and periods 66-75 average 130
(plain) and 123 (fund).

**While the harvest is poor (p1-10, the same rows as P2).**
- The farm makes 36 a period against 40 sold, and its stock drains 40 to 0 by p10. Its price holds at $25-26
  (plain) and $25-28 (fund), because the goods rule moves only once nothing is left.
- The farm plans ever more batches (5 up to 8-9) to rebuild its buffer. Its 40 staffed hours cannot make them,
  so it pays idle hours. Its cash rises from $880 to $1,657 (plain) and $1,760 (fund), while the owner's falls.
- Care sold falls from 40 to 13 (plain) and 3 (fund). The clinic cuts its price a dollar at a time ($30 to
  $25-27), as the service rule does when output runs under nameplate.
- Utility output falls from 120 to 88 (plain) and 80 (fund). Hours at p10 are 186 and 211. Unmet at p10 is
  6/10/27 (plain) and 0/19/37 (fund).

**After it comes back (p11 on).** Only the farm's physical side heals:
- It makes 40 a period again (4 batches on its 40 hours). Its stock refills to 39 by p18 in plain and to 40 by
  about p38 in fund.
- Unmet food in plain falls to 0-5 for a while.
- No price comes back. The farm's price stays $26 in plain (p10-p20) and rises to $29 in fund. It steps down
  only once stock is above the buffer (to $24 by about p40 in plain), so it never returns to $25 and keeps
  wandering ($19-35).

**What sinks it is the clinic.**
- Fund: at p13 care demand is 0. From p14 the clinic's cash cannot cover its wages and power for the 22-32 units
  then asked (spare from -$289 to -$615). It performs nothing, its cash falls to $1.10 by p15, and it never
  sells again.
- Plain: the clinic drifts down to 0 output by p35 with $5.10 left.
- With no output, the service price rule steps the clinic's price up a dollar every period against buyers it
  turns away: $187 (plain) and $215 (fund) at p200.
- The utility sheds its people (employed 15 to 3 in plain, 12 to 2 in fund). Hours slide to about 130 by p60-75,
  to about 100 by p100-120, and to 16-20 at the end.
- The farm and the shop stop at p164/p168 (plain) and p149/p147 (fund). The shop's price ratchets to $125 and
  $153.

**Who goes without, and where the money ends.** In the last 20 periods every account goes without almost all
food and care, and the owner too (it holds $2-157). The cash sits in workers' tills: w_utility holds $3,210
(plain) and $4,504 (fund), and w_shop $851 (plain). It sits idle there because there is nothing left to buy.

**Three plain conclusions.**
1. Ending the cause does not undo the damage. A workplace that has run out of cash has no way back, and no price
   returns toward the opening.
2. The ten-period shock does more harm than the permanent one in the fund world: the clinic closes at p13 in P8
   and never in P2. That is because small differences from p11 on (farm output 30 vs 27 at p12, care sold 14 vs
   18) push the clinic over the cash edge.
3. P8 is therefore a strong test for the round-four rules, and the baseline gives them no help.

### D: suppliers plan for their buyers' new plans

Switch: SPIKE_D: "on" turns the rule on. Unset or "off" leaves it off. Any other value panics. It is read once,
through a OnceLock in services::market::spike_d.

Where: rust/crates/babylon-material-circuit/src/transition/state.rs: close_material_period_with_portfolios no
longer calls services.plan before next_plans when D is on. next_plans takes an Option<&mut ServiceClose> and,
when it is given, runs services.plan between plan_production and plan_attendance; with D off the old order is
kept exactly. src/services/market.rs: update now visits markets in a new order under D (local services first,
the utility last). Under D it replaces planned_quantity with: owed + (demand_at_quote minus the business buyers'
part of it) + business_next, or the future orders if those are more. It adds spike_d(), SpikeDReceipt,
business_next() and moment_of(). src/clearing/table.rs: MarketTable gains a business side list with
record_business and business_at_quote. src/services/tiers.rs price_market and src/services/admission.rs
price_stage_market record what business buyers could pay for at the posted price. src/services/close.rs:
ServiceClose.spike_d, filled by plan(). src/model.rs: MaterialCircuitTransition.spike_d. lib.rs and services.rs
export the new items. tests/small_world/spike.rs rule_flows adds these columns for each service:
flow_d_base_plan_, flow_d_plan_, flow_d_beyond_ (plan minus today's plan, signed), flow_d_business_last_,
flow_d_business_next_ and flow_d_business_unpaid_. Patch:
patches/r4-D/0001-spike-D-services-plan-for-their-business-buyers-new-.patch

What it does:

At the close, the makers of goods plan first (plan_production). Then each service plans, local services before
the utility. Its plan is what households could pay for at its posted price in the period that closed, plus what
is owed, plus the service inputs that its business buyers' new plans need. That need is read from their freshly
set planned_batches, capped by each buyer's input policy and by what the buyer's cash above its floor pays for
at the posted price. Only after that are hours asked for every plan (plan_attendance) and goods prices set. Here
the business buyers are the farm and the clinic, both buying power, so the utility is the only service whose
plan the rule changes. It sees the farm's and the clinic's new plans in the same close.

Where it differs from the design's rule:

1) One pass in a fixed order (goods, then local services, then the utility). It does not repeat until plans
   rest, so it cannot handle recipes that run in circles. Here there are none, but A5 asks for repeated passes.
   2) Only services plan for their buyers' new plans. A goods supplier (the farm for the shop) still plans from
   what it sent this period plus its buffer. The shop's restock for the next period is placed only during that
   period, after production, so it is not known at the close. Households' plans are not known either, so the
   households' part is still what they could pay for in the period that closed. 3) Plans that the buyer's own
   people or nameplate cannot carry are counted in full, up to the input policy cap. That cap is twice the
   opening need and never binds. In P2/P8 the farm plans 5 to 9 batches while its 5 people can work 4, so the
   utility plans for power the farm can never use. The utility's plan reaches 125-143 against its 120-hour
   force, and the utility pays idle hours: plain P2 589 idle hours in p1-60, against 185 in the base. 4) Cash: a
   buyer's new need counts only as far as its cash at the close pays for it at the utility's posted price
   (business_unpaid records the rest). That is read at a different moment from today: at the close, after
   payouts, rather than at the next period's utility stage, after that period's wages. The business buyer's
   limit price (P5) is not applied to the new need. Nothing else reads money at a new moment. 5) Prices are
   untouched. The service price rule still cuts against nameplate (SpareCapacity), so the utility's price falls
   to $10 in most runs. 6) No orders for the next period are placed: the plan is a count, not an order, and the
   next period's market still clears from that period's requests. 7) The rule is measured alone, without f, d2,
   R, S, W or a, and only at the small world's figures: no national-figures run and no 400-period run.

### R: a service cuts its price only when it performed less than it planned

Switch: SPIKE_R, read once through a OnceLock in babylon_material_circuit::spike_r(). "on" turns the rule on.
Unset or "off" leaves it off. Any other value panics.

Where: rust/crates/babylon-material-circuit/src/services/market.rs: new spike_r(), a new enum Spare (Nameplate |
Planned{batches, per_batch}), a new fn under(), and changes to update() and quote(). The test quote() uses for
SpareCapacity is now under(row, spare_against); before, it was performed_quantity < available_capacity.
src/services.rs and src/lib.rs re-export spike_r. tests/small_world/spike.rs: rule_flows(catalog, before,
closed) reads the plan from the state the previous close left (the opening state for period 1, via
world.build().1), and write_run threads that state through. With the switch off, rule_flows returns no columns.
Patch:
patches/r4-R/0001-spike-R-a-service-cuts-its-price-only-for-buyers-who.patch.
Rows: out/r4-R-200/ (summary.json, summary.txt, table.json)
and out/r4-R-off-200/. Row reader: scripts/r4r_rows.py.

What it does:

With the switch on, a service steps its posted price down for spare capacity only when it performed less than
the batches it planned at the last close for this period, and its direct cost was below its receipts (or it
performed nothing). Nameplate capacity is no longer a reason. The plan is read from the recurring production
row's planned_batches in update(), before this close overwrites it, and is capped at nameplate
(available_capacity / quantity_per_batch). In period 1 that row holds the opening's plan (40 care, 120 utility),
so the rule judges against that. A service that planned 0 batches can never perform under its plan, so it holds
rather than cuts, even if it performed nothing. The steps up (FundedUnmet, PricedOut, CostPressure), the cost
test and the order of the tests are unchanged.

Where it differs from the design's rule:

1) The plan is compared in whole batches: a cut fires when performed_quantity.div_ceil(quantity_per_batch) <
   planned_batches. The state carries only planned_batches, not the planned quantity, and the receipts that hold
   the quantity are not carried between periods. For every service with 1 unit a batch (the clinic everywhere,
   and the utility in every run but P6) this is exactly the stated rule. Under P6 the utility makes 9 units a
   batch, so a shortfall of less than one batch (up to 8 units) under its rounded-up plan does not cut. The
   alternative, comparing units against batches times 9, would have cut a utility that sold exactly what it
   planned. I chose this before the first run and tried no other form. 2) "Planned for paying buyers" is the
   plan the engine stores (P14: demand at the quote plus what is owed, or future orders if more). It is not
   split into paying and non-paying parts. 3) The flow columns are measured in the harness, from the previous
   period's state, by the same reading the rule makes. flow_r_unused is planned units (batches times units a
   batch) minus performed, so under P6 it includes the rounding. 4) No other rule of the design (S, W, D,
   e-kept, f, d2, a) is on: this is R alone, at the small world's figures only, for 200 periods (not 400, and
   not at the national figures).

### S: a goods price steps up when the seller's stock stands under its buffer

Switch: SPIKE_S, read once through a OnceLock. "on" turns the rule on. Unset or "off" leaves it off. Any other
value panics.

Where: rust/crates/babylon-material-circuit/src/recurring/prices.rs: new pub fn spike_s(), a new
PriceDecision::UnderBuffer variant, and the Responsive arm of quote().
rust/crates/babylon-material-circuit/src/recurring.rs: re-exports spike_s.
rust/crates/babylon-material-circuit/tests/small_world/spike.rs: rule_flows() now writes
flow_s_under_{farm,shop} and flow_s_step_{farm,shop}. Patch:
patches/r4-S/0001-spike-S-a-goods-price-steps-up-when-the-seller-s-sto.patch.
Table helper: scripts/r4s_table.py.

What it does:

Under the Responsive goods price policy, with SPIKE_S=on, a seller's posted price steps up one step (saturating
at its ceiling) whenever its closing stock stands strictly under the policy's target_stock, whether or not any
buyer waited. The rule reads the same stock figure the price rule already reads: the seller's state.inventory
quantity at the very end of the close, inside update_prices. That is after household sales, production, dispatch
and the same-period restock (local transfers), and after next_plans has planned production. Inbound freight is
not counted. The other parts of the rule are unchanged: the step up when demand waited and stock is at or under
target (reason UnservedDemand, checked first), the cost-pressure step, and the step down when nothing waited and
stock is above target. A step taken only because stock is under the buffer is recorded as
PriceDecision::UnderBuffer. For a merchant that restocks to its target, this means the rule fires only when its
supplier could not fill the restock. For a maker whose buffer equals its target, it fires whenever this period's
sales and output leave it under the buffer, and it keeps firing until production rebuilds the buffer.

Where it differs from the design's rule:

1. The rule fires on stock strictly under target. Stock equal to target does not fire it, which is what keeps
   the opening still. 2. It reads only the closing inventory. Goods in transit are not counted: in the one-place
   small world all transfers are same-period, but in the country a merchant with freight on the way would read
   as under its buffer. 3. It is one step a period, the policy's own step ($1 here). No size scaled to the gap
   was tried. 4. It knows nothing of whether the seller is working: a stopped maker whose stock is under its
   buffer keeps raising its price every period (plain P2 farm, p121-200, $60 to $140). 5. When the stock is
   under target and the cost has also risen, the receipt says UnderBuffer, not CostPressure. The step is the
   same, and flow_s_step counts only the steps that today's rule would not have made. 6. Adding
   PriceDecision::UnderBuffer breaks the exhaustive matches in babylon-tick (recurring_receipt.rs) and
   babylon-persistence (qualification_audit/economic.rs, production_projection/prices/projection.rs). Only the
   small_world test binary was built on this branch. 7. Only the small world's figures ($1 steps, one period of
   cash) were run, for 200 periods. The national figures and 400 periods were not run.

### W: raw goods and power move in large steps and open where a short market closed

Switch: SPIKE_W, read once through a OnceLock. "on" turns the rule on; unset or "off" leaves it off; any other
value panics. The multiple is the constant SPIKE_W_MULTIPLE = 4, fixed before the first run. No other value was
tried.

Where: Engine:
- src/recurring/prices.rs: spike_w() (the switch), SPIKE_W_MULTIPLE, spike_w_mark_raw() (the caller hands in the
  raw (site, good, unit) keys; the engine names none), spike_w_raw(key), spike_w_open(stepped, closing,
  maximum). update_prices reads the closing price and the unit cost for a raw key and passes them to quote().
  quote() takes the four-fold step, the cost floor on a step down, and then the open at the closing price.
- src/services/market.rs: update() reads the closing price for a raw service. quote() takes the four-fold step,
  the floor of direct cost per unit performed on a SpareCapacity step down, and the open at the closing price.
- src/clearing/table.rs: MarketTable::closing_price(site, good, unit). It returns the highest clearing_price
  among this seller's short-market receipts of the period where clearing_price > quote_price, and None
  otherwise.
- src/recurring.rs: re-exports the switch and the mark function.

Harness:
- tests/small_world/support.rs: where the offers are built, it marks (utility, power) and (farm, food) as raw.
- tests/small_world/spike.rs: rule_flows writes flow_w_step_{farm,utility}, flow_w_open_{farm,utility} and
  flow_w_floor_{farm,utility}. Each period it also recomputes rule W's price from the receipts and asserts it
  equals the posted next price. The assertion held in all 17 runs for 200 periods.

Patch:
patches/r4-W/0001-spike-W-raw-goods-and-power-step-four-fold-open-at-a.patch.
Rows: out/r4-W-200/ (with summary.json), and the OFF check
in out/r4-W-off-200/. Row reader: scripts/r4w_rows.py.

What it does:

For a product the harness marks as raw (the farm's food, the utility's power), each posted-price step is four of
the product's own steps ($4 at the small world's figures), up or down. The reasons for a step are today's:
unserved demand or cost pressure for goods; funded-unmet, priced-out, cost pressure or spare capacity for
services. A step down stops at the seller's direct cost of the period and at the policy's floor. After a period
in which a short market of that seller's product cleared above its quote, the next posted price is the clearing
price, under the ceiling, when that is higher than the stepped price. When the market was not short, or was
short but cleared at the quote, the rule only takes the four-fold step and the cost floor. The closing price is
read from the period's MarketTable rows, the same data as the MarketClearingReceipt rows. Direct cost for goods
is GoodsPriceCostEvidence::unit_cost() (this period's produced or released unit cost, rounded up). For a service
it is ServiceMarketReceipt.direct_cost divided by performed_quantity, rounded up: the same basis today's
CostPressure and SpareCapacity tests use. A period with nothing produced or performed has no cost floor beyond
the policy minimum.

Where it differs from the design's rule:

1. "Raw" is a process-wide list (a Mutex'd set) that the harness hands to the engine. It is not a field of the
   price policy or catalog, so it is not carried in the state, the wire or the digest.
2. The reasons for a step are today's reasons. The rule is not combined with A1, R, S or e-kept: a service still
   cuts for running under nameplate, and a goods price still waits for unserved demand.
3. The closing price comes only from this seller's own short market (the farm's restocking market, the utility's
   market). A short market downstream, such as the shop's household food market, does not count.
4. A service's direct cost is spread over the units performed, not those produced. Expired units raise the
   floor.
5. A period with no production or performance has no cost floor.
6. Price receipts keep today's reason enum. A goods price that a closing price raised from a Hold or ExcessStock
   decision keeps that reason, and the flow_ columns carry what W did instead. No new reason variants were
   added.
7. A2's "large step down when offered goods go unsold" is today's ExcessStock or SpareCapacity condition at four
   steps. It is not A1's buffer-and-sold test.
8. Only the small world's figures were run (no SPIKE_STEP_BPS or SPIKE_J_PERIODS: those switches are not on
   spike/r4-base), and only for 200 periods, not the design's 400.

## 4. The questions, as the measuring agent answered them from the rows

These are the measuring agent's own words. Section 5 lists what the independent check refuted in them; where the
two differ, the check holds.

### Does the economy come back after a shock that ends?

Under core, no run returns to its opening state, at either set of figures. The design's own test is 228 hours
and needs met in each account (within 2 of 40 per product), from period 76 (11 + 65) and staying there. Under
core no run meets it.

SMALL FIGURES, core (r4-core-200 and r4-core-400; identical through p200).

Periods 1-10:
- The farm's price rises $4 a period from p1. S's under-buffer step is made four-fold by W: 29, 33 ... 65 at
  p10. The stock drains 36 to 16-20.
- The shop's buyers of food do not answer that price. The shop pays it: its cash falls from $1,400 to $20 at p6.
  d2 tops it up ($120, then $380).
- The shop's posted price climbs $1 a period on cost pressure: 38 to 46 at p10.
- The clinic's cash falls ($167 at p7, plain). Care unmet reaches 34-38 at p7-p10.

After the harvest returns (p11):
- Plain: the farm's stock jumps above its buffer (51 at p11). Its price then steps down $4 a period (ExcessStock
  with W) to its $20 cost floor by p22.
- Fund: the stock sits at 22 until p15, so S keeps raising the price to $89 at p16. It falls to $20 only by p34.
- The shop's price goes on climbing on cost pressure to $53 (plain, p17-19) and $63 (fund, p27). It comes down
  $1 a period only afterwards, through e-kept: offered, unsold, nobody waiting. It reaches $34-37 by p40.
- Meanwhile the shop hoards cash: $2,500 plain at p23-28, $3,240 fund at p37. The clinic is starved: $108-250 in
  cash. The owner is drained by top-ups: plain $1.66 at p37-40, fund $16-51 at p51-70. With the owner empty, d2
  has nothing to give.
- Hours fall AFTER the harvest is back: plain 141 at p26 (p21-30 mean 165), fund 137 at p37.

The recovery:
- Plain: hours stay >=228 from p103. Unmet food and utility reach 0 from about p121. But the owner lacks 10 care
  every period to p400, in a 3-period cycle.
- Fund: hours stay >=228 from p97, and every need is met from p109. The run is exactly still from about p110 to
  p400.

Where they rest:
- Fund rests at 240 hours and 0/0/0 unmet. Prices 10/24/36/34 against 12/25/30/38. Cash: utility $1,403 (opened
  $1,200), farm $1,474 ($880), clinic $1,201 ($880), shop $645 ($1,400), owner $655 ($640). The benefits fund
  holds $480 (opened $960). Every standard is back to getting_by.
- Plain rests at 240 hours with prices 10/28/24/38. Cash: utility $1,314, farm $1,559, clinic $1,338, shop $400,
  owner $504 ($800). The owner is still going without.
- So the economy comes back to full work and (fund) full needs, but late, at other prices, and with money moved
  from the shop and the fund to the farm, clinic and utility.

NATIONAL FIGURES, core (r4-core-nat-200/400). It never returns.
- The farm's price rises $2.50 a period: 27.5 at p1, 50 at p10, 55 (plain) and 60 (fund) by p14-15.
- Hours stay 238-240 through p11 (plain), then fall to 201 at p32 (plain) and 205 at p39 (fund).
- The farm's price holds at $55-60 through p40. The 50-period windows show $41.75 over p51-100, then $21-23 from
  p101 on. The reason it holds: stock stands exactly at the 40 buffer and all 40 sell, so S does not fire,
  ExcessStock needs stock above target, and e-kept needs goods beyond the buffer to go unsold. Nothing steps it
  down.
- The shop's posted price climbs $0.95 a period: 38 to 73 at p40, about 100 by p100, then held at 97-106 to
  p400. Its own market is short every period (40 offered, 41-50 asked) and clears within the period at about
  $103 (ADR312).
- Hours rest at about 222-226 (plain) and 202-210 (fund) at p101-400.
- Workers lack 10-10.5 food, 13-16 utility and 27-31 care. The owner holds $2,000-3,500 and is affluent. The
  fund treasury holds $2,693 at p200, the benefits fund $400.
- By contrast, the pair and no-prices at the national figures rest at 240 hours after P8 with no top-ups. Their
  prices are 9.9-10.2/25/23.25-24.75/38, but the owner still lacks 7.8-9.8 care.

### Does a lasting shortage settle?

Under core no lasting shortage settles near target, and at 400 periods two runs at the small figures end in
ruin.

SMALL FIGURES (core-200, core-400).
- Plain P2 slides: 185 at p181-200, 222 at p381-400. The owner lacks 9/9.2/10. Top-ups ($18,923 by p400) never
  stop.
- Fund P2: the clinic closes from 159. At 400 periods the clinic, shop and farm stop from 371-381 and hours fall
  to 43. The owner is drained to $0 by p40-80 and stays near 0, so d2 has no money behind it.
- Plain P6 is still moving at 208 (p200). At 400 the clinic runs dry (p281-320). Then the utility, farm and shop
  prices run away ($121/$150/$116/$68 averages at p321-360, up to farm $183), and the farm and shop stop from
  347 and 314.
- Fund P6 slides: 212, then 195.5 at 400, swinging 128-233. The farm hoards $2,900-3,300.

NATIONAL FIGURES (core-nat).
- No closures in 400 periods.
- P2 rests at 218-235 hours and P6 at 209-231, still moving or sliding.
- The shop's price ratchets from $38 to about $100 by p100. It then holds a band of $97-106 to p400: no climb
  without end, and no way back.
- The farm's price returns to about $21-24. Utility is at $10-12 and care at $21-23 (both below opening).

Who goes without at the national figures: the workers. w_utility lacks 12-15 care, 6-12 utility and 1.7-4.2
food. The supported account lacks 8 care and 3-4 utility. Meanwhile the owner holds $1,900-3,400 and the fund
world's treasury $1,800-2,700.

The pair does better on every lasting shortage:
- Small figures: 229-236 hours, the owner going without.
- National figures: 174-216 hours, the workers going without, the shop at $97-130.

Ratchets under core:
- S with W on the farm, at both figures, while stock is under the buffer.
- Cost pressure on the shop.
- A stopped clinic's posted price stepped up by turned-away buyers: $110-124 after closing in fund P2 at 400.

### The pushes on the side of demand

P4 (the clinic pays a tenth more):
- Under core it settles near target at the small figures in both worlds: 240 hours. Plain care unmet 4.85 (the
  owner's), prices 12/25/27/38. Fund care 1.1, prices 12/25/30/38. These are the same as the pair.
- At the national figures plain P4 is back at the opening prices with 240 hours and 1.3 care unmet, as with the
  pair.
- But fund P4 at the national figures is worse under core: a band of 196-236 (mean 216) at p200, then 196.75
  still moving at p400. Workers lack 12 care, the shop sits at $100.7, top-ups go on. The pair holds 240 hours
  with 1.85 care unmet.

P5 (the fund's taxes cut by a quarter, fund world only):
- Under core it is worse than the pair at both figures.
- Small: still moving 205-240 (mean 228) at p200, and 228.65 at p400 with top-ups never stopping. The owner
  lacks 5.6/6.4/7.9 and the supported account 1.6 utility and 5.7 care. The pair settles at 240 hours with 4.35
  care unmet (supported).
- National: slides, 207.4 at p200 and 202.75 at p400. Workers and the supported account lack 9/16-18/30. The
  pair is at 231.5.
- Removing S restores 240 hours in P5 at both figures (unmet care 4.3 small, 5.85 national).

### What each part carries

Each part, read from the variant with that part taken away. Hours are last-20 means at 200 periods, small
figures and national figures.

- f (no-advance). Without f the core collapses at the small figures. Every pushed run but plain P4 and fund P5
  stops for good: hours 2-50, prices in the hundreds, $235,000-375,000 of top-ups circulating in the P6 runs. At
  the national figures nothing stops, but hours fall to 174-195. f carries the most.

- a, lent hands (no-hands). Inside the core, a is load-bearing. This is the reverse of round three, where a
  harmed the pair. Without it, at the small figures: fund P8 is ruined (all three goods workplaces stop from
  p103-111), plain P2 falls to 139.5, and plain P6's clinic closes. At the national figures: both P2s and plain
  P6 are ruined (plain P6 to 0 hours), and the clinic closes in fund P4 and plain P8.

- D, plans through the chain (no-plans). D holds the clinic in P6 at the small figures: without it the clinic
  closes in both worlds and plain P8 rests at 207.6 with the owner lacking 10/10/10. Without D, fund P8 is
  better (237.6, still moving) and plain P2 is somewhat better in unmet but slides (220.6). At the national
  figures removing D changes little (within a few hours).

- S, the under-buffer step (no-signal). S is harmful. Removing it raises every pushed run except fund P6 small,
  which falls 212 to 190. Small figures: fund P2 154 to 240, plain P2 185 to 240, fund P5 228 to 240, plain P6
  208 to 228, P8 to 240. National figures: fund P4 216 to 240, fund P5 207 to 240, fund P8 210 to 240, plain P8
  226 to 240, with prices near the opening and only the owner's care unmet.

- W, raw goods swing (no-raw). Mixed. Small figures: removing W helps plain P2 (185 to 235) and fund P2 (154 to
  188), but fund P6's clinic closes (212 to 158) and fund P8 slides (235). National figures: about even, with
  fund P8 slightly worse (210 to 203).

- R, e-kept, S and W together (no-prices, which is f, d2, a and D). Removing all four gives the best set
  measured. Small figures: all pushed runs at 234-240 hours, unmet only for the owner and the supported account,
  but $8,000-18,000 of top-ups in P2/P6/P8. National figures: P4, P5 and P8 at 240; P2 and P6 at 198-237 with
  workers going without.

- The pair (f and d2) is about as good as no-prices at the small figures (229-240) with far fewer top-ups
  ($322-7,120). At the national figures it is worse on P2 and P6 (174-216).

R and e-kept alone were not taken away separately: the task's variants remove them only together, in no-prices.

### Who goes without, and where the money ends

Under core, at the small figures, the owner goes without and is the one drained:
- In P2, P5 and P6 the owner lacks 4.7-9.6 food, 6.4-9.6 utility and 7.9-10 care, while it pays $4,453-12,149 of
  top-ups and holds $0-1,196.
- In fund P2 everyone lacks care, and the clinic is closed.
- Plain P8 leaves only the owner short (10 care). Fund P8 leaves nobody short.
- The money ends in the workplaces: farm $869-3,014, utility $836-1,572, shop up to $3,302 (plain P2). In fund
  P2 at 400 it ends with w_utility ($5,174) after the ruin.

At the national figures the workers go without, in every pushed run but plain P4:
- w_utility lacks 12-15 care, 7-11 utility and 1.4-4.5 food.
- w_clinic, w_farm and w_shop lack 2-5 care and 1-2 food each.
- The supported account lacks 8 care, 3-5 utility and 3-4 food.
- The owner lacks nothing and is affluent or comfortable, holding $1,885-3,436.
- The money ends with the shop ($2,900-3,000), the owner ($2,000-3,400), the fund world's treasury
  ($1,800-2,700, which opened at $160) and the farm ($1,300-1,900).
- Worker households hold $0-25 each.

### Where prices end, and whether the owner keeps a profit

Where prices end under core:
- Small figures: utility $10-15 (opening 12), farm $20-38, clinic $22-65, shop $31-42.
- Utility at $10 is its direct cost, and W's cost floor is exactly where today's rule already ends.

Whether the owner keeps a profit:
- Small figures: it does not. The owner ends at $0-655 and in P2/P5/P6 near $0, because d2 drains it into
  top-ups.
- National figures: it does. The owner holds $1,885-3,436, fed by the shop's food sold at about $100 in a market
  that is short every period.

Which prices come back after a shortage ends (P8):
- The farm's price comes back down at the small figures in plain (via stock above its buffer, ExcessStock with
  W, to its cost floor). In fund it comes back only after S stops (p17-34).
- The shop's price comes down $1 a period through e-kept once cost pressure ends (small figures: to 34-38).
- At the national figures the farm's price falls back only after about p60-100. The shop's never does: it holds
  about $100 to p400, because its short market keeps clearing at about $103.
- Service prices: the clinic ends at $24 (plain P8) and $36 (fund P8) against 30. Utility ends at $10 against
  12. R holds cuts but nothing raises them back.

### What is still moving at the end

Still moving at the end of the longest run (core-400 and core-nat-400):
- Small figures: plain P2 (slides, 222), fund P6 (slides, 128-233) and fund P5 (band 200-240).
- Plain P6 and fund P2 end in ruin after p314-381.
- National figures: fund P4 (still moving, 196.75), fund P5 (slides, 202.75), fund P6, fund P8 and plain P6
  (still moving), plain P2 (slides, 235.45).

Top-ups that never stop, paid in p381-400:
- Small: plain P2 $303, plain P6 $3,720, fund P5 $340, fund P6 $94.
- National: plain P2 $704, plain P6 $166, plain P8 $257, fund P2 $694, fund P4 $512, fund P5 $1,129, fund P6
  $454, fund P8 $505.
- They stop only in P4 and the small-figure P8 runs.

Workplaces under one period of their outlay (spare cash below 0 in the last 20 periods of the 400 runs):
- National: the utility (-105 to -360) and the clinic (-10 to -30) in every pushed run but plain P4.
- Small: fund P6 utility -446 and clinic -871; fund P2 clinic -697; fund P5 utility, farm and shop; plain P2
  clinic and shop.
- The shop is under its own outlay in most runs at the small figures: plain P8 ends with the shop at $400
  (opened $1,400).

### What the design, as built here, does not mend

What the design, as built here, does not mend.

1. It does worse than round three's pair. Core holds fewer runs than f+d2 at both figures: fund P2 runs away
   (clinic from 159; total ruin by p381 at 400), and plain P6 is ruined at 400.

2. The price rules as built make things worse. no-prices (f, d2, a, D) beats core in nearly every run. S is the
   most harmful part: no-signal raises most runs to 240.

What the rows show for item 2:
- S's step finds no buyer that answers it. The shop's restock order takes target minus stock whatever the price.
  So the farm's price climbs $4 a period at the small figures and $2.50 at the national ones, while its stock
  drains on the same schedule.
- That passes into the shop's cost pressure, and from there to households.
- A goods seller whose stock stands exactly at its buffer and sells all it offers has no step down under A1 as
  read here. So the farm holds $55-60 at the national figures for 50-90 periods.

3. At the national figures, the shop's market stays short every period and clears within the period at about
   $103 (ADR312). The posted price climbs to meet it and holds there to p400. Workers are priced out of about 10
   food while the affluent owner buys.

4. d2's owners are finite. At the small figures the owner is drained to $0, and from then on d2 tops up nothing
   (fund P2, plain P6, fund P6). Top-ups are never paid back, and at the national figures they never stop.

5. The fund world's treasury accumulates $1,800-2,700 while the supported account lacks 8 care. The benefits
   fund falls from $960 to $400.

6. No P8 run comes back within 65 periods, and none to the opening's prices and cash.

What the rows suggest is missing (CONJECTURE, not measured):
- A downward test for a seller at exactly its buffer whose price rose in a shortage. For example, stepping down
  when the price stands above the cost-based or pre-shortage level and the market is not short.
- Making S answer only when a buyer can switch. A4, the cheapest seller, needs a second seller: S's step has
  meaning only when buyers can leave.
- Real credit in place of d2. Owners' finite cash is the binding limit at the small figures.
- A bound on how far a short market's within-period price can carry the posted price, or a second shop.
- Rule A3's 'cut work first' was not tested: no prototype lays off before cutting price.

### What surprised the measuring agent

1. The whole design does worse than round three's pair (f at 100 with d2) in most runs, at both sets of figures.
   - The best set measured is no-prices: f, d2, a and D with today's prices.
   - Of the new price rules, S does the most harm, and W is mixed.

2. Rule a was harmful in round three (with f and d2). Inside the core it is load-bearing: without it, runs are
   ruined at both sets of figures.

3. Small figures, core, fund P8: this is the first run in four rounds to come back after the harvest returns.
   - It reaches 240 hours with every need met and is exactly still from about p110 to p400.
   - It does so only after p97-109, and at other prices and other cash.
   - At the national figures, core does not come back at all. The pair and no-prices do: 240 hours, prices near
     the opening, the owner short of care.

4. Under core, hours fall further AFTER the harvest returns than during it: 141 at p26 (plain) and 137 at p37
   (fund). The cause is the farm price that S and W pushed up, which moved cash into the shop and drained the
   clinic and the owner.

5. At the national figures the shop's food sells at about $103 every period, in a market that is short each
   period (ADR312's price rising inside the period). Its posted price climbs to meet that price and holds there
   to p400.

6. Switches and reproduction.
   - On round three's branch d2 was on unless SPIKE_D2=off. Here it is on only with SPIKE_D2=on, so that every
     switch is off when unset.
   - e had no switch at all, so it was given SPIKE_E.
   - With those changes, every rule alone still reproduces its own branch's rows exactly.

7. W's per-period price assertion held in every run where W is on, including with S's UnderBuffer and e's Unsold
   reasons.

### What was not done

Things not done:
- Rule A4 (a second seller) was not built, as the task said. No new rule was built.
- D is the services-only, one-pass form its own agent built.
- e is round one's e as built: the e-kept reading plus its planned gain for sellers stepping down, in goods and
  services.
- R and e-kept were not taken away one at a time. The task's variants remove them only together, in no-prices.
- Only core was run for 400 periods. Every other variant has 200.
- No second reader checked these rows.
- No parameter other than the given ones was tried: f at 100, W's multiple 4, the national figures at 250 bps
  and 2 periods of cash.

Where the artefacts are:
- Rows are under out/, in r4-<name>[-nat]-200, r4-core-400,
  r4-core-nat-400, r4-all-off-200 and c4-* (the checks). Each has a summary.json and summary.txt.
- Logs are in logs/.
- Scripts are in scripts/: r4run.sh, r4variants.sh, r4table.py, r4back.py, r4path.py and r4win.py.
- The patch is in patches/r4-all/.

State of the worktree:
- It is left on spike/r4-all at b0425b713, and the tree is clean.
- codex/households-and-homes is untouched at ef3a8b3bb.
- No background process was started.

## 5. The independent check

A second reader recomputed the claims from the rows and read every prototype branch. It judged 24 claims.

### Claims it refuted

- Claim: S alone, fund P5: 'closes: none'
  Evidence: The farm makes 0 from p197 and the shop from p196, through p200 (out_farm 0,0,0,0 for p197-200).
  Correction: The farm and the shop stop at p196-197, so the run is entering ruin at its last period.
- Claim: Core-400, small figures: plain P6 ruined (farm from 347, shop from 314), fund P2 ruined (farm 381,
  clinic 371, shop 375), fund P6 'slides, 195.5, closes: none', plain P2 222.15, fund P5 228.65
  Evidence: The hours and the top-ups match: plain P2 $18,923, plain P6 $46,868. But in fund P6 the clinic
  performs 0 from p392 (out_clinic 0 in 8 of the last 9 periods), its cash falls from $723 to $1-18, and care
  unmet is 40 in p392-400. The shop's out=0 runs from 388 in fund P2 and from 313 in plain P6.
  Correction: Fund P6 at 400 is not merely sliding: its clinic stops at p392 with no cash left, so three of the
  core's runs at the small figures (plain P6, fund P2 and fund P6) end in or near ruin by p400.
- Claim: Lasting shortage: 'The pair does better on every lasting shortage' (and still_broken 1: core holds
  fewer runs than f+d2 at both figures)
  Evidence: Small figures: the pair is better (P2 234.25/235.65 against 185.30/153.95; P6 235.25/228.65 against
  207.75/212.50). National figures, last-20 means at 200, core against pair: plain P2 233.75 vs 215.70, fund P2
  211.40 vs 173.60, plain P6 231.65 vs 200.20, fund P6 216.20 vs 207.25. Core is better on all four lasting
  shortages there. The pair is better on fund P4 (240 vs 216.10), fund P5 (231.50 vs 207.40) and both P8s (240
  vs 226.25/209.55).
  Correction: At the national figures core beats the pair on every lasting-shortage run (P2, P6) and loses on
  the demand pushes and P8: 4 against 4, with plain P4 even. 'Worse than the pair in most runs at both figures'
  holds only at the small figures.
- Claim: S is harmful: removing it raises every pushed run except fund P6 at the small figures
  Evidence: Small: holds (plain P2 185.30 to 240, fund P2 153.95 to 240, fund P5 227.85 to 240, plain P6 207.75
  to 228.35, P8 240 to 240 but with more unmet, fund P6 212.50 to 190.05). National: fund P6 216.20 to 205.85
  and plain P2 233.75 to 231.40 both fall. Fund P4, fund P5 and both P8s rise to 240.
  Correction: Removing S raises most runs, but lowers fund P6 at both figures and plain P2 at the national
  figures. At the small figures it also makes P8 worse on needs: unmet 0/0/0 under core against 0/3.75/8.1
  without S (fund).
- Claim: Without D, fund P8 is better (237.6, still moving)
  Evidence: r4-no-plans-200 fund P8: 237.60 hours, unmet 1.45/1.90/5.25, top-ups $4,044. Core fund P8: 240
  hours, 0/0/0, still. Plain P2 without D is 220.60 against core 185.30, better in hours too, not only in unmet.
  The clinic closes in P6 without D (plain 185, fund 162) and plain P8 rests at 207.60 with the owner lacking
  10/10/10: these hold.
  Correction: Without D, fund P8 is worse than core. D is load-bearing for fund P8 and both P6s at the small
  figures, and harmful for plain P2.
- Claim: Core without a: plain P2 'closes: none'
  Evidence: r4-no-hands-200 plain P2: out_clinic 0 from p192 to p200, after 1 at p191.
  Correction: The clinic stops at p192.
- Claim: At the national figures the shop's market is short every period (40 offered, 41-50 asked) and clears
  within the period at about $103, which holds its price near $100
  Evidence: Core-nat, last 100 periods: the shop's market is short in 16-49 of 100 periods (plain P2 19, plain
  P8 36, fund P4 49, fund P8 42). In the last 20 it is short in 3-11. Demand ranges 37-44, sold 37-40. The price
  alternates +-$0.95 (e.g. p381-390: 103.55, 102.6, 101.65, 100.7, 101.65 ...). Mean over p101-400 is $102.66
  (plain P8) and $98.79 (fund).
  Correction: The shop's price rests in a band of about $97-106, where demand roughly equals its 40, short about
  a third of the time. Workers are priced out of about 10 food while the owner buys. It is a resting price set
  by who holds the money, not a market short in every period.

### Claims it could not settle

- Claim: Who goes without at the national figures: workers in every pushed run but plain P4; the owner lacks
  nothing and holds $1,885-3,436; worker households hold $0-25
  Evidence: Owner unmet is 0/0/0 in every core-nat pushed run but P4 (plain P4 owner care 1.3). The owner's
  last-20 mean cash is $2,006-3,294. Worker accounts carry all the going without, with the supported account in
  fund. But worker cash reaches $49-51 (plain P8). The owner's standard is getting_by, not affluent or
  comfortable, in fund P4 and P8 at 200. The farm holds $911 (fund P8) and $1,184 (fund P2), under the stated
  $1,300-1,900.
  Correction: The substance holds; the cash ranges are loose.

### Claims that hold

- Claim: With every switch off, spike/r4-all reproduces spike/r4-base, and each single-rule branch's OFF run
  equals the base
- Claim: Each rule alone and each round-three set on spike/r4-all reproduces its own branch's rows
- Claim: Quiet runs are still and money is conserved in every r4 variant
- Claim: Baseline P8: rows equal P2's through p10; after p10 no period reaches 228 hours; highest 205 at p22
  (plain) and 197 at p13 (fund); p66-75 mean 130.2 and 123; clinic closes from 35 (plain) and 13 (fund); money
  5160 and 6120
- Claim: Single-rule tables (D, R, S, W alone): hours at p34/p100/last, last-20 band and mean, unmet, prices,
  owner cash
- Claim: Core, small figures, 200: hours, unmet, closures, prices, owner cash and top-ups as tabled (plain P2
  185.30, fund P2 153.95 with the clinic from 159, P4 240, fund P5 227.85, P6 207.75/212.50, P8 240/240; top-ups
  12,149 / 11,222 / 4,453 / 11,690 / 6,868 / 4,316 / 3,527)
- Claim: Core, national figures, 200 and 400: last-20 hours, unmet, prices, owner cash, no closures
- Claim: Back after a shock that ends (P8), core, small figures: fund reaches >=228 hours from p97, every need
  from p109, and is exactly still from about p110 at prices 10/24/36/34 with cash utility 1,403, farm 1,474,
  clinic 1,201, shop 645, owner 655, fund 480; plain reaches >=228 from p103 and rests with the owner lacking 10
  care; neither passes the design's test
- Claim: Back after a shock that ends, core, national figures: never returns
- Claim: The pair and no-prices at the national figures rest at 240 hours after P8 with no top-ups, prices near
  the opening, the owner short of care
- Claim: Parts: without f, ruin at the small figures (hours 2-50, $235k-375k of top-ups in P6), 174-195 at
  national; without a, ruin (fund P8 small; both P2s and plain P6 national); no-prices is best; W mixed
- Claim: National farm price climbs $2.50 a period to 55 (plain) / 60 (fund) and holds there with stock exactly
  40 and all 40 sold, then falls to $21-23 from p101
- Claim: Core small P8 path: farm price +$4 a period to 65 at p10; shop cash 1,400 to 20 at p6; shop price 38 to
  46 at p10; plain stock 51 at p11; fund stock 22 to p15 and farm price 89 at p16; hours 141 at p26 (plain) and
  137 at p37 (fund)
- Claim: Top-ups that never stop: paid in p381-400 small (plain P2 303, plain P6 3,720, fund P5 340, fund P6 94)
  and national (704, 166, 257, 694, 512, 1,129, 454, 505)
- Claim: Workplaces under one period of their outlay in the last 20 of the 400 runs: national utility (-105 to
  -360) and clinic (-10 to -30) in every pushed run but plain P4; small fund P6 utility -446, clinic -871; fund
  P2 clinic -697
- Claim: Demand pushes: P4 settles near target under core at the small figures, but fund P4 at the national
  figures is 216.10 then 196.75 at 400; P5 is worse than the pair at both figures; removing S restores 240 in P5
  at both

### Were the prototypes honest?

- spike/r4-base (P8): honest = True. None found. The poor yield (9) holds for periods 1-10. From period 11
  (HARVEST_RETURNS) the harness picks a second catalog that differs only in farm_output_per_batch =
  OPENING_FARM_YIELD. The opening state is asserted equal to the quiet world's and P2's, the carried state is
  untouched, and the rows equal P2's through p10 and differ from p11.
- spike/r4-D: honest = True. No site, product or period is named, and the rule is behind SPIKE_D (OnceLock). The
  order is fixed: goods plan_production, then services sorted by (is-utility, index), then plan_attendance. Each
  service reads only plans set earlier in the same close: the farm's planned_batches, and the clinic's
  planned_batches written in the loop before the utility. No figure from the future is read. As declared, it is
  one pass and services only. It counts buyer needs that the buyer's own people cannot carry, which leads to
  paid idle utility hours. It reads buyers' cash at a new moment (the close).
- spike/r4-R: honest = True. It is behind SPIKE_R and names nothing. It reads last close's planned_batches
  before overwriting them, capped at nameplate. The comparison is in whole batches, as declared (under P6, up to
  8 units of shortfall go unseen).
- spike/r4-S: honest = True. It is behind SPIKE_S, names nothing and steps one policy step on stock < target.
  The new PriceDecision::UnderBuffer variant breaks exhaustive matches in babylon-tick and babylon-persistence
  (declared), so the branch does not build workspace-wide.
- spike/r4-W: honest = True. The multiple is the constant SPIKE_W_MULTIPLE = 4, as reported. The engine names no
  site or product: the raw set is a process-wide Mutex the harness fills with (utility, power) and (farm, food).
  The floor of direct cost applies only to a step down: a held price or a period with no output has no cost
  floor. So 'never under direct cost' is not guaranteed in general, only that no W step-down crosses it. The raw
  marking lives outside catalog and state (declared).
- spike/r4-all: honest = True. Ten commits (f, d2, i, j, a, D, R, S, W, e). Every switch is OFF when unset, and
  the runner sets exactly the reported variants. There is no f64/f32 in the diff and no site, account or period
  is named in the rules (d2 and lent hours iterate generically). Money is conserved in every run. Minor:
  SPIKE_E_KEPT is read with std::env::var on each call rather than once.

### What the check says is left unsaid

The answers leave out several things a decision needs:
- **No variant passes the design's own test after P8, at either set of figures.** That includes the pair and
  no-prices: they hold 240 hours, but the owner lacks 7.85-10 care. Only core fund P8 at the small figures ever
  meets every need in each band, and it does so from p109, 33 periods after the p76 deadline. Its full state is
  still only from about p128.
- **Core at the small figures ends in or near ruin at 400 in three runs, not two.** Fund P6's clinic stops
  performing at p392 with $1-18 of cash and 40 care unmet. In S alone, fund P5's farm and shop stop at p196-197.
  In core without a, plain P2's clinic stops at p192. The tables say 'none' for all three.
- **The ablations' verdict differs by figures.** At the national figures, core beats the pair on every lasting
  shortage (P2 and P6). S's removal lowers fund P6 at both figures and plain P2 at the national ones. D's
  removal makes fund P8 worse at the small figures.
- **Which parts are needed depends on the figures.** f and a are load-bearing at both; removing either ruins
  runs. S hurts most runs but helps fund P6. W is mixed. R and e-kept were never removed separately, so whether
  either is needed or harmful is unknown.
- **The national shop price is not held by a permanently short market.** It rests around $100, where demand
  roughly meets 40, because money sits with the owner and the shop. Its market is short only in 16-49% of
  periods. So the remedy the report conjectures (bounding the within-period clearing price) addresses the wrong
  mechanism.
- **Workers go without needed food, power and care in every national pushed run but P4.** That happens while the
  treasury holds $1,858-2,693 and the owner $2,000-3,300. At the small figures the owner goes without instead.
- **Workplaces sit under one period of their outlay at the end.** At the national figures the clinic (cash
  $371-568 against a $1,760 opening) and the utility are in every pushed run. The farm is in some national fund
  runs. The shop is at $400 in core plain P8.
- **Top-ups never stop in 12 of the 400-period runs**, and they are never repaid.
- **Every result rests on parameters never varied:** f at 100, W at 4, one sequence of D, 200-period ablations
  only.
- **The rows do not show** what the design's other tests need: pace, marks, pay both ways, and sellers competing
  (A4 is not built).

### Its summary

No at either set of figures. At the small world's figures only fund P8 comes back to full work with every need
met, from p97-109 against the design's p76 deadline, and it settles at other prices and cash; plain P8 recovers
its hours but the owner lacks 10 care, and at the national figures no P8 run returns. Every reproduction check
holds when recomputed from the rows: all-off and each rule's OFF run equal the base byte for byte, each rule
alone and each round-three set equal their own branch's rows, quiet runs are still and money is conserved. Most
tabled figures recompute exactly, but several claims are refuted. 'The pair does better on every lasting
shortage' fails at the national figures, where core beats the pair on P2 and P6; removing S lowers fund P6 at
both figures and plain P2 at the national figures; removing D makes fund P8 worse; the national shop market is
short only a third of the time, not every period; and three runs listed as 'closes: none' end with a workplace
stopped (core-400 fund P6's clinic, S-alone fund P5's farm and shop, no-hands plain P2's clinic). Every
prototype branch reads as honest: each rule sits behind its switch, the engine names no site, product or period,
no floats are used, D reads only plans made earlier in the same close in a fixed order, W's multiple is 4, and
P8's yield returns at p11 with nothing else changed; but W stops a price at direct cost only on a step down, not
on a hold or in a period with no output. For a decision: no variant passes the design's own test after a shock
that ends, workers go without at the national figures while the owner and treasury hold the money, top-ups never
stop in 12 of the 400-period runs, and R and e-kept were never measured apart.
