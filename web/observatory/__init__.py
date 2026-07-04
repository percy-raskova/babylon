"""Observatory — read-only developer dashboard over the simulation database.

Spec-096 (Program 09, Lane O). This Django app exposes read-only endpoints
under ``/api/observatory/`` that query the headless simulation runner's
Postgres (the ``sim`` database alias) through its declared view interfaces.

The app owns **no tables** and declares **no models**: it is a strict observer
(Constitution II.11 — cross-subsystem reads go through declared interfaces).
"""
