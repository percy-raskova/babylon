AI Prompting Reference
======================

Prompt templates, response formats, and API usage patterns for the Babylon
AI game master system. For conceptual explanation, see
:doc:`/concepts/ai-integration`.

Base Prompt Template
--------------------

System Prompt
~~~~~~~~~~~~~

.. code-block:: python

   SYSTEM_PROMPT = """You are the game master for a Marxist political simulation.
   Your role is to:
   - Analyze player actions through dialectical materialism
   - Generate realistic consequences based on material conditions
   - Maintain internal consistency with previous events
   - Escalate or de-escalate contradictions appropriately
   - Consider class interests and power relations in all outcomes"""

Core Principles
~~~~~~~~~~~~~~~

1. Ground all responses in material conditions
2. Maintain internal consistency
3. Consider class relations and power dynamics
4. Provide structured, parseable responses
5. Include both mechanical effects and narrative description
6. Keep track of historical continuity
7. Allow for emergence of new contradictions

Context Hierarchy
-----------------

Include context elements in this priority order:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Category
     - Elements
   * - Material Conditions
     - Economic conditions, class relations, political power distribution
   * - Active Contradictions
     - Current intensity, involved entities, historical development
   * - Recent Events
     - Outcomes, affected parties, changes to material conditions
   * - Player Status
     - Position, resources, relationships

Response Format
---------------

Standard Response Structure
~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

Parsed Response Structure
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   class GameEffects:
       immediate_effects: list[str]
       new_contradictions: list[dict]
       contradiction_changes: list[dict]
       triggered_events: list[dict]
       entity_effects: list[dict]

Specialized Prompts
-------------------

Economic Action Prompt
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def economic_action_prompt(action: str, state: GameState) -> str:
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

Political Action Prompt
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def political_action_prompt(action: str, state: GameState) -> str:
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

Context Extraction
------------------

Data Processing
~~~~~~~~~~~~~~~

Extract relevant context from game objects:

.. code-block:: python

   def extract_relevant_context(objects: list) -> list[dict]:
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

API Integration
---------------

Claude API Usage
~~~~~~~~~~~~~~~~

.. code-block:: python

   import anthropic

   def generate_game_response(prompt: str) -> GameEffects:
       client = anthropic.Anthropic()
       response = client.messages.create(
           model="claude-3-5-sonnet-20241022",
           max_tokens=1024,
           temperature=0.7,
           system=SYSTEM_PROMPT,
           messages=[{"role": "user", "content": prompt}]
       )
       return parse_response(response.content[0].text)

API Parameters
~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Parameter
     - Recommended
     - Rationale
   * - ``model``
     - ``claude-3-5-sonnet-*``
     - Balance of capability and cost
   * - ``max_tokens``
     - 1024
     - Sufficient for structured responses
   * - ``temperature``
     - 0.7
     - Balance creativity with consistency
   * - Context window
     - Up to 200k tokens
     - Use ContextWindowManager to optimize

Response Parsing
~~~~~~~~~~~~~~~~

.. code-block:: python

   def parse_response(response: str) -> GameEffects:
       game_effects = GameEffects(
           immediate_effects=[],
           new_contradictions=[],
           contradiction_changes=[],
           triggered_events=[],
           entity_effects=[]
       )
       # Parse structured response sections
       # Extract IMMEDIATE EFFECTS, CONTRADICTION CHANGES, etc.
       return game_effects

Vector Database Integration
---------------------------

Query Flow
~~~~~~~~~~

1. Convert user input to vector embedding
2. Query ChromaDB for top N similar entries
3. Build context from retrieved entries
4. Include in prompt alongside current state

Stored Content Types
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Content Type
     - Description
   * - Previous actions
     - Historical player decisions and outcomes
   * - Entity descriptions
     - Properties and relationships of game entities
   * - Historical events
     - Past events and their consequences
   * - Contradiction patterns
     - Common contradiction resolutions

Best Practices
--------------

Consistency Management
~~~~~~~~~~~~~~~~~~~~~~

- Track all significant decisions and outcomes
- Maintain a history of events and their consequences
- Ensure new developments follow logically from established patterns

Context Building
~~~~~~~~~~~~~~~~

- Only include relevant information
- Structure context hierarchically
- Prioritize recent and directly related events

Error Handling
~~~~~~~~~~~~~~

- Have fallback options for unclear responses
- Validate AI outputs against game constraints
- Maintain game stability if AI service is unavailable

See Also
--------

- :doc:`/concepts/ai-integration` - Conceptual explanation
- :doc:`/reference/context-window-api` - Context window management API
- :doc:`/reference/configuration` - Configuration system
- :doc:`/concepts/architecture` - System architecture
