# HOI4 supply, in material terms: what moves, where it chokes, what a cut costs

**Status:** read-only, 2026-10-25. Target: `/media/user/data/steam/steamapps/common/Hearts of Iron IV/hoi4`,
ELF64 PIE, stripped, 70,902,032 bytes, SHA-256 `56fc2945…3a88a` — the same artifact as
`hoi4-script-pass.md` §7 B1, `hoi4-decomp-supply.md` and `hoi4-decomp-orders.md`, so all three offset
ledgers still apply. Base game only; `common/defines`, `common/units`, `map/` read as publisher plaintext.

This pass answers the §6 blockers of the two prior supply briefings: the bottleneck `min` reduction
(**observed**, §2.2), the falloff evaluation site (**found**, §3.4), the `supply_tuple` identity (§1),
`_RemainingSupply` accounting (§4), severing (§5) and the army supply buffer (§6). It *refutes* one prior
inference (the debug dump prints fingerprints, not field values — §1.3) and *confirms* one negative
(the logistic is a compiled shape with four scale dials, §3.4).

---

## Thesis

1. Supply in this build is a **reach value propagated over provinces by five sequential passes** (`0x113c8a0`), not a stock: a node's budget is re-derived every tick and nothing is banked at the node.
2. The only durable accumulator in the chain is the **army supply ratio** (`0x11a95f0`: +1 %/hour default, ≤15 %/hour, ≈4.2 days from zero), which is why a cut has a *recovery* cost measured in days rather than a one-tick dip.
3. Corridor throughput is **`10 + 5 × min-edge-level`** (`0x11a5c80`, `0x11a6f10`), so a single fully damaged segment anywhere on a level-5 trunk removes 71 % of its capacity — interdiction is cheap, repair is not.
4. Shortage is shared **proportionally and uniformly** (`0x1183ee0`: one ratio from `remaining/asked`, then per-consumer shares), so cutting a corridor degrades every consumer downstream by the same visible fraction — no hidden prioritisation to reverse-engineer.
5. The distance falloff is a **compiled fixed-point sigmoid** (`0x1146e74`, base-e `pow` at `0x34a0ec0`) whose four dials only slide a multiplier in [0.25, 0.90]: the curve cannot be re-shaped from content, which is exactly the primitive Babylon's constitution refuses.

---

## 0. Method, and the image-base trap

| Class | Source | Establishes |
| --- | --- | --- |
| **S** | `common/defines/00_defines.lua`, `common/units/*.txt`, `map/*.txt` | Authored values, ceilings, file:line |
| **B** | Retained asserts + RTTI + `.rodata` layout in the shipped binary | Invariants, field names, constants |
| **C** | `objdump -d` over `.eh_frame`-delimited functions (128,165 FDEs) | Instruction-level sequence, arithmetic, branches |

REA was not used: the prior pass measured its per-request timeout at 330 s on this artifact
(`hoi4-decomp-supply.md` §0), and nothing here needed it.

**Ghidra 12.1.4 + Temurin 21 was attempted and discarded.** Two results worth recording:

1. `analyzeHeadless … -process hoi4 -postScript Target3.java 0x11a6f10:0x32b` decompiled an unrelated
   visitor function: Ghidra maps this PIE at image base `0x100000`, so program address `0x11a6f10` is
   file vaddr `0x10a6f10`. The prior pass's warning reproduces exactly.
2. With the corrected address (`0x21a6f10:0x32b`) the *existing* project returned a 6-instruction stub for
   a range that `.eh_frame` says is 811 bytes; `removeFunction`/`createFunction`/`setBody` did not take
   effect on the stale project. No decompiled output is used anywhere below.

Everything below is therefore **C-class**: exact function ranges from `.eh_frame`, exact addresses from
`objdump`, NSupply define storage addresses resolved by following each define's generated lua reader
(§0.1). Fixed-point convention throughout: `CFixedPoint` is a signed 64-bit integer scaled by
**100000 = 1.0**; the compiler's divide is `imul 0x29f16b11c6d1e109 / sar 0xe`.

### 0.1 Define storage map (new, reusable)

Each `NSupply` key has a generated reader: `lea <"NSupply::KEY"+9>,%rsi; lea <dest>,%rdx; call <reader>`.
Following all 103 keys gives the live addresses in `.bss` (0x439e7a0–0x466d5e8):

| Range | Kind | Example |
| --- | --- | --- |
| `0x4406588` … `0x44065f8` | int | `MAX_RAILWAY_LEVEL` `0x4406588` (also `RIVER_RAILWAY_LEVEL` `0x44067d8`) |
| `0x4406598` … `0x4406be8` | `CFixedPoint` (16-byte stride) | `RAILWAY_BASE_FLOW` `0x4406598`, `CAPITAL_INITIAL_SUPPLY_FLOW` `0x4406648`, `SUPPLY_FLOW_DIST_LOGISTICS_FALLOFF_K` `0x44067f8` |

Reader sites (one per key) are at `0x1ea7710`–`0x1ead7c5`; `MAX_RAILWAY_LEVEL`'s reader is
`0x1ea7710` with destination `0x4406588` at `0x1ea77cc`, and it clamps a bad value up to 1 at
`0x1ea7913`. This map is what makes the rest of the report cheap to read: every `# 4406xxx` operand in
the supply code is a named dial.

---

## 1. Supply node identity: province-keyed, country-overlaid

### 1.1 The key is a province, not a (province, country)

`supply_tuple_province_id` (`hoi4:.rodata 0x35aa9fc`) is dumped as one field of a contiguous 27-key
cache table (`0x35aa87f–0x35aaa63`, TU `supply/supply_system.cpp` at `0x35aa840`), immediately after
`has_capital_reach`/`capital_reach`. **B**

The same identity appears in the save grammar: `country_supply.cpp`'s loader (function `0x1138a90`,
8,476 B) asserts the token sequence `Reader.GetLeft().GetToken() == _node_` (`0x35a8a00`),
`== _id_` (`0x35a8a66`), `== _data_` (`0x35a8a8a`) — i.e. a node is persisted as **an id plus a value
blob**, and the id is the province. **B**

The per-country layer is an *overlay inside* the node, not part of the key:
`CAssociativeArray<CCountryTag, SSupplyNodeData::SConvoyAndTrainInfoPerCountry>` (mangled RTTI with a
21-entry inline buffer), plus `SSupplyNodeData::SConsumerData` (25-entry buffer) and
`CSupplySystem::SStateSupplyInfo::SPerCountryInfo` (42-entry). **B** — that closes
`hoi4-script-pass.md` §6 follow-up 4: node state is per province, country data is a map member.

### 1.2 Two node structures, not one

Two different records are addressed by the supply code and they must not be conflated:

| Record | Stride / fields observed | Used by |
| --- | --- | --- |
| `SSupplyNodeData` (cache, province-keyed) | fields at `+0x4` (province), `+0x8` (type), `+0xc` (connected flag), `+0x20`/`+0x38`/`+0x48` (three additive supply pools), `+0x60`/`+0x6c` (per-country array), `+0x94` (railway level/damage), `+0x98` (supply from capital) | cap computation `0x1180ae0`, tooltips `0x11b6590`, dump `0x1187d70` |
| flow-cache node | stride **0xe8**, `+0x8` type, `+0xc`, `+0x30` incoming-leftover accumulator, `+0x38` `_TotalSupply`, `+0x40` `_RemainingSupply`, `+0xd0`/`+0xdc` consumer array | allocation `0x1183ee0`, leftovers `0x114f770`, flow `0x1141010` |

**C** (strides are literal `imul $0xe8` / `imul $0xd8` in each function).

### 1.3 Correction: the 27-key dump is a fingerprint table

In `0x1187d70` each key is emitted with a value computed as
`100000 × (dword[-0xbc] XOR dword[-0xc0] XOR dword[-0xb8])` (`0x118980e–0x1189836` for
`supply_tuple_province_id`). It is a **debug fingerprint per cache field**, not a semantic dump of the
value. Prior passes treated this table as a state decomposition; it is that, but its printed numbers are
hashes and should not be read as quantities. **C**

### OURS

- One identity per place, with a per-faction overlay map inside it. That is the shape Babylon needs for
  a *contested* corridor: the road belongs to the map, the toll/stock/denial state belongs to whoever
  holds it. Do not make (place, faction) the primary key — it doubles every edge and makes "who controls
  this bridge" a join instead of a field.
- The dump table is a debugging convenience. Two or three named derived fields with a visible value and a
  dirty cause will beat 27 hashed keys; a hash cannot answer "why did this node dry up".

---

## 2. Corridor capacity: per-edge level, min over the path, damage as a linear tax

### 2.1 The per-edge tuple

`railway_manager.cpp` (`0x35aa258`) stores `_RailwayLevelsToNeighbors`, an integer level **per
(province, neighbour index)**:

| Assert / action | Offsets |
| --- | --- |
| `_RailwayLevelsToNeighbors.GetSize() == NumNeighbors` | `0x35aa299` at `0x1178a8a` |
| `Invalid neighbor index in SetRailway` | `0x35aa2cd` at `0x117908a` |
| write-time clamp: `if (level > MAX_RAILWAY_LEVEL) level = MAX` | `0x1178ff5–0x1179003`; assert text `0x35aa352`/`0x35aa2f2` |
| upgrade path requires `CurrentLevel < MAX_RAILWAY_LEVEL` | `0x35aa39c` at `0x1179279` |

`MAX_RAILWAY_LEVEL = 5` (`00_defines.lua:4264`), live at `0x4406588`. **C+S**

`map/railways.txt` (909 rows, `level count province…`) is a *different, coarser* quantity — corridor
tiers as authored — and `RIVER_RAILWAY_LEVEL = 1` (`00_defines.lua:4294`) is read in this build **only**
by the supply-map tooltip (`0x11b95fb` in `0x11b6590`), so "rivers behave as level 1" is a declared intent
whose supply-side use I could not observe. Marked **uncertain**.

### 2.2 The `min` reduction — observed

`0x11a6f10` (811 B, `supply_system_utils.cpp`) takes a province path (`CPdxArray<int>`: data at `+0`,
count at `+0xc`) and returns one integer:

```
acc = *MAX_RAILWAY_LEVEL_variable            ; 0x11a6f2e  (identity for min)
if count == 0: assert "Empty Rail Segment being analysed…" (0x35acabc @0x11a71f1); return acc
if count == 1: return acc
cur = path[0]
for i in 1..count-1:
    nxt = path[i]
    info = CProvinceRailwayInfo[cur]         ; binary search, 0x11a70bf–0x11a70d5
    if !info: assert "Failed to find CProvinceRailwayInfo…" (0x35acb52 @0x11a7186); cur = nxt; continue
    lvl = info->levelTo(nxt)                 ; 8-byte sorted pairs, level at second dword
    if lvl <= 0: assert "Level > 0" (0x35ac9d5 @0x11a7125)
    acc = min(acc, lvl)                      ; cmp %eax,%ebx / cmovl  @0x11a6f6c–0x11a6f74
    cur = nxt
```

So **corridor capacity = the minimum edge level along the stored path**, initialised to the ceiling.
This is the loop the prior pass recorded but did not observe (`hoi4-decomp-supply.md` §1, "Not
established"). A missing or zero edge does not degrade the result — it drives the accumulator to 0, and
`BottleneckData._BottleneckLevel > 0` (`0x35ac9bb` @0x11a7541) then fires. **C**

### 2.3 Corridor throughput, exactly

Three small functions in `supply_system_utils.cpp`:

| Function | Formula | Offsets |
| --- | --- | --- |
| `0x11a5c80` (64 B) | `flow(level) = RAILWAY_BASE_FLOW + RAILWAY_FLOW_PER_LEVEL·level` | reads `0x4406598`@`0x11a5cb4`, `0x44065a8`@`0x11a5c87` |
| `0x11a5cc0` (82 B) | `damageTax(level, health) = level · RAILWAY_FLOW_PENALTY_PER_DAMAGED · (1−health)` | `0x44065b8`@`0x11a5ccc` |
| `0x11a5d20` (135 B) | both combined for one segment | both dials at `0x11a5d2e`/`0x11a5d69` |

With authored values (`00_defines.lua:4332-4336`) `RAILWAY_BASE_FLOW = 10.0`,
`RAILWAY_FLOW_PER_LEVEL = 5.0`, `RAILWAY_FLOW_PENALTY_PER_DAMAGED = 5.0`:

| Bottleneck level | Capacity | Fully damaged segment at that level | Result |
| --- | --- | --- | --- |
| 0 (no rail) | 10.0 | — | 10.0 |
| 1 | 15.0 | −5.0 | 10.0 |
| 3 | 25.0 | −15.0 | 10.0 |
| 5 | 35.0 | −25.0 | 10.0 |

**A fully damaged segment anywhere on that level collapses the whole corridor to the no-rail base.**
`RAILWAY_MIN_FLOW = 5.0` is read in `railway_manager.cpp` (`0x1177250`@`0x1177317`,
`0x1177c50`@`0x1177d19`) but not in the supply-flow path, so the 10.0 floor above comes from
`RAILWAY_BASE_FLOW`, not from `RAILWAY_MIN_FLOW` (whose actual use I did not resolve — uncertain).

`0x11a5e50` (3,176 B) is the assembler: for each candidate path it takes the `0x11a6f10` bottleneck,
folds in a second source (`0x74(node)` when larger, `0x11a6461–0x11a6473`), keeps
`min` across paths (`cmovl 0x11a647a`), writes the winning level to `+0x4` of the connection
(`0x11a6531`), then computes railway flow at `0x11a66b8–0x11a66f2` and naval flow
(`NAVAL_BASE_FLOW + NAVAL_FLOW_PER_LEVEL·level`, `0x11a66f5–0x11a671f`), and prefers railway unless
naval is strictly greater (`cmp %rcx,%rdx / jge 0x11a68cd` at `0x11a6722`). **C**

### OURS

- Capacity as **min-over-authored-segments** is the right cheap model: the path is authored geography, the
  bottleneck is derived, one integer changes when a bridge falls.
- Harvest the linear damage tax, not the numbers: *one destroyed segment removes a constant from the
  corridor, and the constant scales with the corridor's own tier*. That gives the insurgent a crisp
  target-selection rule — on a level-5 trunk a single cut costs 71 % of throughput, on a level-1 spur the
  same cut costs 33 %. It also means a defender's repair is worth more on high tiers, which is exactly the
  asymmetry a small force wants.
- Do not adopt `MAX_RAILWAY_LEVEL` clamping at write time as the model. It exists because their array is
  fixed-arity; ours should refuse an out-of-range authored level at load with a named error.

---

## 3. Reach: five passes, a distance-growing penalty, and a compiled sigmoid

### 3.1 The tick is five propagation passes plus a finaliser

`0x113c8a0` (451 B) is the per-country driver and calls, in order:

```
0x1145ae0   pre-pass (air-drop origin setup; reads 0x11a5db0)
0x1145e50   pass A (5,103 B)
0x1147240   pass B (5,033 B)
0x114a7c0   pass C (6,149 B)
0x114bfd0   pass D (5,723 B)
0x114d630   pass E (4,877 B)
0x114e940   finalise
```

call sites `0x113c8cb`, `0x113c8dc`, `0x113c8ed`, `0x113c8fe`, `0x113c90f`, `0x113c91a`. Passes A and B
read only the falloff/infra/river dials; C, D and E each read all three source triples
(capital / built node / naval base) and select by node type. **C**

Selection triples, with authored values:

| Source | initial flow | starting penalty | added penalty | Read sites (C/D/E) |
| --- | --- | --- | --- | --- |
| capital | 5.0 | 0.5 | 1.2 | `0x4406648/58/68` @ `0x114adce–dc`, `0x114c2e8–f6`, `0x114d90f–25` |
| built node | 2.8 | 0.5 | 0.7 | `0x4406678/88/98` @ `0x114adfc–e0a`, `0x114c30e–1c`, `0x114d933–44` |
| naval base | 3.3 | 0.84 | 1.1 | `0x44066a8/b8/c8` (4 switch arms each) |
| floating harbour | 2.6 | 0.8 | 0.8 | `0x4406728-48`, used in `0x113f900` |

Note the shape: a capital projects **further** (5.0 at 1.2/step) but starts higher; a built node decays
slower (0.7/step) from a lower 2.8. Both start with the same 0.5 first-step.

### 3.2 The propagation step (observed in pass A, `0x1145e50`)

Breadth-first queue (`0x1146a50`–`0x114c40`; growth factor 1.5 at `0x1146b98`), visited array at
`0x1146aa2`, per-province flow array written at `0x11470d1`:

```
for each neighbour p of the current entry:
    if state[p] == visited && flow[p] >= candidate: skip      ; 0x11470b9–0x11470c4
    candidate = flow[current] − penalty                       ; 0x114709d  sub %rcx,%r12
    flow[p] = candidate                                        ; max-keep, not overwrite
    assert candidate < flow[current]                           ; "NeighborFlow < CurrentEntry._Flow" 0x35a939c @0x11470f3
    enqueue p with distance+1                                  ; 0x1147144  add $0x1,%cl
```

So a province keeps the **best** of the paths that reach it (relaxation), while each single step is
strictly decreasing. The distance counter is a **byte**, incremented per hop. **C**

### 3.3 Penalty composition per step

Observed in the same loop:

| Term | Mechanism | Offsets |
| --- | --- | --- |
| distance | `d` = hop count (byte), `d·1e5` in fixed point | `0x1146a2d–0x1146a3b`, `0x1147140–0x1147147` |
| infrastructure | `infraRatio = infra_level / d`, asserted `≤ 1.0` (`0x35a9386` @ line `0x7b3`) | `0x1146c59–0x1146c6e` |
| infra relief | `penalty ← penalty · (1 − (1−f)·infraRatio)` with `f = 1 − SUPPLY_FLOW_DROP_REDUCTION_AT_MAX_INFRA` | `0x1146a07`, applied `0x1147057–0x1147096` |
| river | `penalty += SUPPLY_FLOW_PENALTY_CROSSING_RIVERS` when the neighbour's byte `& 0xfe == 2` | `0x114702b–0x1147048` |
| distance curve | §3.4 | `0x1146e74–0x1146f60` |

`SUPPLY_FLOW_DROP_REDUCTION_AT_MAX_INFRA = 0.30` (`:4309`), `SUPPLY_FLOW_PENALTY_CROSSING_RIVERS =
0.20` (`:4310`). Full infrastructure therefore removes up to 30 % of each step's penalty; a river
crossing adds a flat 0.2 to the step. **C**

### 3.4 The four falloff dials: the site, and why the curve is not re-shapeable

The evaluation site the prior pass could not find is the block at `0x1146e74–0x1146f60`, present
**five times** — once per pass, at `0x1146e85`, `0x1148230`, `0x114bbfc`, `0x114d1c9`, `0x114e599`:

```
x    = −K · (d − MIDPOINT)                                ; K negated by 0x34a0cb0 @0x1146e8f
                                                          ; d·1e5 − MIDPOINT @0x1146e94–0x1146ea9
      = pow(E, x)                                         ; call 0x34a0ec0 @0x1146ed2,
                                                          ;   base pointer 0x35a86f8 = int64 271828 = e·1e5
L    = SCALAR / (1 + pow)                                 ; 0x1146edf–0x1146f27
L    = max(L, MIN_PENALTY_SCALE)                          ; cmp/cmovg 0x1146f30–0x1146f33
step = base · (1 + L·X) / 1e5 …                           ; imul 0x1146f37, +1.0 at 0x1146f56, imul 0x1146f5c
```

So the documented closed form `scalar / (1 + e^(−k(d−midpoint)))` is **literally what runs**, in
fixed point, with `e` as a stored constant and an integer `pow` (0x34a0ec0: sign/parity handling for
negative bases, integer-part loop adding `0x186a0`, fractional series — not libm). That closes
`hoi4-decomp-supply.md` §5 follow-up 1 and *refines* its §2 finding: there is no exponential *call*
because the exponential is a fixed-point base-e `pow`.

Evaluated at the authored dials (`K=1.3`, `MIDPOINT=2.3`, `SCALAR=0.9`, `MIN=0.25`):

| d (provinces from source) | 1 | 2 | 3 | 4 | 5 | 6 | 8 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `L(d)` | 0.250 (clamped) | 0.363 | 0.642 | 0.811 | 0.874 | 0.893 | 0.900 |

`L` is a **penalty scale in [0.25, 0.90]** — it multiplies a per-step penalty that itself grows with
distance, so the reach profile is the product of two increasing functions and is *stiff*: flattening it
requires patching code, not numbers. This confirms the prior pass's negative finding and answers its
"approximated, not re-shapeable" hypothesis precisely: the *form* is exact, the *composition* is fixed,
and the four dials only slide and clamp the multiplier.

**Partially unresolved:** the two coefficients in `step = base · (1 + L·X)` — `base` is a stack value
loaded at `0x1146e5b`, `X` is `*(*(*(obj+0xd8)+0xa8)+0x1d0)` loaded at `0x1146e74`. I read the
arithmetic order with certainty but not which of the two carries `(STARTING + ADDED·d)`. Two candidate
compositions give capital-on-foot reach of ≈1.5 or ≈3 provinces; the second fits the game's observed
behaviour and the define comments better. Treat the *shape* as established and the *absolute reach* as a
range.

### 3.5 Delivery at the edge: the 0.1 ramp

`0x11a5dd0` (124 B) is a one-line policy function: `if flow < SUPPLY_FLOW_REDUCTION_THRESHOLD (0.1):
amount ← amount · flow/0.1`. Its only caller is the consumer-supply reducer `0x1142900`
(call at `0x1142aeb`), and it gates its own call on a global flag byte at `0x438ef00`
(`0x1142adb–0x1142ae2`).

Read carefully this is **not** "flow < 1.0 delivers proportionally". Above 0.1 the amount is untouched;
below 0.1 it fades linearly to zero at flow 0. The ragged edge keeps a trickle, and the define's comment
("if supply flow is lower than this, it is not applied") describes the 0.1 knee, not a cliff. **C**

### 3.6 Node cap and railway bonus

`0x1180ae0` (366 B) assembles a node's supply cap:

```
cap = Σ(per-source pools) − motorisation-baseline + (MAX_RAILWAY_LEVEL − node+0x94) · NODE_FLOW_BONUS_PER_RAIL_LEVEL
      ; 0x1180b74–0x1180bb1, dial at 0x44066e8 = 0.34
if (node+0x48 + node+0x20 + node+0x38) > 0:
    share = 1 − node+0x48·1e5 / (node+0x48 + node+0x20 + node+0x38)     ; 0x1180bb4–0x1180c12
    cap   = max(0, cap) · share / 1e5                                  ; 0x1180c1b–0x1180c40
```

`0x94` is compared to `MAX_RAILWAY_LEVEL` elsewhere (`0x738592`), so it is a railway-level quantity; if
it counts *damaged* levels then the bonus is `0.34 × effective level`, which matches
`NODE_FLOW_BONUS_PER_RAIL_LEVEL`'s published meaning ("node flow increases by this amount per railway
level of the node's bottleneck"). I record the expression as observed and that reading as **probable,
not certain**. **C**

### OURS

- The logistics curve is the exact primitive Babylon forbids: a fitted sigmoid whose parameters are
  exposed and whose shape is compiled. Copy the *decomposition* (per-step penalty × a distance-dependent
  scale) only if the scale is itself a modelled quantity; otherwise model stock and flow and let decay
  fall out. This pass is now hard evidence that HOI4 could not re-shape its own curve with its own dials.
- The `infraRatio = infra/d` term is the interesting one and it is *not* a curve: infrastructure near the
  source matters more than infrastructure far away because it is divided by distance. That is a
  defensible mechanism — a road's quality is worth more the closer it is to the depot.
- The 0.1 ramp is a good pattern for "barely supplied": below a knee, deliver a fraction rather than
  nothing. It keeps a cut-off force alive at reduced effectiveness instead of toggling it off, which is
  what makes interdiction a *pressure* rather than a switch.

---

## 4. The per-tick budget: `_TotalSupply`, `_RemainingSupply`, and proportional allocation

### 4.1 The pool and its two asserts

In the flow-cache node (stride `0xe8`): `+0x38` = `_TotalSupply`, `+0x40` = `_RemainingSupply`.

| Invariant | Text | Site |
| --- | --- | --- |
| `_TotalSupply >= _RemainingSupply` | `0x35a8c24` | `0x1141313–0x114131b` |
| `_RemainingSupply >= 0` | `0x35aaa96` | `0x1186935–0x118693d`, after the allocation loop |
| unused = total − remaining, then forwarded | — | `0x114f805–0x114f80d` |

`0x1141010` (5,919 B) walks the node array and **skips any node whose total equals its remaining**
(`0x1141364–0x114136c`) — i.e. it acts only on nodes that actually spent supply this tick. Divergence
between the two fields is therefore a *within-tick* artefact, and the pool is re-derived each tick. I did
not observe the reset store itself; marked **probable**.

### 4.2 Allocation is one ratio, applied per consumer

`0x1183ee0` (15,135 B) is `AssignConsumersToNodes`-side allocation:

```
asked_sum = Σ consumers[i].asked                        ; 0x1186610–0x118661c, stride 0x18
if asked_sum == 0: ratio = 1.0                          ; 0x118675c
else: ratio = min(1.0, node->_RemainingSupply·1e5 / asked_sum)   ; idiv 0x11867a1–0x11867a3
     if ratio <= 0: return                              ; 0x11867ae
for i in consumers:
    if ratio < 1:  share = asked[i] · ratio / 1e5       ; 0x118681c–0x118683f
    if ratio<1 and last: share = min(remaining, asked[i]) ; 0x11868f9–0x1186907 (rounding top-up)
    consumer->received (+0x68) += share                 ; 0x1186846
    consumer->has_supply (+0x1b) = 1                    ; 0x118684a
    RecordReceived(share)                               ; 0x117fb70, asserts _ReceivedSupply <= _AskedSupply
    node->_RemainingSupply -= share                     ; 0x118685a
    province.available            -= (share − consumer local ally part)  ; 0x1186877–0x118687e
    assert province._TotalNeed >= ProvCapReduction      ; 0x35a944a @0x11868a4–0x11868db
```

**Consequences that matter:**

1. Shortage is shared **proportionally, uniformly** — there is no consumer priority, no "front first".
   A cut degrades every consumer in the subtree by the same factor.
2. The last consumer absorbs the rounding remainder, so the pool empties exactly (`remaining >= 0` assert
   is a real check, not decoration).
3. `_ReceivedSupply <= _AskedSupply` is asserted at the consumer object (`0x35aa686` @ `0x117fac3`), so
   over-delivery is a diagnosed bug — the accounting is exact fixed point throughout.
4. The province has its *own* budget, decremented in parallel and asserted against `_TotalNeed`
   (`0x35a944a`), so node supply is capped by province need as well as by flow.

### 4.3 Leftovers are forwarded, and **duplicated at branches**

`0x114f770` (720 B):

```
for node n in cache:
    if n->connected(+0xc) != 0: skip
    if n->type(+0x8) > 5 or type ∈ {0,1,4,5} (mask 0x33): skip        ; 0x114f7f0–0x114f803
    unused = n->_TotalSupply(+0x38) − n->_RemainingSupply(+0x40)
    if unused <= 0: skip
    n->incoming(+0x30) += unused                                      ; 0x114f80f
    for each downstream neighbour m (via 0x1156c50): m->incoming(+0x30) += unused   ; 0x114f95f
```

This is the single most consequential structural fact in the whole chain: **unused supply is added in
full to every downstream neighbour, not split between them.** Supply is a *relaxation/broadcast* value,
not a conserved flow. A branching network therefore over-supplies its branches, and the only place where
interdiction is decisive is the **last edge before a subtree** (everything downstream of a cut loses its
whole upstream contribution) — whereas cutting one of two parallel routes removes nothing, because the
other route's leftover arrives in full. **C**

### OURS

- Adopt the two-field pool (`total`, `remaining`) plus per-consumer `asked`/`received` pairs: it makes a
  receipt able to say *why* a consumer got what it got, and the `remaining >= 0` / `received <= asked`
  pair are cheap invariants that catch the two ways an allocator usually rots.
- Do **not** adopt broadcast leftovers. It is the reason HOI4 supply is generous at branches and why
  cutting a redundant corridor feels inert. Babylon should conserve: split a node's surplus by an authored
  or measured share, so redundancy costs the defender something and interdiction has a measurable yield.
- The uniform proportional cut is worth keeping for a different reason: it is *legible*. If a player cuts
  a corridor, every unit downstream drops by the same fraction, and the receipt can name the fraction.

---

## 5. What a cut actually costs

### 5.1 The disconnected condition, as the game itself tests it

`supply_gui_utils.cpp` (`0x11b6590`, 16,985 B) appends the "disconnected" line when:

```
node->supply_from_capital (+0x98) <= 0   AND   node->connected_flag (+0xc) == 0
```

`0x11b7ca1–0x11b7cb6`, string `SUPPLYMODE_TOOLTIP_DISCONNECTED` `0x35ad1f4`; otherwise it appends
`SUPPLYMODE_TOOLTIP_SUPPLY_FROM_CAPITAL` (`0x35ad239`) with `max(0, value)` (`0x11b7d19–0x11b7d2c`).
**C**

A severed node is therefore *not* a node at zero — it is a node that receives nothing from the capital
and is flagged disconnected. It keeps its own local pools (the three additive fields), which is why a
cut-off province still supplies some units.

### 5.2 What survives a cut: local state supply

State supply is computed independently of any corridor, in `0x11b4000` (9,612 B), whose UI strings are
`STATE_SUPPLY_HEADER`, `TOTAL_STATE_SUPPLY`, `BASE_STATE_SUPPLY`, `STATE_INFRA_SUPPLY`,
`STATE_POP_SUPPLY`, `STATE_SUPPLY_CONTROL_SCALE`, `STATE_VP_SUPPLY_*`, `STATE_AIRDROP_SUPPLY`
(`0x35acec7–0x35acf93`):

```
infra_supply  = ((intact_infra + 0.15·damaged_infra) · INFRA_TO_SUPPLY)          ; 0x11b4206–0x11b4252
base          = SUPPLY_BASE_MULT · state_base                                     ; 0x11b425d–0x11b4279
pop_supply    = AVAILABLE_MANPOWER_STATE_SUPPLY · f(manpower)                     ; 0x11b42c0–0x11b42dc
                × NON_CORE_MANPOWER_STATE_SUPPLY if the holder is not the owner    ; 0x11b4361–0x11b438a
vp_supply     = Σ over state VPs: VP_TO_SUPPLY_BASE + VP_TO_SUPPLY_BONUS_CONVERSION·vp_level
                                                                                  ; 0x11b443a–0x11b4474
```

with `INFRA_TO_SUPPLY = 0.3`, `SUPPLY_FROM_DAMAGED_INFRA = 0.15`, `SUPPLY_BASE_MULT = 0.2`,
`AVAILABLE_MANPOWER_STATE_SUPPLY = 0.18`, `NON_CORE_MANPOWER_STATE_SUPPLY = 0.2`,
`VP_TO_SUPPLY_BASE = 0.2`, `VP_TO_SUPPLY_BONUS_CONVERSION = 0.05` (`:4362-4370`). **C**

So: infrastructure damage cuts local supply *by 0.3 per level* but damaged infrastructure still yields
`0.15` — half of intact. A cut that damages infrastructure does **both** things at once: removes capital
flow and reduces the local fallback. That is the only way to actually starve a position.

### 5.3 Timers around a cut

| Effect | Value | Evidence |
| --- | --- | --- |
| railway unusable after capture | `RAILWAY_CONVERSION_COOLDOWN = 10` days, `_CORE = 5`, `_CIVILWAR = 0` | `00_defines.lua:4386-4388`; live `0x4406ad8/ad…`; `pInfo->IsOnCooldown()` assert `0x35aa517` @ `0x117b2b8` |
| country skips supply entirely while its capital is not controlled | — | `Skipping calculating supply data because _pCapital->GetController() != CountryTag` `0x35a8fa9` @ `0x113c7cf` |
| moving the supply capital | needs surrender ratio > 0.15, 30-day cooldown, full supply only after 21 days | `00_defines.lua:4405-4408`, read at `0x4406908/918/928/938` |
| nodes not reachable from the capital | tracked as `_NonLocalNodes`; asserts that capital and built-supply provinces are *not* in it | `0x35a8ffb/0x35a9076/0x35a9119` in `0x114ec40`, `0x114d630`, `0x114bfd0` |
| "no node available" / "Supply flow was zero" | hard failures reported, not silently degraded | `0x35a929e` @`0x114dfe3`; `0x35a8c81` @`0x1142350`, `0x11424dd` |

The 10-day rail cooldown is the game's own admission that capture-without-destruction is a *delay*
weapon: the line survives and the attacker simply cannot use it for ten days.

### 5.4 What a consumer loses, and what it keeps

`0x1142900` (1,200 B) computes the delivered amount per consumer:

```
factor = MIN_TRAIN_SUPPLY_FACTOR + (1 − MIN_TRAIN_SUPPLY_FACTOR)·train_availability(node+0x150)
       ; 0.5 + 0.5·x, dial 0x4406ab8 @0x1142a4e
share  = asked · per_country_share · factor / 1e5          ; 0x1142aa1–0x1142ad3
share  = ramp_0.1(share, flow)                             ; 0x11a5dd0 @0x1142aeb
consumer->reduced (+0x20) = share                          ; 0x1142b02
```

So the **worst case from having no trains is half supply** (`MIN_TRAIN_SUPPLY_FACTOR = 0.5`), and
`MIN_TRAIN_REQUIREMENT = 2` waives the penalty entirely when the requirement is ≤ 2
(`0x11b157b` in `0x11b0f20`). `SUPPLY_POINTS_PER_TRAIN = 1.0` and
`NUM_RAILWAYS_TRAIN_FACTOR = 0.03` (train need scales with rail distance) are read at `0x113ca94`,
`0x113d508`.

### OURS

- Model a cut as **three separate effects with three different clocks**: flow stops now, the line is
  unusable for N days if captured rather than destroyed, and local supply continues at a damaged-infra
  rate. A single "supply = 0" rule would lose the most interesting decision in the system (destroy vs
  capture; starve vs occupy).
- Trample the hidden half: `MIN_TRAIN_SUPPLY_FACTOR` silently caps the penalty from rolling stock at 50 %.
  Babylon should either model rolling stock as a real constrained stock or not model it — a floor nobody
  can see is a curve in disguise.
- A cut-off force eating local supply is the correct default for an insurgency game: the countryside is
  never *empty*, it is just poor. That is what makes dispersal a strategy.

---

## 6. Buffers and stockpiles (and what is *not* a stockpile)

### 6.1 Army supply ratio: the only true accumulator

`0x11a95f0` (267 B) is called per army (`0x1347e54`, `0x1a92ebd`) with out-pointers for a stored amount
and a gain rate:

```
if (ratio(+0x40) < 1.0 && grace >= ratio):
    stored += (1.0 − ratio) · STORED_SUPPLY_CONSUMPTION_RATE_FACTOR / 1e5     ; 0x11a965b
    gain    = ARMY_SUPPLY_RATIO_STARTING_GAIN (0.0)                         ; 0x11a9684
else:
    gain = max(gain, STARTING_GAIN) + ARMY_SUPPLY_RATIO_SPEED_GAIN_PER_HOUR  ; 0x11a96b3
    gain = min(gain, ARMY_MAX_SUPPLY_RATIO_GAIN_PER_HOUR)                    ; 0x11a96c0
    stored = min(stored + gain, cap)                                         ; 0x11a96d1–0x11a96de
if stored < 0: stored = 0                                                    ; 0x11a96e6
```

Authored: `ARMY_SUPPLY_RATIO_STARTING_GAIN = 0.0`, `ARMY_SUPPLY_RATIO_SPEED_GAIN_PER_HOUR = 0.01`,
`ARMY_MAX_SUPPLY_RATIO_GAIN_PER_HOUR = 0.15`, `STORED_SUPPLY_CONSUMPTION_RATE_FACTOR = 0.75`
(`00_defines.lua:4399-4401`, `:4425`).

Material reading: **recovery from zero supply takes ~100 hours (≈4.2 days)** at the default 1 %/hour, can
be no faster than 15 %/hour, and while under 100 % the army also accrues a stored-supply amount at 75 %
of its deficit. This is the *only* place in the chain where supply accumulates across ticks. **C**

### 6.2 The node pool is per-tick, not a stockpile

Despite `_TotalSupply >= _RemainingSupply` looking like a tank, `_RemainingSupply` is reset from
`_TotalSupply` each tick (nodes with total == remaining are skipped as "did nothing",
`0x1141364`); leftover supply is *forwarded* within the tick (§4.3), not banked. **No node-level supply
stockpile exists in this build.** Any "stockpile" the UI shows is the army-ratio accumulator above. **C**

### 6.3 Trucks and attrition (numbers only)

`TRUCK_ATTRITION = 0.003`, `TRUCK_ATTRITION_FACTOR = 0.65`, `BASE_TRUCK_HP = 100`
(`00_defines.lua:4380-4384`), read in `0x1152060` at `0x1152b1b`, `0x1152be3`, `0x1152bc9`;
`SUPPLY_THRESHOLD_FOR_ARMY_ATTRITION = 0.35` (`:4421`) — below 35 % supply an army takes attrition.
Truck/train stock is per country (`CCountrySupplySystem::STruckInfo`, `STrainInfo`, 42-entry inline
buffers). **C**

### OURS

- One accumulator, with an explicit gain ceiling and an explicit recovery constant, is enough for
  "logistics has inertia". Put the numbers where a player can see them ("supply recovery 1 %/hour, max
  15 %/hour") — HOI4 hides both, which is why its supply feels like weather.
- The 75 %-of-deficit stored amount is a second hidden dial with no visible consumer in this chain. Do not
  import it.

---

## 7. Consolidated material factors

| Quantity | Value | Source |
| --- | --- | --- |
| capital supply cap | `5.0 + 0.3·civ + 0.6·mil + 0.4·dockyard` | `:4267-4270`, helpers `0x11a8f10`,`0x11a9020`,`0x11a9090`,`0x11a9100` |
| capital reach seed | 5.0 flow, 0.5 start, +1.2/province | `:4273-4275` |
| built-node reach seed | 2.8 flow, 0.5 start, +0.7/province | `:4278-4280` |
| naval-base reach seed | 3.3 flow, 0.84 start, +1.1/province | `:4283-4285` |
| railway capacity | `10 + 5·bottleneckLevel` (10…35) | `:4333-4334`, `0x11a5c80` |
| railway damage tax | `5.0 · level · (1−health)` | `:4335`, `0x11a5cc0` |
| node cap rail bonus | `0.34 · (5 − field@0x94)` | `:4288`, `0x1180b74` |
| infra relief of penalty | up to 30 % at full infra, scaled by `infra/d` | `:4309`, `0x1147057` |
| river crossing | +0.2 penalty per crossing | `:4310`, `0x1147037` |
| distance curve | `0.9/(1+e^(−1.3(d−2.3)))`, clamped ≥ 0.25 | `:4317-4320`, `0x1146e74` |
| trickle knee | below 0.1 flow, deliver `flow/0.1` | `:4396`, `0x11a5dd0` |
| supply per train | 1.0 point; need ∝ rail distance × 0.03 | `:4390-4391` |
| train shortfall floor | ×0.5, waived if need ≤ 2 | `:4393-4394` |
| army recovery | +1 %/h default, ≤15 %/h, ~4.2 days 0→100 % | `:4399-4401`, `0x11a95f0` |
| attrition threshold | army supply < 35 % | `:4421` |
| local state supply | `0.2·base + 0.3·(intact + 0.15·damaged infra) + 0.18·pop + Σ_VP(0.2+0.05·lvl)` | `:4362-4370`, `0x11b4000` |
| rail after capture | 10 days (5 core, 0 civil war) | `:4386-4388` |
| infantry battalion demand | 0.05–0.06 supply | `common/units/infantry.txt:46,169` |

**Conversion for intuition:** a 9-battalion infantry division asks ≈0.5 supply, so a level-1 railway
(15 points) feeds ≈30 such divisions, a level-5 trunk (35) ≈70, and a single destroyed segment on a
level-5 trunk drops it to 10 — ≈18 divisions. A 20-civ/10-mil capital (≈17 points) supports ≈34
divisions from its own production before any corridor.

---

## 8. Evidence ledger

Coordinates are file offsets = link-time virtual addresses (`.text 0x50d2f0–0x35056f2e`,
`.rodata addr == offset == 0x3506000`). Function ranges from `.eh_frame`; instruction addresses from
`objdump -d`. No REA Evidence IDs (provider unused, §0).

| # | Claim | Coordinate | How verified |
| --- | --- | --- | --- |
| M1 | PIE image base `0x100000`; raw-vaddr decompilation returns wrong bytes | `0x11a6f10` vs program `0x21a6f10` | Ghidra 12.1.4 headless, both bases; second returned a 6-instruction stub for an 811-byte FDE range |
| M2 | NSupply dial → `.bss` storage map (102 keys) | `0x4406588`–`0x4406be8`; readers `0x1ea7710`–`0x1ead7c5` | generated-reader `lea` pairs; `MAX_RAILWAY_LEVEL`→`0x4406588` at `0x1ea77cc` |
| I1 | tuple key is a province id, dumped among 27 cache keys | `0x35aa9fc`; table `0x35aa87f–0x35aaa63`; TU `0x35aa840` | `dd`/`strings`; dump emission `0x1189827` |
| I2 | node persisted as id + data blob | tokens `0x35a8a00/66/8a`; loader `0x1138a90` | retained asserts + FDE range |
| I3 | per-country data is an overlay inside the node | RTTI `CAssociativeArray<CCountryTag, SSupplyNodeData::SConvoyAndTrainInfoPerCountry>`, `SConsumerData` (25), `SStateSupplyInfo::SPerCountryInfo` (42) | RTTI strings in `0x35a82xx–0x35a87xx` |
| I4 | dump values are 3-dword-xor fingerprints, not quantities | `0x118980e–0x1189836` | `imul $0x186a0` of `xor` of three stack dwords |
| C1 | `_RailwayLevelsToNeighbors` per-edge int, clamped at write to 5 | `0x1178ff5–0x1179003`; asserts `0x35aa352`,`0x35aa2f2` | `cmp/jle` clamp after assert block |
| C2 | capacity = min edge level along path, seeded with MAX | `0x11a6f10`, `cmovl` at `0x11a6f71`, seed at `0x11a6f2e` | full function disassembly |
| C3 | railway flow `10 + 5·level`; damage tax `5·level·(1−health)` | `0x11a5c80`, `0x11a5cc0`, `0x11a5d20`, `0x11a5e50`@`0x11a66b8` | full function disassembly + dial addresses |
| C4 | naval flow `5 + 3·level`; railway wins ties | `0x11a66f5–0x11a6725` | `cmp/jge` |
| R1 | five propagation passes then finalise | driver `0x113c8a0`, calls `0x113c8cb…0x113c91a` | direct-call scan + FDE |
| R2 | BFS relaxation, best-path keep, distance byte+1 | `0x1146a50`, `0x11470b9–0x11470d1`, `0x1147144` | disassembly |
| R3 | step penalty minus current flow; `NeighborFlow < CurrentEntry._Flow` | `0x114709d`, assert `0x35a939c`@`0x11470f3` | disassembly + assert |
| R4 | infra ratio `infra/d`, assert ≤1; 30 % relief at full infra | `0x1146c59–0x1146c6e` (assert `0x35a9386` line `0x7b3`), `0x1146a07`, `0x1147057–0x1147096` | disassembly |
| R5 | river +0.2 on crossings | `0x114702b–0x1147048` | disassembly |
| R6 | logistic evaluated in fixed point, base e = 271828, `pow` not libm | `0x1146e74–0x1146f60`; `0x34a0cb0` (neg), `0x34a0ec0` (pow), const `0x35a86f8` | disassembly; `int64 271828` at the constant slot |
| R7 | 0.1 trickle knee | `0x11a5dd0`; call `0x1142aeb` | disassembly |
| R8 | node cap = pools + `0.34·(5−field)` then × share ratio | `0x1180ae0`@`0x1180b74–0x1180c40` | disassembly |
| A1 | `_TotalSupply` `+0x38`, `_RemainingSupply` `+0x40`; total ≥ remaining | asserts `0x35a8c24`@`0x1141313`, `0x35aaa96`@`0x1186935` | retained asserts + FDE |
| A2 | one ratio `min(1, remaining/asked)`, proportional shares, last-consumer top-up | `0x118675c–0x1186907` | disassembly |
| A3 | per-consumer `received`, flag, pool decrement, province decrement | `0x1186846–0x118687e` | disassembly |
| A4 | `_ReceivedSupply <= _AskedSupply` asserted per consumer | `0x35aa686`@`0x117fac3` | assert |
| A5 | province need cap assert | `0x35a944a`@`0x11868a4` | assert |
| A6 | leftovers forwarded in full to **each** downstream node | `0x114f770`@`0x114f805–0x114f95f` | disassembly |
| S1 | disconnected = no capital supply AND flag clear | `0x11b7ca1–0x11b7cb6`; `0x35ad1f4` | disassembly + tooltip strings |
| S2 | local state supply formula (infra/VP/pop/base) | `0x11b4206–0x11b4474` in `0x11b4000` | disassembly + dial addresses |
| S3 | railway cooldown 10/5/0 days; `IsOnCooldown` assert | `:4386-4388`; `0x35aa517`@`0x117b2b8` | script + assert |
| S4 | skip supply when capital is not controlled | `0x35a8fa9`@`0x113c7cf` | assert |
| B1 | army ratio recovery +1 %/h, ≤15 %/h, stored 75 % of deficit | `0x11a95f0`@`0x11a965b/9684/96b3/96c0` | full function disassembly |
| B2 | train shortfall floor 0.5, waiver at need ≤2 | `0x1142a4e`, `0x11b157b` | disassembly + dial addresses |
| B3 | no node-level stockpile: total==remaining skipped, leftover forwarded in-tick | `0x1141364`, `0x114f770` | disassembly |

---

## 9. Uncertainty, and what I could not close

1. **Falloff composition** (§3.4). The formula, the clamp and the five sites are certain; which operand
   carries `(STARTING + ADDED·d)` is not. Absolute reach numbers are therefore a range (≈1.5–3 provinces
   on foot for a capital). I did not guess a value into §7.
2. **`field@0x94` sign** (§3.6). The expression is `(MAX − field)·0.34`, added. If the field is *damaged*
   levels this equals the published "per bottleneck level" bonus; if it is the level itself, the sign is
   inverted relative to the comment. Recorded as observed, reading flagged probable.
3. **`RIVER_RAILWAY_LEVEL`** is read only by the tooltip in this build (`0x11b95fb`). Whether river
   transfer is implemented elsewhere or dead is unresolved.
4. **`RAILWAY_MIN_FLOW`** read sites (`0x1177250`, `0x1177c50`) are in `railway_manager.cpp` and their role
   was not decompiled; the 10.0 floor I report comes from `RAILWAY_BASE_FLOW`.
5. **Node type enumeration.** Types `0,1,4,5` are excluded from leftover forwarding (mask `0x33`,
   `0x114f7f7`); I did not establish which type index is capital / built / naval / harbour. The triples are
   matched to node classes by which dials the switch arms load, which is strong but indirect.
6. **The 27-key dump's numbers are hashes** (§1.3) — prior passes' reading of that table as a state
   decomposition stands, but its values must not be quoted as quantities.
7. **Tick rate.** All rates are per hour in the defines; I did not verify how many supply passes run per
   game hour (the driver `0x113c8a0` is called from the country update; caller not traced).

### Non-goals for Babylon

- Do not re-implement the five-pass propagation. It exists to make a 4,000-province world cheap on a
  shared read-mostly cache; our circuit is a per-period authored network.
- Do not adopt broadcast leftovers (§4.3). It is the single design choice that makes HOI4 interdiction
  feel inert, and Babylon's whole premise is that interdiction pays.
- Do not expose the four falloff dials "for tuning". A compiled sigmoid with four sliders is the exact
  artefact the constitution refuses, and this pass now has the offsets to prove it is not re-shapeable.
- Do not add a hidden rolling-stock floor or a hidden stored-supply factor. Both are invisible
  multipliers that a player cannot reason about.
- Do not take `_RemainingSupply >= 0` as licence for a mutable third field. One pool value plus recorded
  per-consumer pairs is enough; the third field is what forces the assert.
