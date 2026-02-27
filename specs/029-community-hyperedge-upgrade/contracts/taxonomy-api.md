# Contract: Taxonomy & Axis Query API

**Feature**: 029-community-hyperedge-upgrade
**Covers**: FR-001, FR-002, FR-010

## Functions

### get_contradiction_axis

```python
def get_contradiction_axis(community: CommunityType) -> ContradictionAxis | None:
```

**Preconditions**: `community` is a valid CommunityType member.
**Postconditions**:
- Returns ContradictionAxis if community belongs to a contradiction pair (Category 1)
- Returns None if community is institutional exclusion (Category 2) or lifecycle (Category 3)

**Test Cases**:
| Input | Expected Output |
|-------|-----------------|
| SETTLER | COLONIAL_AXIS |
| NEW_AFRIKAN | COLONIAL_AXIS |
| PATRIARCHAL | PATRIARCHAL_AXIS |
| WOMEN | PATRIARCHAL_AXIS |
| DISABLED | None |
| YOUTH | None |

### is_hegemonic

```python
def is_hegemonic(community: CommunityType) -> bool:
```

**Test Cases**:
| Input | Expected |
|-------|----------|
| SETTLER | True |
| PATRIARCHAL | True |
| NEW_AFRIKAN | False |
| DISABLED | False |
| YOUTH | False |

### is_marginalized

```python
def is_marginalized(community: CommunityType) -> bool:
```

**Note**: Institutional exclusion communities ARE marginalized.

**Test Cases**:
| Input | Expected |
|-------|----------|
| NEW_AFRIKAN | True |
| DISABLED | True |
| SETTLER | False |
| YOUTH | False |

### get_opposing_communities

```python
def get_opposing_communities(community: CommunityType) -> list[CommunityType]:
```

**Test Cases**:
| Input | Expected |
|-------|----------|
| SETTLER | [NEW_AFRIKAN, FIRST_NATIONS, CHICANO] |
| NEW_AFRIKAN | [SETTLER] |
| PATRIARCHAL | [WOMEN, TRANS] |
| DISABLED | [] |

### shared_marginalized_communities

```python
def shared_marginalized_communities(
    agent_a_communities: set[CommunityType],
    agent_b_communities: set[CommunityType],
) -> set[CommunityType]:
```

**Test Cases**:
| Agent A | Agent B | Expected |
|---------|---------|----------|
| {NEW_AFRIKAN, DISABLED} | {NEW_AFRIKAN, QUEER} | {NEW_AFRIKAN} |
| {SETTLER, DISABLED} | {SETTLER, DISABLED} | {DISABLED} |
| {YOUTH, ADULT} | {YOUTH} | {} |

## Validation Contract

### COMMUNITY_CATEGORY_MAP Exhaustiveness

At module load time, verify:
```python
assert set(COMMUNITY_CATEGORY_MAP.keys()) == set(CommunityType)
```

If a CommunityType member is added without updating COMMUNITY_CATEGORY_MAP,
this assertion raises immediately — not silently at runtime.
