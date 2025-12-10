# The Digital Grow Room - UI Aesthetic Specification

**Status:** Approved Design Direction (Phase 4)
**Created:** 2025-12-09

## The Pivot

Moving away from the "State Planner" (Cybersyn) aesthetic—which implies you *are* the government—to the **"Insurgent Operator"** aesthetic. You are the *virus* in the machine. You are inside the Imperial Core, stealing electricity to grow something illegal and dangerous.

This fits the "Third Worldism" theme perfectly: **you are the internal contradiction.**

---

## The Aesthetic: "Hydroponic Cyber-Insurgency"

**The Vibe:** High-tech but jury-rigged. Expensive GPUs cooling in a damp basement. Purple LED grow lights reflecting off CRT monitors. The hum of fans.

### Color Palette

| Name | Hex | Purpose |
|------|-----|---------|
| **Void** | `#050505` | The dark basement |
| **Grow Light** | `#9D00FF` | The "life" of the revolution/AI |
| **Data** | `#39FF14` | The raw output (terminal green) |
| **Heat/Danger** | `#FF3333` | Overheating/Rupture |

**Design Language:** "Blurple" (UV Grow Lights) and "Terminal Green"

### Typography

- **Code/Data:** JetBrains Mono
- **Headers/Glitch:** VCR OSD Mono

### Sound Design (Mental Model)

- Fan noise
- Hard drive clicks
- Low-frequency hum
- Occasional electrical crackle

---

## The UI Layout (NiceGUI)

The screen is not a "Dashboard"; it is a **"Monitor Station."**

### 1. Center Stage: The "Attack Surface" (Topology)

**Visual:** `ui.echart` configured as a **Network Topology Scanner** (like Maltego or Nmap).

**Style:**
- Dark background
- Nodes aren't clean circles; they are hex codes or icons (Server, Factory, Police Station)

**Animation:**
- **Exploitation:** Instead of "particles," show "packets" or "pings" draining from the Periphery to the Core
- **Tension:** The graph "glitches" or vibrates when tension is high
- **Fog of War:** Unexplored nodes are dim or "encrypted" (scrambled text)

### 2. The Sidebar: The "Root Shell" (Narrative)

**Visual:** A translucent terminal window floating over the map (`ui.card` with backdrop-filter).

**Behavior:**
```
> system_scan_complete: tension at 0.45
[AI_CORE]: Detecting pattern match in Sector 7...
[AI_CORE]: Analysis: The bourgeoisie is hoarding surplus value.
[AI_CORE]: Suggesting immediate rupture.
[!] ALERT: Repression level increasing in node 0x7F3A...
```

**Events:** "System Warnings" or "Intrusion Detection" alerts.

### 3. The Control Deck: "Environmental Controls" (Praxis)

**Metaphor:** You aren't "passing laws"; you are **tuning the environment** to maximize yield (Revolution).

**Widgets:**
- **"Agitation" (Consciousness):** A fan-speed slider. Turn it up to spread the "spores" (ideology), but it increases "Noise" (Repression risk).
- **"Fundraising" (Rent):** A voltage dial. Undervolt to stay hidden? Overvolt to gain resources fast (but risk a fire/raid)?
- **"The Big Red Button":** Label it **`EXECUTE_BATCH`** (Next Turn).

---

## Widget Metaphors

| Game Concept | Grow Room Metaphor | Visual Implementation |
|--------------|-------------------|----------------------|
| **Organization** | "Canopy Density" | A density heatmap. How thick is the network? |
| **Tension** | "GPU Temp" | A thermometer gauge. If it hits 90°C (1.0), system crashes (Revolution). |
| **Repression** | "External Heat" | A "Heat Signature" warning light. Is the DEA/FBI knocking? |
| **Resources** | "Power Draw" | An electricity meter. How much juice do you have left? |
| **The AI** | "The Gardener" | An avatar in the corner that "watches" stats and prints advice. |

---

## Implementation Strategy (Phase 4)

This aesthetic is actually **easier** to build in NiceGUI than the clean corporate look because "rough edges" look intentional.

### Step 1: Foundation
```python
ui.dark_mode().enable()
```

### Step 2: CSS Injection
Custom `style.css` to give everything that "glow" effect:
```css
.grow-glow {
    box-shadow: 0 0 10px #9D00FF;
}

.terminal-text {
    font-family: 'JetBrains Mono', monospace;
    color: #39FF14;
    text-shadow: 0 0 5px #39FF14;
}

.danger-pulse {
    animation: pulse 1s infinite;
    box-shadow: 0 0 20px #FF3333;
}
```

### Step 3: ASCII Art Boot Sequence
```
████████╗██╗  ██╗███████╗    ███████╗ █████╗ ██╗     ██╗
╚══██╔══╝██║  ██║██╔════╝    ██╔════╝██╔══██╗██║     ██║
   ██║   ███████║█████╗      █████╗  ███████║██║     ██║
   ██║   ██╔══██║██╔══╝      ██╔══╝  ██╔══██║██║     ██║
   ██║   ██║  ██║███████╗    ██║     ██║  ██║███████╗███████╗
   ╚═╝   ╚═╝  ╚═╝╚══════╝    ╚═╝     ╚═╝  ╚═╝╚══════╝╚══════╝

> INITIALIZING BABYLON CORE v0.1.0
> LOADING MARXIST-LENINIST DIALECTICAL ENGINE...
> CONNECTING TO PERIPHERY NODES...
> [OK] READY FOR PRAXIS
```

---

## Thematic Alignment

**Why This Works:**

1. **Third Worldist Perspective:** You are not the state. You are the virus. The contradiction. Growing revolution in the basement of empire.

2. **Material Grounding:** The metaphors (electricity, heat, fans) are *material*. They ground abstract concepts (organization, tension) in physical reality.

3. **Paranoia as Mechanic:** The "heat signature" / "external heat" metaphor naturally creates tension. You're always watching for the knock on the door.

4. **Tech Aesthetic Without Tech-Utopianism:** This isn't clean Silicon Valley design. It's jury-rigged, desperate, dangerous. Technology as tool of liberation, not domination.

---

## Widget Specifications

### Time: The Doomsday Clock

**Concept:** A "Doomsday Clock" showing the Tick count.

**Visual:** Classic Bulletin of Atomic Scientists aesthetic - midnight = system collapse/revolution.
- Clock face with hour hand approaching midnight
- Each tick advances the hand
- Glowing red as it approaches 12:00
- Optional: Minutes to midnight display (based on aggregate tension)

**Implementation:**
```python
ui.circular_progress(value=tick/max_ticks, show_value=True)
# Or custom SVG clock face with ui.html
```

**Thematic Fit:** The revolution is inevitable. The only question is when.

---

### Imperial Rent: The Sankey Diagram

**Concept:** A Sankey Diagram overlay showing wealth flow from Periphery → Core.

**Visual:**
- Thick flowing lines representing value extraction
- Color gradient: Periphery nodes (green/life) → Core nodes (purple/extraction)
- Line thickness = magnitude of imperial rent (Φ)
- Animated flow particles showing direction

**Implementation:**
```python
# ECharts Sankey
ui.echart({
    'series': [{
        'type': 'sankey',
        'data': nodes,
        'links': flows,
        'lineStyle': {'color': 'gradient'}
    }]
})
```

**Thematic Fit:** Make the invisible visible. Show where the wealth *actually* goes.

---

### Contradiction: The Tension Gauge

**Concept:** An analog needle-style "Tension Gauge" with glass-crack effect at 1.0.

**Visual:**
- Retro analog gauge (steampunk industrial aesthetic)
- Needle sweeps from 0.0 (green) → 0.5 (yellow) → 1.0 (red)
- Red Zone clearly marked
- **At 1.0:** Glass cracks overlay (CSS animation), sparks, rupture event

**Implementation:**
```python
ui.echart({
    'series': [{
        'type': 'gauge',
        'min': 0, 'max': 1,
        'axisLine': {'lineStyle': {'color': [[0.5, '#39FF14'], [0.8, '#FFFF00'], [1, '#FF3333']]}},
        'pointer': {'itemStyle': {'color': '#9D00FF'}},
        'data': [{'value': tension}]
    }]
})
```

**Glass Crack CSS:**
```css
.glass-crack {
    background-image: url('crack-overlay.png');
    animation: shake 0.5s infinite;
}
```

**Thematic Fit:** Pressure builds. The system can only take so much before it shatters.

---

### Consciousness: The Political Compass

**Concept:** A scatter plot showing population drift from "Reactionary" to "Revolutionary".

**Visual:**
- X-axis: Class Consciousness (0 = false consciousness, 1 = class conscious)
- Y-axis: National Identity vs Internationalism
- Each dot = a population segment or social class
- Dots drift over time based on agitation, solidarity, material conditions
- Color by faction affiliation

**Quadrants:**
```
                 Internationalist
                       │
    Revolutionary ─────┼───── Reactionary
    Proletarian        │      Nationalist
                       │
                 Chauvinist
```

**Implementation:**
```python
ui.echart({
    'xAxis': {'name': 'Class Consciousness', 'min': 0, 'max': 1},
    'yAxis': {'name': 'Internationalism', 'min': -1, 'max': 1},
    'series': [{
        'type': 'scatter',
        'data': [[class_consciousness, internationalism, population_size]],
        'symbolSize': lambda x: x[2] / 1000  # Size by population
    }]
})
```

**Thematic Fit:** Watch the masses awaken. Or watch them fall to fascism.

---

### Inspection: The Dossier Modal

**Concept:** Click any node → Opens a "Dossier" modal showing raw Ledger data.

**Visual:**
- Manila folder aesthetic (or digital file aesthetic matching grow room)
- Tabs: Overview | Raw Data | History | Relationships
- Shows Pydantic model fields in readable format
- JSON toggle for developers

**Content:**
```
╔══════════════════════════════════════════════════╗
║  DOSSIER: Proletariat [Node 0x7F3A]              ║
╠══════════════════════════════════════════════════╣
║  CLASS: SocialClass                              ║
║  ROLE: PROLETARIAT                               ║
║  ─────────────────────────────────────────────── ║
║  MATERIAL CONDITIONS:                            ║
║    wealth: 1200.00                               ║
║    wages: 800.00                                 ║
║    subsistence: 500.00                           ║
║  ─────────────────────────────────────────────── ║
║  CONSCIOUSNESS:                                  ║
║    ideology: -0.3 (Left-leaning)                 ║
║    organization: 0.45                            ║
║    agitation: 0.2                                ║
║  ─────────────────────────────────────────────── ║
║  SURVIVAL CALCULUS:                              ║
║    P(S|A): 0.72                                  ║
║    P(S|R): 0.28                                  ║
║    Status: Acquiescent (but watching)            ║
╚══════════════════════════════════════════════════╝
```

**Implementation:**
```python
with ui.dialog() as dossier:
    with ui.card().classes('w-96'):
        ui.label(f'DOSSIER: {node.name}').classes('text-xl')
        ui.separator()
        with ui.tabs() as tabs:
            ui.tab('Overview')
            ui.tab('Raw JSON')
            ui.tab('History')
        with ui.tab_panels(tabs):
            # ... panel content
```

**Thematic Fit:** Intelligence gathering. Know your enemy. Know your comrades.

---

## Related Documents

- `brainstorm/mechanics/layer0_territory.md` - Territorial substrate (Heat mechanics)
- `ai-docs/decisions.yaml:PDR001_ui_framework` - UI framework decision pending
- Phase 4 roadmap (when defined)

---

*"The revolution will not be downloaded. It will be cultivated."*
