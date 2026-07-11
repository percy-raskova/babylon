"""The domain — the game's subject matter (Program 14 re-layering).

Material-base packages between models/formulas and the engine:
``economics`` (value, rent, tensors), ``dialectics`` (oppositions,
contradictions), ``organizations``, ``institution``, ``bifurcation``
(crisis routing), and ``geography`` (terrain, H3/R8 mesh, capacity —
the immutable spatial substrate's implementation, formerly
``infrastructure``). Domain packages may import kernel/models/formulas/
topology; the engine imports them; they never import the engine back
(enforced by import-linter).
"""
