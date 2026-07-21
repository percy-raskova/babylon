Projection Registry (Constitution II.11)
========================================

.. note::

   Stub — the full registry lands with the Program 24 P1 keel (work order
   WO-2). This document is the constitutionally mandated spec for II.11:
   subsystem boundary interface contracts (views, RPC, events) and the
   table-ownership registry. Until WO-2 fills it, the normative content is
   the II.11 clause itself (``CONSTITUTION.md``) and the declared-view
   facade precedent in ``babylon.persistence.postgres_aggregation``.

Scope
-----

Constitution II.11 requires that each subsystem own its persistence tables
and that every cross-subsystem read go through a declared interface: an SQL
view with an explicit contract, an RPC boundary, or an event stream. The
projection layer (``babylon.projection``, Program 24 "The Hoist") is the
consumer of those declared interfaces on behalf of every client.

This registry will enumerate, per declared view:

* the owning subsystem and the view name (e.g. ``v_county_value_aggregate``,
  ``v_hex_state_asof``),
* the frozen Pydantic view-model that hydrates its rows,
* the explicit ``ORDER BY`` that makes every projection deterministic
  (Constitution III.13), and
* the columns exposed to full-text search.
