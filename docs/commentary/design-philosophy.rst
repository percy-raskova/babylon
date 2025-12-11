Design Philosophy
=================

This document captures the architectural principles, coding standards, and
design decisions that shape the Babylon codebase. It serves as both
historical record and ongoing guidance.

.. epigraph::

   Graph + Math = History

   -- Babylon Development Mantra

The Core Insight
----------------

Babylon encodes a specific thesis: **class struggle is not random events,
but deterministic output of material conditions**. Imperial Rent, Unequal
Exchange, and Atomization create a compact topological phase space where
history unfolds according to discoverable laws.

This isn't abstraction—it's code. Every mechanic has a formula. Every
formula has a theoretical justification. Every justification traces to
historical events.

Architecture: The Embedded Trinity
----------------------------------

The system runs locally without external servers, organized into three
pillars that never mix their concerns:

**The Ledger (SQLite/Pydantic)**
   Stores rigid, material state—economics, resources, turn history.
   The Ledger is **truth**. It doesn't interpret; it records.

**The Topology (NetworkX)**
   Stores fluid, relational state—class solidarity, tension, supply chains.
   The Topology is **structure**. It enables "Atomization" and "Hub Node"
   analysis through graph algorithms.

**The Archive (ChromaDB/Ollama)**
   Stores semantic history for AI narrative generation via RAG.
   The Archive is **context**. It informs but never controls.

.. note::

   This separation is non-negotiable. The Ledger never asks the Topology
   what to record. The Topology never queries the Archive for structure.
   The Archive never writes to the Ledger.

AI as Observer
--------------

The AI system acts as an **observer**, generating narrative from state
changes rather than controlling game mechanics.

This is a deliberate architectural choice:

1. **Determinism** — The simulation produces identical outcomes given
   identical inputs. AI non-determinism would break reproducibility.

2. **Theoretical integrity** — MLM-TW theory is encoded in formulas, not
   in LLM prompts. The AI interprets; it doesn't invent.

3. **Testability** — We can unit test every formula. We cannot unit test
   AI narrative quality with the same rigor.

.. admonition:: The Archive's Role

   The Archive (ChromaDB + RAG) provides historical and theoretical
   context to the AI narrator. When the simulation triggers a SURPLUS_EXTRACTION
   event, the AI retrieves relevant Marxist theory to frame its narrative.

   But the narrative is *commentary*, not *causation*. The simulation
   would produce identical mechanical outcomes with or without AI.

Data-Driven Design: The Paradox Pattern
---------------------------------------

Game logic should not be hardcoded. It should be defined in data files
and loaded into Pydantic models at runtime.

**Bad:**

.. code-block:: python

   if class_name == "proletariat":
       anger += 10

**Good:**

.. code-block:: python

   anger += entity.modifiers.get("repression_impact").calculate(state)

This pattern (borrowed from Paradox Interactive games like Crusader Kings)
provides:

- **Moddability** — Change game balance without touching Python
- **Transparency** — All mechanics visible in configuration
- **Testability** — Validate data schemas independently from code

Type Safety as Contract
-----------------------

Babylon enforces strict typing throughout:

**Constrained Types**

.. code-block:: python

   from babylon.models import Probability, Currency, Intensity

   def calculate_something(
       p: Probability,    # 0.0 to 1.0
       c: Currency,       # non-negative float
       i: Intensity,      # enum: LOW, MEDIUM, HIGH
   ) -> Probability:
       ...

These aren't just documentation—Pydantic validates at runtime. A function
that returns ``Probability(1.5)`` will raise an exception.

**Why This Matters**

- Bugs manifest at boundaries, not deep in calculation chains
- Error messages point to the source, not symptoms
- Reviewers can trust type signatures as contracts

Test-Driven Development
-----------------------

Every feature follows the TDD cycle:

1. **Red** — Write a failing test that captures the requirement
2. **Green** — Implement the minimum code to pass
3. **Refactor** — Clean up without changing behavior

This isn't aspirational—it's enforced. PRs without tests don't merge.
The test suite covers:

- **Unit tests** — Individual formula correctness
- **Integration tests** — System interactions
- **Theory validation** — Outcomes match MLM-TW predictions

.. code-block:: bash

   # Run the full test suite
   mise run test

   # Run fast formula tests only
   mise run test-fast

   # Run with coverage report
   mise run test-cov

State is Pure Data
------------------

A critical architectural principle:

.. admonition:: State/Engine Separation

   **State is pure data. Engine is pure transformation. They never mix.**

The ``WorldState`` object is a frozen snapshot. It has no methods that
modify itself. All changes flow through the engine:

.. code-block:: python

   # Good: Engine transforms state
   new_state = step(old_state, config, context, defines)

   # Bad: State modifies itself
   state.apply_rent_extraction()  # This method doesn't exist

This enables:

- **Time travel** — Any previous state can be restored
- **Parallelism** — Multiple simulations can run independently
- **Testing** — States are comparable with simple equality

Documentation Philosophy
------------------------

We follow Diataxis with discipline:

- **Tutorials** — Learning by doing
- **How-to guides** — Goal-oriented procedures
- **Concepts** — Understanding why
- **Reference** — Lookup specifications

Each document serves ONE purpose. "Super-documents" that mix purposes
get split.

**Demand-Driven Principle**

Documentation emerges from actual pain points, not anticipated needs.
Before writing documentation, ask:

   Who is currently blocked by the absence of this information?

Not "who might someday need this" — who needs it *now*.

**Accuracy over Comprehensiveness**

Five accurate documents beat fifty outdated ones. Incompleteness is
honesty. Inaccuracy is toxic.

Commit Standards
----------------

All commits use conventional commit format:

- ``feat:`` — New feature
- ``fix:`` — Bug fix
- ``docs:`` — Documentation only
- ``refactor:`` — Code change that neither fixes a bug nor adds a feature
- ``test:`` — Adding or correcting tests
- ``chore:`` — Build process or auxiliary tool changes

Commits are atomic—one logical change per commit. Large features are
broken into reviewable pieces.

See Also
--------

- :doc:`/concepts/architecture` - Technical architecture details
- :doc:`theoretical-foundations` - MLM-TW theory encoding
- ``CLAUDE.md`` - Full project context file
