# Database Schema Design for Babylon RPG

This document describes the comprehensive database schema designed for "The Fall of Babylon" - a Marxist text-based RPG that simulates complex social, political, and economic systems.

## Overview

The database schema is designed to capture the complex interactions between economic base and political superstructure as described in historical materialist theory. The schema supports:

- Game session management and player tracking
- Economic system modeling based on Marxist theory
- Political system and policy implementation
- Entity relationship management
- Dialectical contradiction tracking
- Event system with triggers and effects
- Time-series data for historical analysis

## Core Architecture

### 1. Game Management Layer

**Games Table** - Central table managing game sessions
- Tracks game lifecycle (active, paused, completed)
- Stores game configuration and initial conditions
- Links to all other game-specific data

**Players Table** - Player information and statistics
- Links players to specific games
- Tracks player decisions and strategy preferences
- Records performance metrics (game score, decision effectiveness, resource management efficiency, dialectical understanding score, revolutionary success rate)

**GameStates Table** - Game state snapshots
- Enables save/load functionality
- Provides historical game state analysis
- Supports rollback capabilities

**PlayerDecisions Table** - Decision tracking and analysis
- Records all player actions and their contexts
- Tracks decision outcomes and effectiveness
- Enables pattern analysis of player behavior

### 2. Economic System Layer

**Economies Table** - Core economic state management
Based on Marxist economic theory, tracking:
- Basic indicators (GDP, unemployment, inflation) - Surface-level economic measurements
- Marxist metrics (constant capital, variable capital, surplus value) - Underlying class relations and exploitation
- Derived ratios (organic composition of capital, rate of profit) - Calculated from Marxist base metrics
- Class relations and exploitation rates - Social dynamics derived from economic foundation
- Crisis indicators and phases - Dialectical contradictions manifesting in economic sphere

*Note: Basic indicators reflect the economic superstructure while Marxist metrics capture the underlying material base. The relationship follows historical materialism - changes in the material base (constant/variable capital, surplus value) drive changes in the superstructure (GDP, unemployment rates).*

**EconomicTimeSeries Table** - Historical economic data
- Tracks all economic metrics over time
- Enables trend analysis and pattern recognition
- Supports modeling of Marx's tendency of rate of profit to decline

**ClassRelations Table** - Social class dynamics
- Models different social classes (proletariat, bourgeoisie, etc.)
- Tracks class consciousness and political influence
- Records relationship to means of production

**ProductionSectors Table** - Sectoral economic analysis
- Models different production sectors
- Tracks sectoral capital composition
- Enables analysis of commodity circulation between sectors

### 3. Political System Layer

**PoliticalSystems Table** - Political superstructure state
- Government type and ruling parties
- Stability and legitimacy metrics
- Democratic institutions and civil liberties
- Revolutionary potential indicators

**Policies Table** - Policy implementation and effects
- Tracks all policies proposed and implemented
- Records policy effects on economic and social systems
- Measures policy effectiveness and unintended consequences

**Institutions Table** - Political and social institutions
- Models institutional framework
- Tracks institutional health and effectiveness
- Measures corruption and transparency

**ElectionEvents Table** - Democratic processes
- Records electoral events and outcomes
- Tracks participation and legitimacy impacts
- Links electoral results to policy changes

### 4. Entity System Layer

**Entities Table** - Universal game object representation
- Flexible entity system for all game objects
- Supports various entity types (organizations, resources, etc.)
- Tracks entity lifecycle and relationships

**EntityAttributes Table** - Structured attribute storage
- Detailed attribute tracking with type safety
- Supports numeric, string, and JSON attributes
- Enables efficient querying of entity properties

**EntityAttributeHistory Table** - Attribute change tracking
- Complete audit trail of attribute changes
- Supports analysis of entity evolution
- Enables rollback and debugging

**EntityRelationships Table** - Inter-entity relationships
- Models complex webs of entity interactions
- Supports various relationship types (owns, controls, influences, etc.)
- Tracks relationship strength and evolution

**EntityEvents Table** - Entity-event linkage
- Many-to-many relationship between entities and events
- Tracks entity roles in events
- Records event impacts on entities

### 5. Contradiction System Layer

**Contradictions Table** - Dialectical contradictions
Based on Marxist dialectical materialism:
- Models contradictions as drivers of systemic change
- Tracks intensity, state, and transformation potential
- Supports antagonistic vs. non-antagonistic contradictions
- Links to affected entities and systems

**ContradictionHistory Table** - Contradiction evolution
- Tracks how contradictions develop over time
- Records intensity changes and state transitions
- Links changes to triggering events

**ContradictionEffects Table** - Contradiction impacts
- Models how contradictions affect the system
- Supports targeted and systemic effects
- Tracks effect duration and conditions

**ContradictionNetworks Table** - Inter-contradiction relationships
- Models how contradictions interact
- Supports amplification, suppression, and generation relationships
- Enables analysis of complex dialectical networks

**ContradictionResolutions Table** - Resolution attempts and outcomes
- Tracks attempts to resolve contradictions
- Records success levels and unintended consequences
- Enables learning from resolution patterns

### 6. Event System Layer

**Events Table** - Game events and occurrences
- Stores all game events with their triggers and effects
- Supports various event types (economic, political, social, etc.)
- Tracks event lifecycle and impacts

**Existing Models Integration**
- **LogEntry Table** - System logging and debugging
- **Metric Table** - Performance metrics and monitoring

## Key Design Principles

### 1. Marxist Theory Integration
The schema directly models concepts from Marx's Capital:
- Organic composition of capital (constant/variable capital ratio)
- Rate of profit and tendency to decline
- Surplus value extraction and exploitation rates
- Dialectical contradictions as change drivers
- Base-superstructure relationships

### 2. Historical Materialism Support
- Time-series tables track systemic changes over time
- Contradiction evolution models dialectical development
- Policy effects demonstrate superstructure influence on base
- Class relations track social development

### 3. Flexible Entity System
- Universal entity model supports diverse game objects
- JSON attributes provide flexibility while structured tables ensure performance
- Relationship tracking enables complex systemic modeling
- Event linkage supports cause-and-effect analysis

### 4. Performance Optimization
- Strategic indexing on frequently queried columns
- Separate time-series tables for historical data
- JSON storage for flexible attributes with structured queries
- Foreign key relationships maintain data integrity

### 5. Extensibility
- Enum types allow easy addition of new categories
- JSON fields provide flexibility for future features
- Modular design supports independent system development
- Clear separation of concerns enables parallel development

## Relationships and Dependencies

### Primary Relationships
- Games → Players (One-to-Many)
- Games → Economies → EconomicTimeSeries (One-to-Many → One-to-Many)
- Games → PoliticalSystems → Policies (One-to-Many → One-to-Many)
- Games → Entities → EntityAttributes (One-to-Many → One-to-Many)
- Games → Contradictions → ContradictionHistory (One-to-Many → One-to-Many)
- Events ↔ Entities (Many-to-Many via EntityEvents)

### Cross-System Relationships
- Contradictions can affect multiple systems (economic, political, social)
- Events can trigger changes in multiple systems
- Entities can participate in economic, political, and social systems
- Policies can have effects across all systems

## Data Integrity and Constraints

### Foreign Key Constraints
- All game-related data links to Games table
- Proper cascading deletes for dependent data
- Referential integrity maintained across all relationships

### Unique Constraints
- Prevent duplicate entity attributes
- Ensure unique entity relationships
- Maintain data consistency

### Indexes
- Strategic indexing on game_id, turn_number, entity types
- Time-series optimizations for historical queries
- Relationship lookup optimizations

## Usage Examples

### Creating a New Game
```python
game = Game(name="Test Revolution", scenario="industrial_capitalism")
economy = Economy(game_id=game.id, gdp=1000.0, constant_capital=600.0, variable_capital=400.0)
economy.calculate_derived_metrics()  # Calculates rate of profit, etc.
```

### Tracking Economic Development
```python
# Record economic metrics over time
for turn in range(100):
    timeseries = EconomicTimeSeries(
        economy_id=economy.id,
        turn_number=turn,
        metric_name="rate_of_profit", 
        metric_value=economy.rate_of_profit
    )
```

### Modeling Contradictions
```python
contradiction = Contradiction(
    game_id=game.id,
    name="Capital vs Labor",
    contradiction_type=ContradictionType.ECONOMIC,
    antagonism=ContradictionAntagonism.ANTAGONISTIC,
    intensity=ContradictionIntensity.HIGH
)
```

## Migration and Maintenance

The schema includes utilities for:
- Fresh database initialization
- Schema validation and compatibility checking
- Table creation and migration
- Data integrity verification

## Future Extensions

The schema is designed to support future additions:
- Additional economic sectors and models
- Complex political coalition modeling  
- Social movement and ideology tracking
- International relations and trade
- Environmental factors and sustainability
- Cultural and ideological superstructure elements

This comprehensive schema provides a solid foundation for modeling the complex social, economic, and political dynamics envisioned in "The Fall of Babylon" RPG.