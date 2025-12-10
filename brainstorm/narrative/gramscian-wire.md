# The Gramscian Wire - Narrative Delivery System

**Status:** Future Enhancement (Phase 5+)
**Created:** 2025-12-09
**Supersedes:** `brainstorm/gramscian-wiki-engine.md` (original concept)

## The Pivot

**Original Concept:** A standalone wiki engine where factional control determined content.

**New Concept:** The wiki IS the game's primary narrative delivery mechanism - like Victoria's newspaper announcements, but with Gramscian hegemony mechanics built in.

**Key Insight:** You're not passively reading newspapers. In the Insurgent Operator framing, you're *intercepting information streams*. The news is contested terrain.

---

## Theoretical Foundation: Gramsci's Hegemony

Antonio Gramsci's concept of **cultural hegemony**: The ruling class maintains power not just through coercion (police, military) but through **consent** - by making their worldview seem like "common sense."

Media is a key instrument of hegemony:
- The bourgeois press frames events to **naturalize** capitalism
- Revolutionary press provides **counter-hegemonic** narratives
- The **same event** is described completely differently depending on class perspective

**This is the whole point of materialist analysis** - cutting through the mystification to see the material interests behind the narrative.

---

## Core Concept: "The Wire"

**Name:** "The Wire" - a play on:
- News wire services (AP, Reuters)
- Wiretapping / signal interception (insurgent aesthetic)

**Function:** Primary narrative delivery mechanism for game events.

**Structure:** Multiple channels representing different ideological perspectives. Same events, different framings.

---

## The Three Channels

### Channel 1: CORPORATE FEED (Hegemonic)

**Aesthetic:** Clean, professional, AP/Reuters style. Sanitized language.

**Voice:** "Neutral" (but actually bourgeois perspective naturalized)

**Examples:**
- Strike → "Labor Unrest Threatens Economic Recovery"
- Wage cut → "Companies Implement Cost Optimization Measures"
- Police violence → "Officers Restore Order Amid Disturbances"
- Imperial extraction → "Free Trade Agreement Benefits All Parties"

**Visual in UI:** Standard news ticker / article format

---

### Channel 2: LIBERATED SIGNAL (Counter-Hegemonic)

**Aesthetic:** Samizdat, underground press, pirate radio. Raw, urgent.

**Voice:** Revolutionary perspective, theoretical grounding.

**Examples:**
- Strike → "WORKERS RISE AGAINST EXPLOITATION"
- Wage cut → "Capitalists Extract Surplus Value from Labor"
- Police violence → "State Repression Intensifies - Solidarity Required"
- Imperial extraction → "Core Nations Continue Colonial Plunder"

**Visual in UI:** Glitchy, intercepted signal aesthetic. Purple glow.

---

### Channel 3: INTEL BRIEFING (Player Faction)

**Aesthetic:** Military/intelligence report format. Data-focused.

**Voice:** Your faction's analysis. Actionable intelligence.

**Examples:**
```
INCIDENT REPORT: Strike Action
LOCATION: Sector 7 Industrial
TIMESTAMP: Tick 42

EFFECTS:
  - Proletariat organization: +0.2
  - Bourgeoisie tension: +0.15
  - Local heat: +0.1

ANALYSIS:
Spontaneous action with revolutionary potential.
No vanguard presence detected.

RECOMMENDED ACTIONS:
  [ ] Deploy solidarity support
  [ ] Accelerate agitation
  [ ] Observe and document
```

**Visual in UI:** Terminal/dossier format. Data-forward.

---

## Concrete Example: One Event, Three Headlines

**EVENT:** Workers at a factory go on strike due to wage cuts.

### CORPORATE FEED:
```
LABOR UNREST THREATENS ECONOMIC RECOVERY

Radical elements disrupt production at key industrial facility.
Analysts warn of investment flight as productivity drops.
Government officials urge calm, promise swift resolution.

"We remain committed to the wellbeing of all stakeholders,"
said company spokesperson.
```

### LIBERATED SIGNAL:
```
>>> INTERCEPTED TRANSMISSION <<<

WORKERS RISE AGAINST EXPLOITATION!

Brave comrades at [REDACTED] refuse starvation wages!
The bosses thought they could squeeze us forever.
THEY WERE WRONG.

Solidarity actions spreading to adjacent sectors.
The dialectic intensifies.
THE CONTRADICTIONS CANNOT BE CONTAINED.

>>> END TRANSMISSION <<<
```

### INTEL BRIEFING:
```
╔═══════════════════════════════════════════════════════╗
║  INCIDENT: STRIKE_ACTION_042                          ║
║  SECTOR: Industrial-7 | TICK: 42                      ║
╠═══════════════════════════════════════════════════════╣
║  MATERIAL CONDITIONS:                                 ║
║    Wage cut: -15% (trigger)                           ║
║    Subsistence gap: CRITICAL                          ║
║                                                       ║
║  CONSCIOUSNESS SHIFT:                                 ║
║    Organization: 0.3 → 0.5 (+0.2)                     ║
║    Agitation: 0.1 → 0.25 (+0.15)                      ║
║                                                       ║
║  TACTICAL ASSESSMENT:                                 ║
║    Spontaneous action. No vanguard guidance.          ║
║    High potential, low coordination.                  ║
║    Window for intervention: 3 ticks                   ║
╚═══════════════════════════════════════════════════════╝
```

---

## Mechanical Integration

### 1. Hegemony Stat (New Faction Attribute)

```yaml
hegemony:
  description: "Cultural/narrative control over public discourse"
  range: [0.0, 1.0]
  effects:
    - "Determines which perspective is 'mainstream'"
    - "Affects consciousness drift of neutral populations"
    - "Higher hegemony = your framing shapes reality"
```

**Gameplay:** The faction with highest hegemony controls the "default" narrative. Other factions must work harder to spread counter-narratives.

### 2. Propaganda Actions

```yaml
propaganda_actions:
  underground_press:
    cost: "Resources + Organization"
    effect: "+Counter-hegemonic reach"
    risk: "Increases Heat (repression)"

  radio_broadcast:
    cost: "Resources + Territory (transmitter location)"
    effect: "Mass consciousness shift in range"
    risk: "Location can be traced"

  viral_campaign:
    cost: "Organization + Network connections"
    effect: "Rapid spread through solidarity edges"
    risk: "Can be co-opted/distorted"
```

### 3. AI Generation Pipeline

```
Event occurs (engine)
    ↓
NarrativeDirector.generate_perspectives(event)
    ↓
For each faction perspective:
    - Query faction-specific RAG corpus
    - Apply faction voice/framing
    - Generate article variant
    ↓
Store all variants in event_log
    ↓
UI displays based on player's channel selection
```

### 4. Reader Effect (Optional Advanced Mechanic)

What the player chooses to read affects their faction:

- Reading bourgeois press → Slight consciousness drift toward hegemonic position
- Reading revolutionary press → Reinforces counter-hegemonic consciousness
- Reading intel briefings → No drift, pure information

This is literally Gramsci - consciousness shaped by cultural consumption.

---

## Integration with Digital Grow Room UI

**The Wire** appears as a dedicated panel in the Monitor Station:

```
┌─────────────────────────────────────────────────────────────┐
│  [CORPORATE] [LIBERATED] [INTEL]                            │
├─────────────────────────────────────────────────────────────┤
│  >>> INTERCEPTED TRANSMISSION <<<                           │
│                                                             │
│  WORKERS RISE AGAINST EXPLOITATION!                         │
│                                                             │
│  Brave comrades at [REDACTED] refuse starvation wages!      │
│  The bosses thought they could squeeze us forever.          │
│  THEY WERE WRONG.                                           │
│                                                             │
│  [SIGNAL STRENGTH: ████████░░ 80%]                         │
│  [SOURCE: Underground Network Node 7]                       │
└─────────────────────────────────────────────────────────────┘
```

**Visual Cues:**
- **Corporate Feed:** Clean, white text on dark. "Professional."
- **Liberated Signal:** Glitchy, purple glow, occasional static
- **Intel Briefing:** Green terminal text, structured data

---

## Implementation Phases

### Phase 1: Single Perspective (Current)
- NarrativeDirector generates one description per event
- No hegemony mechanics
- Basic event log display

### Phase 2: Dual Perspective
- Generate Bourgeois + Revolutionary versions
- Tab-based channel switching in UI
- AI uses different prompts/RAG sources per perspective

### Phase 3: Full Implementation
- N-faction perspectives
- Hegemony stat affects which is "mainstream"
- Propaganda actions available
- Reader effect optional mechanic

---

## Why This Is Better Than Original Wiki Concept

| Aspect | Original Wiki | The Wire |
|--------|---------------|----------|
| Integration | Standalone feature | Core narrative system |
| Dynamic | Static until edited | Updates every tick |
| Diegetic | Meta-game | In-world (intercepted signals) |
| Mechanical | Display only | Affects hegemony/consciousness |
| Reuse | New system | Extends NarrativeDirector |
| Educational | Passive reading | Active ideology demonstration |

---

## Related Documents

- `brainstorm/ui/digital-grow-room.md` - UI aesthetic
- `brainstorm/gramscian-wiki-engine.md` - Original concept (superseded)
- `ai-docs/decisions.yaml:PDR002_wiki_implementation` - Pending decision
- `src/babylon/ai/director.py` - NarrativeDirector (to extend)

---

*"The ruling ideas of each age have ever been the ideas of its ruling class." - Marx & Engels, Communist Manifesto*

*"The Wire shows you the ideas. Your job is to cut through them."*
