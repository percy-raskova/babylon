# Your First Game Session

This tutorial walks you through a complete game session in Babylon, teaching you core gameplay mechanics through hands-on experience. You'll learn how contradictions drive the game world and how your decisions shape society's development.

## Prerequisites

- Complete the [Getting Started](getting-started.md) tutorial
- Have Babylon running on your system
- Basic familiarity with text-based interfaces

## What You'll Learn

- How contradictions emerge and evolve
- How to make meaningful political and economic decisions
- How to interpret game feedback and consequences
- How to manage resources and population stability

## Starting a New Game Session

### Step 1: Launch Babylon

```bash
cd babylon
python -m babylon
```

### Step 2: Choose Your Starting Scenario

When prompted, select a scenario:

```
Select starting scenario:
1. Industrial Revolution (Classic)
2. Modern Capitalism (Contemporary) 
3. Post-Apocalyptic (Experimental)
4. Custom Scenario

> 1
```

For this tutorial, choose **Industrial Revolution** (option 1).

### Step 3: Set Your Initial Parameters

```
=== INITIAL SETUP ===
Population size: [S]mall (5,000) / [M]edium (50,000) / [L]arge (500,000)
> M

Starting economic system: [F]eudal / [C]apitalist / [S]ocialist
> C

AI complexity: [B]asic / [I]ntermediate / [A]dvanced  
> I

Generating world... This may take a moment.
```

Choose **Medium** population and **Capitalist** system for this walkthrough.

## Understanding the Game World

### Step 4: Examine Your Starting Situation

```
> look
=== NEW BABYLON - YEAR 1850 ===

Central Factory District
The smokestacks of textile mills rise above cramped worker housing. 
Steam engines thunder day and night. The air hangs heavy with coal smoke.

Population: 50,000
- Factory Workers: 35,000 (70%)
- Capitalists: 2,000 (4%)  
- Artisans: 8,000 (16%)
- Farmers: 5,000 (10%)

ACTIVE CONTRADICTIONS:
⚡ Worker vs Capitalist (Intensity: Medium)
   Long hours and low wages create growing resentment

⚡ Traditional vs Industrial (Intensity: Low) 
   Artisans lose work to machines

RECENT EVENTS:
- New textile factory opened, hiring 500 workers
- Bread prices increased 15% due to poor harvest
```

The game presents contradictions as the core driving force. Notice how they have **intensity levels** that change over time.

### Step 5: Check Available Actions

```
> help actions

AVAILABLE ACTIONS:
Political Actions:
- pass_law [law_name]: Enact new legislation
- negotiate [faction]: Hold talks with a group
- suppress [action]: Use force to maintain order

Economic Actions:  
- invest [sector]: Allocate resources to industry
- regulate [industry]: Set rules for business
- tax [group] [rate]: Set taxation levels

Information:
- analyze [contradiction]: Deep dive into specific issue
- poll [group]: Survey population sentiment
- inspect [location]: Examine specific area
```

## Making Your First Decisions

### Step 6: Analyze a Contradiction

Let's understand the worker-capitalist contradiction better:

```
> analyze worker_vs_capitalist

=== CONTRADICTION ANALYSIS ===
Worker vs Capitalist Contradiction

ROOT CAUSES:
- Workers receive only 15% of value they produce
- 14-hour workdays with one 30-minute break  
- Unsafe factory conditions: 12 injuries per month
- No job security or benefits

MANIFESTATIONS:
- Whispered complaints during lunch breaks
- 3 minor work slowdowns last month
- Growing attendance at underground meetings

ESCALATION FACTORS:
- High: Economic downturn
- Medium: Industrial accidents  
- Low: Political suppression

POTENTIAL OUTCOMES:
- De-escalation: Better working conditions, higher wages
- Escalation: Strikes, labor organizing, potential revolution

Historical Precedent: Similar contradictions led to the Chartist movement in Britain (1838-1857)
```

This analysis helps you understand what's driving the conflict and what might happen.

### Step 7: Make an Economic Decision

Let's try to address worker concerns with better wages:

```
> invest labor_conditions

=== INVESTMENT DECISION ===
Investing in: Labor Conditions Improvement

Cost: 2,500 economic units (Current treasury: 10,000)
Time to implement: 6 months

Expected effects:
+ Reduce Worker vs Capitalist contradiction intensity
+ Improve worker productivity (+8%)  
+ Increase capitalist costs (-12% short-term profit)

Proceed? [y/n]
> y

IMPLEMENTING POLICY...

New regulations established:
- Maximum 12-hour workday (reduced from 14)
- Safety inspections required monthly
- Minimum wage increased 20%

Capitalist faction reaction: Strongly Negative (-15 influence)
Worker faction reaction: Positive (+8 influence)
```

Notice how your decision has **immediate consequences** that affect different groups differently.

### Step 8: Observe the Results

After making your decision, advance time to see the effects:

```
> advance_time 3_months

=== THREE MONTHS LATER ===

CONTRADICTION UPDATES:
⚡ Worker vs Capitalist (Intensity: Low ⬇️)
   Better conditions have eased worker anger, but capitalists resist further changes

⚡ Traditional vs Industrial (Intensity: Medium ⬆️)
   Displaced artisans organize against factory system

NEW EVENTS:
- Factory productivity increased 12% due to better worker morale
- Capitalists secretly plan to reverse wage increases
- Artisan guild petitions for protection from machine competition

ECONOMIC INDICATORS:
- GDP: +3.2% (productivity gains)
- Wages: +20% (policy effect)
- Profits: -8% (increased costs)
- Unemployment: +2% (artisan displacement)
```

Your decision successfully reduced one contradiction but may have intensified another!

## Advanced Gameplay Concepts

### Step 9: Handle a Crisis

Crises test your understanding of the game mechanics:

```
> advance_time 6_months

=== CRISIS EVENT ===
🚨 ECONOMIC DOWNTURN 🚨

A financial panic has struck! Banks are failing and credit is tight.

- Factory orders down 40%
- 3,000 workers face unemployment  
- Capitalists demand government bailouts
- Workers fear starvation

This crisis could escalate existing contradictions rapidly!

URGENT ACTIONS NEEDED:
Choose your response (you may select multiple):

1. bail_out_banks: Protect capital, maintain credit
2. employ_unemployed: Government work programs  
3. increase_welfare: Emergency food assistance
4. do_nothing: Let market forces resolve crisis

> 2,3
```

Combining multiple actions shows sophisticated decision-making.

```
IMPLEMENTING CRISIS RESPONSE...

Government Employment Program: 2,000 jobs created (road building, public works)
Emergency Welfare: Food distribution centers established

IMMEDIATE RESULTS:
- Worker anger contained (+5 stability)
- Government debt increased 40%
- Capitalists frustrated with "socialist" policies (-8 influence)
- New contradiction emerging: Fiscal vs Social spending

6 months later...
The crisis passes, but your debt-financed response creates new tensions about government spending.
```

### Step 10: Plan Long-term Strategy

```
> status

=== CURRENT SITUATION ===
Year: 1851 (18 months elapsed)
Population: 52,000 (+4% growth)

CONTRADICTION NETWORK:
⚡ Worker vs Capitalist (Low)
⚡ Traditional vs Industrial (High) ← URGENT  
⚡ Fiscal vs Social (Medium) ← NEW
⚡ Urban vs Rural (Low)

Your decisions have created a web of interconnected contradictions. 
Consider: How do you balance competing demands while preventing revolution?

LONG-TERM STRATEGIC OPTIONS:
- democratic_reform: Give workers political voice
- education_system: Help displaced artisans adapt  
- imperial_expansion: Find new markets to ease internal pressure
- revolution: Allow system to collapse and rebuild
```

## Session Wrap-up

### Step 11: Save Your Progress

```
> save babylon_tutorial_session

Game saved successfully!
Session duration: 47 minutes
Decisions made: 8
Contradictions resolved: 1
New contradictions emerged: 2
Population change: +4%

Would you like a session summary? [y/n]
> y

=== SESSION SUMMARY ===
You successfully navigated early industrialization challenges by:

SUCCESSES:
✅ Prevented worker revolution through labor reforms
✅ Managed economic crisis with public employment
✅ Maintained overall social stability

CHALLENGES CREATED:
⚠️  Artisan displacement now critical issue
⚠️  Government debt limits future options  
⚠️  Capitalist opposition may organize resistance

LESSONS LEARNED:
- Every decision has trade-offs and consequences
- Contradictions are interconnected - solving one may create others
- Crisis response reveals your governing philosophy
- Long-term planning is essential for sustainable society

NEXT SESSION RECOMMENDATIONS:
Consider addressing artisan displacement before it escalates.
Explore education or economic diversification strategies.
```

## What You've Learned

Through this session, you've experienced:

✅ **Contradiction Dynamics**: How tensions drive historical change
✅ **Decision Consequences**: Every choice has trade-offs  
✅ **Crisis Management**: How emergencies test your strategies
✅ **System Thinking**: Understanding interconnected social forces
✅ **Historical Materialism**: How economic base shapes social development

## Next Steps

Now that you understand basic gameplay:

- **Experiment with different strategies**: Try the [Advanced Strategies](../how-to/advanced-strategies.md) guide
- **Learn about specific mechanics**: Check the [Game Mechanics Reference](../reference/mechanics/)
- **Understand the theory**: Read about [Dialectical Materialism in Gaming](../explanation/dialectical-materialism.md)
- **Join the community**: Share your strategies and learn from other players

## Quick Reference

**Core Commands:**
- `look` - Examine current situation
- `analyze [contradiction]` - Deep dive into tensions  
- `invest [area]` - Allocate resources
- `advance_time [period]` - Progress the simulation
- `status` - Overall situation summary
- `save [name]` - Preserve your progress

---

**Ready for more complex challenges?** Try starting a new game with different parameters or explore the [Scenario Guide](../how-to/custom-scenarios.md).