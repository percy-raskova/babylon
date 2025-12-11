AI Integration
==============

This document outlines the approach for using Large Language Models (LLMs)
as an intelligent game master for the Babylon simulation.

Overview
--------

The AI system acts as an **observer**, generating narrative from state
changes rather than controlling game mechanics. The simulation engine
produces deterministic outcomes; the AI provides interpretation and
narrative flavor.

Vector Database Integration
---------------------------

Basic Flow
~~~~~~~~~~

1. Present users with pre-generated options plus custom input ability
2. Convert user input into vector embeddings
3. Compare against stored vectors in database
4. Retrieve top N most relevant entries (typically 10)
5. Use these entries to build context for the AI

Vector Database Contents
~~~~~~~~~~~~~~~~~~~~~~~~

- Previous actions and outcomes
- Entity descriptions and properties
- Historical events and consequences
- Contradiction patterns and resolutions

Prompting Guidelines
--------------------

Core Principles
~~~~~~~~~~~~~~~

1. Ground all responses in material conditions
2. Maintain internal consistency
3. Consider class relations and power dynamics
4. Provide structured, parseable responses
5. Include both mechanical effects and narrative description
6. Keep track of historical continuity
7. Allow for emergence of new contradictions

Basic Prompt Structure
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def create_base_prompt():
       return """You are the game master for a Marxist political simulation.
       Your role is to:
       - Analyze player actions through dialectical materialism
       - Generate realistic consequences based on material conditions
       - Maintain internal consistency with previous events
       - Escalate or de-escalate contradictions appropriately
       - Consider class interests and power relations in all outcomes"""

Context Hierarchy
~~~~~~~~~~~~~~~~~

Important elements to include in prompts:

**Material Conditions**
   - Economic conditions
   - Class relations
   - Political power distribution

**Active Contradictions**
   - Current intensity
   - Involved entities
   - Historical development

**Recent Events**
   - Outcomes
   - Affected parties
   - Changes to material conditions

**Player Status**
   - Position
   - Resources
   - Relationships

Response Format
~~~~~~~~~~~~~~~

Request structured responses for reliable parsing:

.. code-block:: text

   IMMEDIATE EFFECTS:
   - [Effect 1]
   - [Effect 2]

   CONTRADICTION CHANGES:
   - [Contradiction ID]: [Change in intensity] because [reasoning]

   NEW EVENTS:
   - [Event description]
   - Likelihood: [High/Medium/Low]
   - Affected entities: [List]

   NARRATIVE DESCRIPTION:
   [2-3 sentences describing outcomes in narrative form]

Implementation Examples
-----------------------

Processing Data for Context
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Rather than sending raw data to the AI, extract relevant information:

.. code-block:: python

   def extract_relevant_context(objects):
       context_elements = []
       for obj in objects:
           if isinstance(obj, Event):
               context = {
                   'type': 'event',
                   'name': obj.name,
                   'description': obj.description,
                   'effects': [e.description for e in obj.effects],
                   'escalation_level': obj.escalation_level
               }
           elif isinstance(obj, Contradiction):
               context = {
                   'type': 'contradiction',
                   'name': obj.name,
                   'description': obj.description,
                   'intensity': obj.intensity,
                   'involved_entities': [e.name for e in obj.entities]
               }
           context_elements.append(context)
       return context_elements

Specialized Prompts
~~~~~~~~~~~~~~~~~~~

**Economic Actions:**

.. code-block:: python

   def economic_action_prompt(action, state):
       return f"""
       The player has taken an economic action: {action}

       Current Economic Indicators:
       - Unemployment Rate: {state.unemployment}
       - Class Inequality Index: {state.inequality}
       - Industrial Capacity: {state.industry_capacity}

       How do the following groups respond:
       1. Working Class
       2. Capitalist Class
       3. State Apparatus
       """

**Political Actions:**

.. code-block:: python

   def political_action_prompt(action, state):
       return f"""
       The player has taken a political action: {action}

       Current Political Landscape:
       - Class Consciousness Level: {state.class_consciousness}
       - State Legitimacy: {state.legitimacy}
       - Opposition Strength: {state.opposition_power}

       Analyze effects on:
       1. Balance of class forces
       2. State authority
       3. Popular support
       4. Potential for resistance
       """

API Integration
---------------

Claude API Usage
~~~~~~~~~~~~~~~~

Using Claude's 200k token context window effectively:

.. code-block:: python

   def generate_game_response(prompt):
       response = anthropic.messages.create(
           model="claude-3-5-sonnet-20241022",
           max_tokens=1024,
           temperature=0.7,
           system="You are an AI game master for a Marxist political simulation.",
           messages=[{"role": "user", "content": prompt}]
       )
       return parse_response(response.content)

Response Parsing
~~~~~~~~~~~~~~~~

.. code-block:: python

   def parse_response(response):
       game_effects = {
           'immediate_effects': [],
           'new_contradictions': [],
           'contradiction_changes': [],
           'triggered_events': [],
           'entity_effects': []
       }
       # Parse structured response sections
       return game_effects

Best Practices
--------------

**Consistency Management**
   - Track all significant decisions and outcomes
   - Maintain a history of events and their consequences
   - Ensure new developments follow logically from established patterns

**Context Building**
   - Only include relevant information
   - Structure context hierarchically
   - Prioritize recent and directly related events

**Response Parsing**
   - Use structured formats for easy parsing
   - Include both mechanical and narrative elements
   - Validate responses against game rules and logic

**Error Handling**
   - Have fallback options for unclear responses
   - Validate AI outputs against game constraints
   - Maintain game stability if AI service is unavailable

Context Window Management
-------------------------

The system implements a robust Context Window Management component:

**ContextWindowManager**
   - Tracks token usage across all content
   - Prioritizes content based on importance scores
   - Automatically optimizes context when reaching 75% capacity
   - Integrates with metrics collection for performance monitoring

**Content Prioritization**
   - Uses hybrid prioritization strategy (configurable)
   - Considers content importance, recency, and access frequency
   - Maintains priority queue for efficient content management
   - Preserves most relevant content when optimization is needed

**Integration**
   - Works with MetricsCollector to track token usage
   - Configurable through ContextWindowConfig

See :doc:`context-window` for detailed documentation.

Future Improvements
-------------------

**Enhanced Context Selection**
   - Improve vector similarity matching
   - Develop better context relevance scoring
   - Enhance context window management with more sophisticated algorithms

**Response Quality**
   - Fine-tune prompts based on response quality
   - Develop better parsing for complex responses
   - Implement validation for logical consistency

**Performance Optimization**
   - Cache common responses
   - Optimize vector searches
   - Reduce API calls when possible

See Also
--------

- :doc:`context-window` - Context window management
- :doc:`object-tracking` - Object tracking and RAG optimization
- :doc:`/reference/configuration` - Configuration system
- :doc:`architecture` - System architecture
