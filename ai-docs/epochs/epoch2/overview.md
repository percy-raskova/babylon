# Epoch 2: The Foundation

**Status**: IN PROGRESS
**Theme**: "Real Data, Real Geography, Real Scale"

## Summary

Epoch 2 builds the infrastructure needed for continental-scale simulation:
- Real economic data from federal APIs (Census, FRED, BLS)
- Real coercive infrastructure data (HIFLD prisons, police; MIRTA military)
- H3 hexagonal coordinate system for geographic precision
- PyQt + pydeck visualization capable of rendering 74,000+ territories

## Why This Epoch Exists

Epoch 1 validated mechanics with abstract territories (T001, T002...).
Epoch 3 requires simulating the actual United States with:
- 50 states
- 3,000+ counties
- 70,000+ cities/townships

This requires:
1. **Real Data**: Economic flows, demographics, infrastructure
2. **Real Geography**: H3 hexagonal coordinates for precise positioning
3. **Scalable Visualization**: DearPyGui cannot render 74,000 territories

## Slices

| Slice | Name | Status | Description |
|-------|------|--------|-------------|
| 2.1 | 3NF Schema | COMPLETE | SQLite schema with dim/fact tables |
| 2.2 | Census Loaders | COMPLETE | QCEW, CBP, population data |
| 2.3 | Economic Loaders | COMPLETE | FRED, Energy, Trade, Materials |
| 2.4 | Circulatory Loaders | COMPLETE | HIFLD, MIRTA, FCC broadband |
| 2.5 | H3 Geographic System | PLANNED | Hexagonal territory coordinates |
| 2.6 | PyQt Visualization | PLANNED | Replace DearPyGui |
| 2.7 | Schema Integration | PLANNED | Bridge data layer to simulation |

## Dependencies

- Epoch 1 must be complete (simulation mechanics)
- API keys required: CENSUS_API_KEY, FRED_API_KEY, FCC credentials

## Success Criteria

Epoch 2 is complete when:
1. All API loaders operational and tested
2. H3 coordinates assigned to all territories
3. PyQt dashboard renders 3,000+ county hexagons
4. Simulation can hydrate state from database
