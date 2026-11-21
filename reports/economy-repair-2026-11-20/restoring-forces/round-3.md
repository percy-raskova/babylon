# What brings the small economy back: round three

Measured 21 November 2026. Round two left one set of rules that held every run for 200 periods: "the pair".
Rule f: a workplace that holds more cash than one period of what it pays out plans for what its buyers could
pay for plus a share of what was asked and not paid for. Rule d2: owners put cash into a workplace that holds
less than its coming wages and inputs. Round three asks whether the pair is robust and who pays for it. This
file is written by the lead from the third round's structured results (`round-3-result.json`) and its
independent check; the rows are under `out/r3-*`. The pushes: P2 a poor harvest, P4 higher pay at the clinic,
P5 a cut in the fund's taxes, and two new ones, P6 scarcer power (the utility makes 9 units where it made 10)
and P7 more mouths in the owner's household. P7 turned out to test nothing: the owner's purchase rule caps
what it buys, so the markets never see it. Hours are out of 240. Unmet is food/utility/care out of 40, the
mean of the last 20 periods.

## 1. The answer

- The pair does NOT hold at the national figures, the form the country will run in. After a poor harvest or
  scarcer power, hours fall to 168 to 215, the shop's price climbs from $38 to over $100, worker households go
  without food, power and care, and the owner holds the money. No share and no added rule mends the poor
  harvest there.
- At the small world's own figures the pair holds the five old pushes for 400 periods without drift, but not
  the new one: after scarcer power the plain world is still falling at period 400.
- The pair does work for pushes on the side of demand (the clinic's pay rise, the fund's tax cut). With the
  pair alone at a half share or more, those runs hold 231 to 240 hours at both sets of figures. At the whole
  share, prices and the owner's profit come back too in three of the four pay-rise runs.
- At the small world's figures the larger the share, the better; a quarter fails. Lent workers help one run
  (the taxed world's poor harvest), harm two (the plain world's poor harvest and pay rise) and are about even
  in the rest, at a higher cost to owners.
- Who pays depends on the push. After the old pushes at the small world's figures: the owner, because service
  prices fall to cost while pay holds. After scarcer power, and in every failing run at the national figures:
  the workers.
- Nothing measured in three rounds is ready to build as the cure.

## 2. The runs

### No rule (the baseline), with two new pushes, 200 periods

| world | run | class | hours p34 / p100 / last | last 20: hours | unmet | closes | prices U/F/C/S | owner's cash |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plain | P2 | runs away | 156 / 116 / 15 | 15-20, mean 18.50 | 40/21.75/40 | clinic from 74, farm from 146, shop from 150 | 10/38/154/141 | 2.20-2.20 |
| plain | P4 | runs away | 179 / 129 / 15 | 15-15, mean 15 | 40/25/40 | clinic from 38, farm from 123, shop from 127 | 10/34/187/147 | 7.65-7.65 |
| plain | P6 | runs away | 195 / 138 / 20 | 20-30, mean 26.50 | 40/21.85/40 | clinic from 58, farm from 155, shop from 159 | 13/34/168/121 | 10.68-10.68 |
| fund | P2 | runs away | 197 / 177 / 113 | 113-116, mean 114.65 | 40/8/13.10 | shop from 169, farm from 171 | 14/4/51/165 | 2967.51-3443.27 |
| fund | P4 | runs away | 237 / 238 / 122 | 116-128, mean 121.55 | 40/6.65/12.65 | shop from 177, farm from 178 | 11/23/47/102 | 2228.33-2435.10 |
| fund | P5 | runs away | 225 / 183 / 116 | 112-123, mean 118.80 | 40/7.40/10.75 | shop from 113, farm from 114 | 10/1/46/170 | 2156.47-2318.15 |
| fund | P6 | runs away | 192 / 195 / 130 | 129-140, mean 130.45 | 40/7.20/9.65 | shop from 124, farm from 126 | 12/26/55/165 | 2296.88-2434.21 |

Quiet, P1 and P3 exactly still in both worlds: yes. Money conserved: yes. P7: only the owner's own unmet need
changes.

### The pair at the small world's own figures, 400 periods

| world | run | class | hours p34 / p100 / last | last 20: hours | unmet | closes | prices U/F/C/S | owner's cash |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plain | P2 | holds a band (summary: cycles, band 228-234) | 230 / 231 / 233 | 228-234, mean 231.30 | 4/8.70/10 | none | 10/25/22/38 | 162.98-291.54 |
| plain | P4 | holds a band (summary: cycles, band 232-237) | 235 / 236 / 236 | 232-237, mean 234.90 | 0/8/10 | none | 10/25/22/41 | 416.72-469.89 |
| plain | P6 | still moving (band 187-204, slope 0.105) | 203 / 215 / 191 | 187-204, mean 195.65 | 2.75/14.15/29.95 | none | 11/22/22/64 | 1173.60-1282.34 |
| fund | P2 | holds a band (summary: settles elsewhere from p399; band 232-234) | 232 / 234 / 234 | 232-234, mean 233.35 | 4/6.40/10.05 | none | 10/25/21/39 | 159.47-189.07 |
| fund | P4 | settles near target (from p17) | 240 / 240 / 240 | 240-240, mean 240 | 0/0/1.05 | none | 12/25/30/38 | 609.56-637.56 |
| fund | P5 | settles near target (from p9) | 240 / 240 / 240 | 240-240, mean 240 | 0/0/4.50 | none | 13/25/28/40 | 657.90-711.74 |
| fund | P6 | holds a band (summary: cycles, band 219-236), still drifting in prices and cash | 231 / 228 / 229 | 219-236, mean 227.95 | 2.70/5.85/12.45 | none | 11/22/22/58 | 732.67-863.64 |

Quiet, P1 and P3 exactly still in both worlds: yes. Money conserved: yes. P7: only the owner's own unmet need
changes.

### The pair at the national figures, 200 periods

| world | run | class | hours p34 / p100 / last | last 20: hours | unmet | closes | prices U/F/C/S | owner's cash |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plain | P2 | still moving (band 194-236, slope 0.166) | 208 / 210 / 223 | 194-236, mean 214.85 | 14.20/16.90/28.70 | none | 10.8/115/21/125.4 | 3728.47-5077.68 |
| plain | P4 | cycles (band 236-239) | 237 / 237 / 238 | 236-239, mean 237.45 | 0/4.95/10 | none | 10.2/25/24/38.95 | 417.04-487.18 |
| plain | P6 | still moving (band 202-226, slope 0.132) | 226 / 202 / 212 | 202-226, mean 213.40 | 11.70/16.40/28.25 | none | 11.7/22.5/21.75/106.4 | 3164.71-3638.00 |
| fund | P2 | cycles (band 161-180) | 200 / 197 / 162 | 161-180, mean 168.05 | 17/10.45/28.25 | none | 10.2/43.125/21.75/119.7 | 1514.92-1750.79 |
| fund | P4 | slides (slope -0.292) | 240 / 230 / 232 | 229-236, mean 233.10 | 0.10/1.60/7.90 | none | 9.9/25/21.75/54.15 | 738.58-995.67 |
| fund | P5 | still moving (band 225-239, slope 0.514) | 226 / 239 / 239 | 225-239, mean 235.10 | 2.10/5.70/8.55 | none | 9.9/20.625/21/58.9 | 882.55-986.89 |
| fund | P6 | slides (slope -0.229) | 226 / 219 / 189 | 178-211, mean 198.10 | 11.05/13.60/29.45 | none | 11.4/21.25/21.75/105.45 | 1890.73-2138.53 |

Quiet, P1 and P3 exactly still in both worlds: yes. Money conserved: yes. P7: only the owner's own unmet need
changes.

### The pair with a quarter share, small world's figures, 200 periods

| world | run | class | hours p34 / p100 / last | last 20: hours | unmet | closes | prices U/F/C/S | owner's cash |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plain | P2 | cycles (band 176-194) | 154 / 190 / 194 | 176-194, mean 187.05 | 7.80/17.05/29.85 | none | 10/64/21/78 | 1486.91-1687.45 |
| plain | P4 | cycles (band 233-236) | 232 / 234 / 233 | 233-236, mean 233.35 | 0/7.15/10 | none | 10/25/21/41 | 433.04-446.74 |
| plain | P6 | slides (slope -0.344) | 217 / 206 / 173 | 161-204, mean 177.35 | 8.50/18.95/31 | none | 12/23/25/77 | 1323.60-1917.34 |
| fund | P2 | still moving (band 178-192, slope 0.147) | 198 / 184 / 192 | 178-192, mean 186.20 | 10.05/17.40/29.65 | none | 10/85/21/96 | 1655.12-1883.22 |
| fund | P4 | settles elsewhere (from p195) | 236 / 235 / 238 | 237-238, mean 237.80 | 0/0/2.75 | none | 11/25/29/39 | 600.62-683.86 |
| fund | P5 | cycles (band 197-209) | 220 / 234 / 203 | 197-209, mean 200.60 | 5.35/10.10/26.25 | none | 11/21/22/73 | 1314.82-1417.65 |
| fund | P6 | cycles (band 226-229) | 227 / 228 / 226 | 226-229, mean 227.40 | 0/2.55/14.95 | none | 12/23/23/45 | 426.59-445.01 |

Quiet, P1 and P3 exactly still in both worlds: yes. Money conserved: yes. P7: only the owner's own unmet need
changes.

### The pair with the whole share, small world's figures, 200 periods

| world | run | class | hours p34 / p100 / last | last 20: hours | unmet | closes | prices U/F/C/S | owner's cash |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plain | P2 | cycles (band 230-240) | 238 / 239 / 231 | 230-240, mean 234.25 | 3.95/8.65/10 | none | 11/25/23/38 | 148.68-323.90 |
| plain | P4 | settles elsewhere (from p197) | 240 / 240 / 240 | 240-240, mean 240 | 0/0/4.10 | none | 12/25/28/38 | 652.73-705.66 |
| plain | P6 | still moving (band 226-240, slope 0.509) | 237 / 235 / 239 | 226-240, mean 235.25 | 4.35/9.05/10.70 | none | 13/22/22/38 | 61.34-542.92 |
| fund | P2 | cycles (band 232-240) | 232 / 234 / 240 | 232-240, mean 235.65 | 4/6.90/10.15 | none | 10/26/21/38 | 115.43-214.58 |
| fund | P4 | settles near target (from p17) | 240 / 240 / 240 | 240-240, mean 240 | 0/0/1.10 | none | 12/25/30/38 | 609.56-637.56 |
| fund | P5 | settles near target (from p8) | 240 / 240 / 240 | 240-240, mean 240 | 0/0/4.35 | none | 12/25/27/40 | 652.52-701.97 |
| fund | P6 | cycles (band 225-234) | 227 / 228 / 228 | 225-234, mean 228.65 | 0/0.40/13.65 | none | 14/30/25/40 | 412.28-569.60 |

Quiet, P1 and P3 exactly still in both worlds: yes. Money conserved: yes. P7: only the owner's own unmet need
changes.

### The pair with a quarter share, national figures, 200 periods

| world | run | class | hours p34 / p100 / last | last 20: hours | unmet | closes | prices U/F/C/S | owner's cash |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plain | P2 | still moving (band 194-216, slope 0.353) | 203 / 216 / 209 | 194-216, mean 208.55 | 14.10/14.15/29.80 | none | 10.2/93.125/20.25/120.65 | 3635.28-5139.18 |
| plain | P4 | slides (slope -0.365) | 191 / 198 / 198 | 194-222, mean 210.80 | 11.60/14.20/27.70 | none | 10.2/20/21/104.5 | 2707.89-3571.61 |
| plain | P6 | slides (slope -0.128) | 238 / 213 / 200 | 200-210, mean 200.50 | 10/27.65/30 | none | 12.3/26.875/21.75/98.8 | 2833.35-2989.32 |
| fund | P2 | cycles (band 164-178) | 198 / 196 / 177 | 164-178, mean 172.10 | 16.05/11/27.55 | none | 10.2/56.875/21/117.8 | 1720.60-1956.53 |
| fund | P4 | slides (slope -0.231) | 186 / 214 / 198 | 186-206, mean 198.45 | 10.55/10.15/29.90 | none | 10.2/20.625/21/106.4 | 2177.58-2375.32 |
| fund | P5 | slides (slope -2.768) | 234 / 240 / 189 | 188-240, mean 225.40 | 4.40/6.15/19.90 | none | 10.2/21.25/20.25/81.7 | 1244.85-2329.24 |
| fund | P6 | cycles (band 189-209) | 207 / 220 / 190 | 189-209, mean 201.05 | 10.20/14.55/29.65 | none | 11.4/21.25/21/104.5 | 2070.49-2229.12 |

Quiet, P1 and P3 exactly still in both worlds: yes. Money conserved: yes. P7: only the owner's own unmet need
changes.

### The pair with the whole share, national figures, 200 periods

| world | run | class | hours p34 / p100 / last | last 20: hours | unmet | closes | prices U/F/C/S | owner's cash |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plain | P2 | cycles (band 188-240) | 220 / 219 / 238 | 188-240, mean 215.70 | 14.30/18.75/29.60 | none | 10.2/114.375/21/129.2 | 3487.87-5277.11 |
| plain | P4 | cycles (repeats every 3 periods) | 240 / 240 / 240 | 240-240, mean 240 | 0/0/1.30 | none | 12/25/30/38 | 762.86-782.86 |
| plain | P6 | settles elsewhere (from p198) | 210 / 200 / 201 | 200-201, mean 200.20 | 10/24.70/30 | none | 12/25.625/21.75/96.9 | 2585.67-2643.87 |
| fund | P2 | still moving (band 161-189, slope 0.534) | 210 / 197 / 179 | 161-189, mean 173.60 | 15.70/11.40/30.65 | none | 10.2/31.875/19.5/119.7 | 1670.57-2170.31 |
| fund | P4 | settles near target (from p191) | 240 / 240 / 240 | 240-240, mean 240 | 0/0/1.85 | none | 10.2/25/24.75/45.6 | 575.87-644.12 |
| fund | P5 | cycles (band 229-233) | 240 / 240 / 233 | 229-233, mean 231.50 | 0.05/2.05/8 | none | 9.9/21.25/21.75/51.3 | 679.37-731.91 |
| fund | P6 | still moving (band 190-221, slope 0.285) | 211 / 210 / 200 | 190-221, mean 207.25 | 9.20/14.50/27.85 | none | 12/22.5/23.25/100.7 | 1965.99-2208.77 |

Quiet, P1 and P3 exactly still in both worlds: yes. Money conserved: yes. P7: only the owner's own unmet need
changes.

### The pair with lent workers, small world's figures, 200 periods

| world | run | class | hours p34 / p100 / last | last 20: hours | unmet | closes | prices U/F/C/S | owner's cash |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plain | P2 | still moving (band 172-240, slope 1.157) | 240 / 240 / 217 | 172-240, mean 195.55 | 2.35/9.15/28.20 | none | 10/24/21/57 | 735.71-1413.09 |
| plain | P4 | slides (slope -1.489) | 240 / 240 / 240 | 182-240, mean 218.45 | 2/7.60/23.10 | none | 13/22/23/54 | 539.04-1791.89 |
| plain | P6 | still moving (band 173-217, slope 0.163) | 225 / 193 / 217 | 173-217, mean 198.05 | 3/12.70/29.90 | none | 13/24/24/65 | 1037.99-1313.43 |
| fund | P2 | settles elsewhere | 240 / 240 / 240 | 240-240, mean 240 | 2.60/6.65/10.55 | none | 10/24/20/42 | 209.23-738.23 |
| fund | P4 | settles near target (from p17) | 240 / 240 / 240 | 240-240, mean 240 | 0/0/1.10 | none | 12/25/30/38 | 609.56-637.56 |
| fund | P5 | settles near target (from p9) | 240 / 240 / 240 | 240-240, mean 240 | 0/0/4.55 | none | 13/25/26/40 | 653.26-716.39 |
| fund | P6 | slides (slope -0.205) | 240 / 235 / 225 | 225-240, mean 229.60 | 3.70/6.45/21.15 | none | 12/21/21/79 | 1218.38-1592.41 |

Quiet, P1 and P3 exactly still in both worlds: yes. Money conserved: yes. P7: only the owner's own unmet need
changes.

### The pair with a plan that remembers, national figures, 200 periods

| world | run | class | hours p34 / p100 / last | last 20: hours | unmet | closes | prices U/F/C/S | owner's cash |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plain | P2 | slides (slope -0.177) | 206 / 227 / 199 | 199-212, mean 209.40 | 14.30/12.25/28.25 | none | 9.9/82.5/20.25/119.7 | 4729.96-5028.21 |
| plain | P4 | settles elsewhere (from p195) | 240 / 240 / 240 | 240-240, mean 240 | 0/0/2.55 | none | 11.7/25/29.25/38 | 700.77-762.02 |
| plain | P6 | cycles (band 227-230) | 231 / 230 / 229 | 227-230, mean 229.10 | 0/1.40/13.95 | none | 16.5/27.5/26.25/46.55 | 940.88-1029.35 |
| fund | P2 | slides (slope -0.402) | 202 / 220 / 155 | 155-184, mean 167.50 | 17.35/8.90/28.25 | none | 9.9/38.75/20.25/121.6 | 1464.85-1710.72 |
| fund | P4 | settles near target (from p165) | 240 / 240 / 240 | 240-240, mean 240 | 0/0/1.40 | none | 10.2/25/23.25/46.55 | 608.47-629.22 |
| fund | P5 | settles elsewhere | 239 / 240 / 240 | 240-240, mean 240 | 0/0/6.90 | none | 10.2/25/20.25/47.5 | 599.86-619.91 |
| fund | P6 | slides (slope -0.463) | 221 / 222 / 212 | 210-222, mean 219.40 | 8.35/10.15/27.60 | none | 12/21.25/21.75/100.7 | 2144.62-2246.71 |

Quiet, P1 and P3 exactly still in both worlds: yes. Money conserved: yes. P7: only the owner's own unmet need
changes.

## 3. The questions, as the measuring agent answered them from the rows

### Does the pair hold at the national figures?

No, the set does not hold at the national figures. In r3-1-200 (f at 50 + d2 + 2.5% steps + two periods of
cash), over p181-200: plain P2 is still moving at 194-236, mean 214.85; fund P2 is 161-180, mean 168.05; fund
P4 slides (229-236, slope -0.29); plain P6 is still moving (202-226); fund P6 slides (178-211); fund P5 is
still moving (225-239). Only plain P4 holds (236-239). Nothing closes. Why, from plain P2's rows: (1) Every
workplace opens with two periods of cash, so each has a full period of spare at p1 and f acts from p2: the
clinic extends from p2 and the shop from p6. But the farm is never short of cash, so d2 never tops it up. (2)
Early pay and hours stay higher than at $1 steps: 240/240/239/236/233 hours in p1-p5, against
240/240/236/224/221. So households keep buying 40 food a period through p5, while the farm, held to 40 hours
by its 5 people, makes 36. (3) R3 raises a goods price only when demand waited and stock is at or below
target. Nothing waits while the farm still has stock, so the farm's price stays at $25 while its stock drains:
40, 36, 32, ... 2, and 0 at p21. At $1 steps food sales fell to 35-36 by p4 and the farm's stock held at
27-30, so the price never had to move. (4) From p22 food waits every period. The farm's price steps up $0.625
a period and the shop's $0.95, to $115 and $125.40 by p200. (5) The cash goes to the owner, the only account
paid profit: its cash is $3,728-5,078 over p181-200, against $163-292 in the same run at $1 steps. Workers
carry all the going without: 14.2 food, 16.9 utility and 28.7 care a period. Owners' top-ups are $3,486, to
the utility and the shop. Part of the owner's money comes back when it pays clearing prices for care: the
clinic's cash jumps to $1,818 at p191 and p198 as the owner's falls by about $1,340. Adding k (r3-4) does not
mend the poor harvest: both P2s slide (plain 209.40, fund 167.50). It does bring plain P4, fund P4 and fund P5
to 240 hours, and holds plain P6 at 227-230.

### Does it hold to 400 periods?

At the small world's figures (r3-2-400) the old pushes hold to 400 periods without drift. Means for p81-100,
p181-200, p281-300 and p381-400: plain P2 231.0/230.8/231.6/231.3; fund P2 233.4/233.3/233.0/233.3; fund P4
and P5 240 throughout. Plain P4 is 235.6/235.6/235.2/234.9, a slow fall of under 1 hour in 300 periods, with
$27 of new top-ups in p381-400. Owner cash, care price, utility price and shop price stay in the same ranges
in every window. The new push P6 is still drifting. In plain P6, hours fall (207.6, 205.2, 199.3, 195.7), the
shop price ratchets (51.8, 59, 63, 64), owner cash rises (774 to 1,225), and top-ups never stop (232 to 1,338
a window). In fund P6 hours hold at 227-230, but the shop price climbs 45 to 58, farm cash falls 1,638 to 930,
and top-ups resume after p280. P7 is inert. So for the five original pushes the set holds to 400 periods, but
it does not settle the new power shortage.

### Does it rest on the half share?

50 is not special. At the small world's figures the result improves with the share. At 25 the set fails: both
P2s fall to about 186-187 hours, fund P5 to 200.6 and plain P6 slides to 177, with $2,900-12,300 of top-ups.
At 50 it holds, as above. At 100 it is better in every pushed run: plain P2 234.25, fund P2 235.65, plain P4
240 (prices 12/25/28/38, owner $653-706, against 235 hours and owner $417-470 at 50), fund P4 and P5 near
target, plain P6 235.25 (still moving; $7,120 of top-ups), fund P6 228.65. At the national figures no share
mends the poor harvest: plain P2 is 208.55/214.85/215.70 and fund P2 172.10/168.05/173.60 at 25/50/100. The
share does decide the higher-pay push there: at 25 both P4s slide (210.8 and 198.45). At 50 plain P4 holds at
237.45 and fund P4 slides. At 100 plain P4 is at target (240, care 1.30, prices back to 12/25/30/38, owner
$763-783) and fund P4 is near it. So the larger share is better wherever the set works; 50 is just the
smallest share measured that holds at the small world's figures.

### What do lent workers add?

Over 200 periods, lent workers (r3-3: f 50 + a + d2) help the taxed world and harm the plain world. Fund P2
holds 240 hours over p181-200, against 233.35 without a, with less unmet food and utility (2.60/6.65/10.55);
top-ups are $1,294 against $597. Fund P6 is about even at 229.6 (slides) against 227.95, but top-ups are
$16,062 against $9,696. In the plain world the 100-period picture reverses. Plain P2 is 240 at p34 and p100,
then breaks down: p181-200 is 172-240, mean 195.55, still moving, against 231.3. Workers now go without most
of the care (w_utility 13.5), and top-ups are $5,365 against $322. Plain P4 slides to 218.45 (182-240),
against 234.9, with $4,999 of top-ups. Plain P6 is still moving at 198.05 with $19,052 of top-ups. Both quiet
runs and both P1s and P3s stay still, and money is conserved. The rows give the same reason round two gave:
borrowed hours drain the farm, and owners keep paying for them. Rule a is not recommended with f + d2.

### The two new pushes

How they are built. P6 (power is scarcer): under P6 only, the utility's process becomes a 10-hour batch that
makes 9 units, where the opening's batch is 1 hour and 1 unit. The opening is stated as 12 such batches (120
hours, capacity 12, commitment 12), so the opening is unchanged and only the yield drops, the way P2 drops the
farm's. One side effect: the utility's plan now moves in 10-hour steps of 9 units, not 1-unit steps. P7 (more
mouths): the owner's cohort counts persons*3/2 (15 plain, 12 fund), with its stock, cash and purchase policy
those of the balanced opening. Baseline: P6 runs away in both worlds (plain: clinic closes from p58, farm
p155, shop p159, 26.5 hours at the end; fund: shop p124, farm p126, 130.45 hours). P7 does nothing to the
economy. The owner's purchase policy caps each product at its balanced need (10 plain, 8 fund), so demand
stays at the opening's and the run 'returns to opening' in every state column. Only the owner's unmet need
changes: 5/5/5 (plain) or 4/4/4 (fund), from p3 for food. No rule touches P7 in any variant: there is no
unpaid asking, so f is silent. So the second new push tests nothing. Under the set (r3-2-400), P6 is the set's
first clear partial failure at its own figures. Plain P6 is still moving at 187-204 (mean 195.65, falling
every 100 periods). Fund P6 holds a band of 219-236 with ratcheting shop prices and $9,696 of top-ups. And
here the workers pay, not the owner: in plain P6 over p181-200 the owner has $1,011 a period of profit and
goes without 1.2 care, while w_utility goes without 13.45 care and w_clinic 2.4 food, 3.15 utility and 5 care.

### Where prices end, and why profit goes

Plain P2 under the set (r3-2): the clinic's posted price falls a dollar each period from p2 to p8 (30 to 23).
Each time it performed less than its capacity row (40) and its direct cost was below its receipts: R2,
SpareCapacity. Sold: 32, 28, 27, 29, 29, 33, 29. The clinic was paid for the plan it kept: hours 40, 36, 34,
33, 35, 35, 38, idle paid 8, 8, 7, 4, 6, 2, 9. f extended the plan by 4-6 units a period. Cash holds at $880
until p8 ($721). The price rises a step at p9 and p13, when the market was short and buyers were turned away
(1 and 3): R11, PricedOut. Otherwise it keeps falling, to $21-22 by p12-15, while sales climb back to 38-40.
The utility holds $12 through p2 (sold 120). It falls to $11 at p3 and $10 at p4 (sold 107, 106; idle 13, 5;
R2). It rises at p8 and p10 when short (R11) and sits at $10-11 from then on, with cash $1,070-1,200. Plain
P4: the clinic falls $30 to $29 at p1, though f had added nothing yet: the owner's $40 top-up left it buying
39 care. It falls again at p2 (39 sold) and p4 (39). It rises at p5, p8, p9 and p12 when short (R11), with $24
topped up at p6. It falls p13-15 (33-35 sold, idle 7/3/5) to $25. The utility holds $12 for ten periods (120
sold), then falls at p11, p13 and p14 to $10 (R2) as clinic hours dip. Is f's extra plan the spare capacity
that cuts the price? No. R2 compares what was performed with the capacity row (40 care, 120 utility), not with
the plan. Every cut follows sales below that nameplate, whatever f planned. Without f (base plain P2) the
clinic's price falls the same way, 30 to 23 by p14, in periods with 0-11 idle hours. f's extension appears as
paid idle hours, not in the price rule. Where prices end: utility $10-11 (its direct cost is $10 a unit, one
hour at $10). Care $21-23, its direct cost of $10 plus a unit of utility at $10-12. Food holds at $25 (farm)
and $38-41 (shop), because the goods rule R3 moves only on waiting demand and stock against target. So the
service profit is competed away to about zero, held down by R2 and lifted only by R11's short-market steps.
What profit is left comes from the farm and the shop. The owner's profit is $240 a period in plain P2 and $439
in plain P4, against $800 in the quiet run.

### Who pays

Measured on spike/r3-2w, which adds flow columns only: every other column equals r3-2 in all 15 runs, and the
residual of each account's cash is 0. Means per period over p181-200. Plain P2: the owner's only income is
$240.19 of profit. It spends $244.18 and holds $173-319. It buys 6.05 food and 1.35 utility, no care, and goes
without 3.95 food, 8.65 utility and 10 care. The worker accounts live on wages: w_utility $1,133.50, w_farm
$400, w_clinic $397, w_shop $377.50, all spent, cash $0-22. Each buys its full 1/1/1 a person plus comfort
care (2-3.35 units an account) and goes without nothing. Sites hold the rest: utility $1,100-1,200, farm
$1,408-1,481 (above its $880 opening: the $321.64 of top-ups, and its food stock turned to cash), clinic
$794-880, shop $1,400. Plain P4: the owner has $439.38 of profit, spends $438.90 and holds $419-479. It buys
10 food and 2.8 utility and goes without 7.2 utility and 10 care. Workers: w_clinic $440 of wages (the $11
rate), the others $400 and $1,155.50; all buy their needs plus 1.5-3.35 comfort care and go without nothing.
Fund P2: the owner has $173.76 of profit and $0.34 of top-up, holds $154-189, and goes without 4.05 food, 6.15
utility and 8 care (all its care). The supported account gets $515.43 of benefits, against $640 in the quiet
run, and goes without 2.1 care. The workers earn $379.50-1,153.50, pay 20% tax, buy their needs plus 1.2-4.1
comfort care, and go without nothing. The fund holds $382-394 (opened with $960) and the treasury $127-131.
Why the owner: wage rates never move (R6), and prices fall under R2 toward direct cost. So the workers' fixed
pay buys more, and wages are the first claim on a workplace's cash. Profit is what is left, and only the owner
is paid it. Its top-ups and its lost profit end as the workers' comfort care and as the farm's cash. The owner
also buys in R7's order (food, then utility, then care), so care goes first. No worker household goes without
anything in these three runs. In fund P2 the supported account also loses about 2 care, because the fund's
taxes on the smaller profits fall short. The owner does not pay in every push. In P6 under the set the workers
go without care (plain P6: w_utility 13.45, w_clinic 5, w_shop 3.65, w_farm 3.25) while the owner takes $1,011
a period of profit. At the national figures the workers go without in every failing run while the owner holds
$1,500-5,100.

### What might keep profit (a conjecture, not measured)

Conjecture except where marked measured. The rows point at R2. A service cuts its price whenever it performed
less than its capacity row, its nameplate 40 care or 120 utility, and its direct cost is below its receipts.
In a slump that is nearly always, so prices fall to direct cost and service profit goes to about zero. The
smallest change the rows suggest: count spare capacity against the plan the service made for paying buyers,
not against nameplate. Then a clinic that sold what it planned for paying buyers would hold its price, and f's
extension and idle nameplate would not cut it. That was not measured. One related result was measured: at the
whole share (r3-2-f100), plain P4 keeps 240 hours with prices 12/25/28/38 and an owner holding $653-706. At
the national figures with share 100, plain P4 returns to the opening prices with the owner at $763-783. Both
are cases where f's larger plan filled the shortfall, so sales stayed at nameplate and R2 never fired. That
route does not keep profit in the poor harvest: plain P2 at share 100 still ends at care $23 and owner
$149-324. Whether a plan-based R2 keeps profit without bringing back the downward ratchet of plans is unknown.

### What surprised the measuring agent

P7 as specified is inert. The owner's purchase policy (maximum purchase = its balanced need) stops it buying
for the extra persons, so markets never see the push and only the owner's unmet need changes. The set's
success at $1 steps partly rests on the slump coming faster. At the national figures, households keep buying
40 food for five periods, and with R3 silent while stock remains, the farm's buffer drains to zero by p21 and
the food prices ratchet from there. Share 100 is better than 50 everywhere at the small world's figures. Under
P6 the set makes the workers, not the owner, go without care. With lent workers, plain P2 is at 240 hours at
p100 and then breaks down by p181-200. At the national figures the owner hoards $3,700-5,100 while workers go
without, and it recycles some of it by paying clearing prices for care.

## 4. The independent check

A second reader recomputed 25 claims from the rows: 24 hold. Not holding:

- Claim: r3-2-400 fund P6: hours steady at 227-230, the shop price climbs from 45 to 58, farm cash falls from
1,638 to 930, and top-ups resume after p280 Finding: Hours means 227.35/229.75/228.90/227.95. Shop
45/56/58/58. Mean farm cash 1,638.3/1,442.0/909.8/930.1. Top-up periods include 205, 207-209, 231-232,
238-241, 263, 267-269, 279. Correction: Top-ups stop only in p181-p204. They resume at p205 ($5.5, then $196
at p207 and $143 at p208) and run through p280 ($2,225.34 in p201-280). The rest of the claim holds.

Every third-round branch was read against the single-rule patches it combines: they differ only in plumbing,
name no site or period, and conserve money.

### What the check says is left unsaid

The set fails at the national figures, which is the form the country will run in. No share and no added rule k
mends the poor harvest there, so nothing measured is ready to build as the cure. Wherever it fails, worker
households go without needed food, utility and care. Under P6 they go without even at the small world's own
figures: w_clinic is paid $175.50 of its $400 and lacks 2.4 food, 3.15 utility and 5 care, while the owner
takes about $1,011 of profit and buys 1.85 comfort care. So 'the owner pays' holds only for P2 and P4 at $1
steps. Several runs are still drifting at their end: plain P6 at 400 periods loses about 4 hours a century
while its shop price climbs; fund P6's farm cash falls from $1,638 to $930 with $9,696 of top-ups; fund P2 and
plain P4 keep taking small top-ups to p397-399. Nothing says how long owners can keep paying, or whether top-
ups are ever paid back. Workplaces fall below their opening outlay: in plain P6 the clinic ends at $132 and
the farm at $760, against $880 at the opening. d2's outlay leaves out a shop's goods purchases, so a shop's
restocking cash is never protected; at the national figures the shop falls to $235. The short-market clearing
price jumps about 6x for one unit short (care at $124 against a $20 quote), moving $1,340 in one period; this
is untested as a price form. The result rests on the share: at 25 the set fails, at 100 it does best, and only
three values were tried. P7 tests nothing, and P6 mixes scarcity with 10-hour batches. No variant reached the
P2 target of 240 hours and 4.44 care. Services end near direct cost, so a decision must also say whether
profit falls to the farm and shop alone. 'Closes' counts zero output, not zero paid hours: a clinic keeps
paying a few hours for 3 periods after its output stops.

### Its summary

I recomputed every claim from the rows, and almost every figure, class, closure, price, owner-cash range and
top-up total in the third round's tables holds. All its reproduction checks hold too: the old runs equal
base-200 byte for byte, r3-2's first 200 periods equal together-r2-6-200, and each chk-r3-* run equals its
part. One claim is refuted: in fund P6 the top-ups pause only in p181-204 and resume at p205, not after p280
($2,225 is paid in p201-280). A few details are loose: the farm's stock falls 4 a period only through p5, at
$1 steps it dips to 17 rather than holding at 27-30, $58 of the national top-ups go to the clinic, and
services keep about $71 a period of profit in plain P2. The code confirms the price account: R2 cuts against
nameplate capacity (process_available), f does not touch market.rs, prices end at direct cost, and the six
branches differ from their single-rule patches only in plumbing, name no site or period, and conserve money.
For a decision, the set does not hold at the national figures, the small-world result depends on the share,
and under P6 and every national failure the workers, not the owner, go without needed care while some runs are
still drifting at their last period.
