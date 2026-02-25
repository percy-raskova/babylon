# Article VIII: Anti-Patterns

> Annex to [Babylon Constitution](../constitution.md). This file contains the full anti-pattern descriptions with code examples.

The following patterns MUST be rejected upon detection:

### 1. Solidarity as Scalar

**Wrong**: `solidarity_points += organizing_action`

**Right**: Edge type transforms from TRANSACTIONAL to SOLIDARISTIC

Solidarity is relational, not quantitative.

### 2. Union Density as Revolutionary Indicator

US unions are largely labor aristocracy institutions. High union density in the core correlates with imperial rent distribution, not revolutionary potential.

Union presence MAY correlate with organizational capacity but NOT with revolutionary consciousness without examining edge types.

### 3. Determinism from Material Conditions

Material conditions CONSTRAIN; they do not DETERMINE.

**Wrong**: `if material_conditions_x: revolution()`

**Right**: Material conditions set P(S|A) and P(S|R). Outcomes depend on strategic choices within those constraints.

### 4. Ungrounded Tensor Notation

See Section III.3. Tensor formalism without transformation laws is rejected.

### 5. Claims Without Falsifiability

See Section III.2. Theoretical assertions without testable predictions are not simulation mechanics.

### 6. Constants Without Data Sources

See Section III.1 and III.4. Every number must trace to primitives or data.

### 7. Superstructure Before Base

See Section VI.1. Implement material dynamics before ideological or repressive mechanics.

### 8. Decorative Visualization

See Section VII.10. Visual elements that carry no data are prohibited. Every visual choice MUST encode meaning or enable navigation.

### 9. Community as Pairwise Edge

**Wrong**: Representing community membership as pairwise edges between all members.

```python
# WRONG: Community of 5 members as 10 pairwise edges
for a, b in itertools.combinations(community_members, 2):
    G.add_edge(a, b, type="community")
```

**Right**: Community membership as a single XGI hyperedge.

```python
# RIGHT: Community is a hyperedge containing all members
H.add_edge(community_members, id="black_church_detroit")
```

Community is not a relationship between agents. It is a thing agents belong to. Flattening hyperedges into cliques destroys collective semantics, inflates edge count combinatorially, and makes community-level operations (state targeting, membership queries) impossible to express naturally. See II.7.
