# Gramscian Wiki Engine

**Status:** Brainstorm
**Created:** 2024-12-07
**Core Insight:** Hegemony isn't a stat - it's control over the player's interface to knowledge

## The Concept

Model Gramscian hegemony as factional control over an in-game wiki/knowledge base. The wiki IS the ideological state apparatus. Players don't read *about* hegemony - they experience mediated reality.

Same Ledger facts → different Jinja templates → different "reality"

## Why This Works

1. **Materialist epistemology** - Knowledge is produced by material interests
2. **Ideology as interface** - Not flavor text, but how you understand the game
3. **Counter-hegemony as gameplay** - Taking wiki sections = shifting "common sense"
4. **Teaches critical media literacy** - Players learn to read against the grain

## Proposed Structure

```
src/babylon/wiki/
├── templates/
│   ├── bourgeois/           # "Job creators", "protesters clash with police"
│   │   ├── event.md.j2
│   │   ├── faction.md.j2
│   │   ├── crisis.md.j2
│   │   └── concept.md.j2
│   ├── proletarian/         # "Owning class", "police attack workers"
│   │   └── ...
│   ├── petty_bourgeois/     # "Both sides", "complexity", "nuance"
│   │   └── ...
│   └── base/
│       └── _facts.j2        # Shared Ledger data accessors
│
├── generated/               # Rendered markdown (Obsidian-compatible)
│   ├── events/
│   ├── factions/
│   ├── concepts/
│   └── _graph.json          # Knowledge graph for visualization
│
├── control.json             # Which faction controls which domains
└── engine.py                # Rendering engine
```

## Template Examples

### Bourgeois Framing
```jinja
## {{ event.name }}

{{ facts.casualties }} individuals were injured when
**protests turned violent** near {{ event.location }}.

Authorities restored order after {{ facts.duration }} hours.
Property damage estimated at ${{ facts.damage | format_currency }}.
```

### Proletarian Framing
```jinja
## {{ event.name }}

**{{ facts.casualties }} workers injured** when police
attacked a peaceful demonstration in {{ event.location }}.

Workers held the line for {{ facts.duration }} hours.

*{{ facts.damage | format_currency }} in "property damage" =
{{ facts.damage / facts.avg_wage | round }} years of wages.*
```

## Obsidian Integration

- Markdown with `[[wikilinks]]` for bidirectional linking
- Graph view reveals ideological structure
- Bourgeois wiki never links "police" → "violence"
- But always links "protest" → "riot", "union" → "corruption"
- The *shape* of the knowledge graph encodes hegemony

## Gameplay Mechanics

### Reading Against the Grain
- No "true" wiki exists - only class perspectives
- Player must triangulate between sources
- Contradictions between wikis reveal cracks in hegemony

### Wiki Control as Struggle
- Factions compete for control of wiki domains
- Revolutionary victory = reframing what's "obvious"
- Partial control = contested narratives, visible seams

### Template Drift
- As contradictions intensify, bourgeois framing strains
- Templates might include `{% if crisis_level > 0.7 %}` blocks
- Hegemonic "common sense" visibly fractures

## Technical Considerations

### Why Jinja?
- Deterministic output (testable, validatable)
- LLM fills slots, doesn't hallucinate articles
- Easy to version control
- Extensible without breaking existing content

### Schema Integration
- Templates pull from existing Ledger (JSON data files)
- `control.json` tracks factional ownership
- Could add `wiki_control` field to faction schema

### Rendering Pipeline
```
Ledger (facts) + Template (framing) + Control (ownership)
    → Markdown
    → Obsidian vault / in-game reader
```

## Open Questions

1. Does the player ever see "objective" facts, or only mediated versions?
2. How granular is wiki control? Per-article? Per-section? Per-sentence?
3. Can players *write* counter-narratives, or only capture existing templates?
4. How does this interact with the Archive (ChromaDB/RAG)?
5. Performance: regenerate on-demand or batch render?

## Dependencies

- Jinja2 (already available via Flask ecosystem)
- Markdown renderer with wikilink support
- Optional: Obsidian publish or similar for graph visualization

## Related Ideas

- [ ] Propaganda as resource production
- [ ] "Consciousness" stat influenced by which wiki player reads
- [ ] Historical wiki showing how narratives shifted over time
- [ ] "Leaked documents" mechanic - raw Ledger data bypassing templates
