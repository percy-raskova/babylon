"""The aggregation sentinel — intensive quantities do not average.

An **extensive** quantity (wealth, population, hours) sums across a region; an
**intensive** one (a rate, ratio, share, balance, index) does not. The aggregate
profit rate is ``Σs / Σ(c+v)``, never ``mean(rᵢ)`` — and the difference is not
cosmetic: the unweighted form gives a four-hundred-person county the same say in
a national threshold as Wayne County, so a national serviceability line moves for
reasons no material relation supports.

This sensor finds the unweighted form statically, by shape: a division whose
numerator accumulates and whose denominator merely counts, inside a function
whose name or accumulator names an intensive. Sites that are legitimately
equal-weighted declare an exemption WITH A REASON in
:mod:`babylon.sentinels.aggregation.registry`.

Advisory and local/on-demand per the standing owner ruling:
``poetry run python tools/sentinel_check.py aggregation``.

Layer 0.5: imports nothing above :mod:`babylon.models`.
"""
