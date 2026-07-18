"""Endgame epilogues — the six terminal texts of the hundred-year campaign.

Spec-116 FR-116-4.2 (Playability Spine): kills the ``"THE BUNKER FAILS"`` x4
duplicate by giving every :class:`~babylon.models.enums.events.GameOutcome`
(including the fixed-horizon ``UNRESOLVED``) its own headline, body, and
palette. Copy is **data** (spec-116 constraint: "copy lives in data, not
conditionals"): the bridge looks the recognized pattern up at render time,
the engine never imports this module, and the (flag-off) LLM narrator
eulogizes through its own separate channel — the engine adjudicates, this
module frames, the AI narrates.

Source material: the three crafted (structurally unreachable) Wire triptychs
in ``web/game/narrator.py`` (``revolutionary_victory`` /
``ecological_collapse`` / ``fascist_consolidation``) supplied the voice for
those outcomes; the ``red_ogv`` / ``fragmented_collapse`` / ``unresolved``
texts are original to this module (no prose existed anywhere for them).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class Epilogue(BaseModel):
    """One terminal outcome's end-screen copy.

    :ivar headline: The end screen's h1 (rendered in the outcome palette).
    :ivar body: Deterministic 2-4 sentence epilogue prose, distinct per outcome.
    :ivar palette: Which of the three end-screen palette families frames this
        outcome (``rupture`` bronze-gold / ``defeat`` laser-red /
        ``unresolved`` cold spire-cyan).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    headline: str
    body: str
    palette: Literal["rupture", "defeat", "unresolved"]


#: The six terminal texts, keyed by the literal lowercase ``GameOutcome.value``
#: strings — the same case ``_outcome_from_endgame_row`` returns and the frontend
#: compares, eliminating the old ``_OUTCOME_HEADLINES`` ``.upper()`` case split.
#: Keys are string literals (not ``GameOutcome.X.value``) so this leaf module honors
#: the web import boundary — only ``engine_bridge`` may import engine code
#: (``tests/unit/web/test_import_boundary.py``). Drift against the enum is caught by
#: ``tests/unit/web/test_epilogues.py::TestEpiloguesCoverage`` (a test may import the
#: enum), which pins these keys to ``{o.value for o in GameOutcome} - {IN_PROGRESS}``.
EPILOGUES: dict[str, Epilogue] = {
    "revolutionary_victory": Epilogue(
        headline="BABYLON FALLS",
        body=(
            "The regime change is real: not a transfer of management but the "
            "end of the manager. The imperial circuit is broken — the rent "
            "that bought the core's silence has stopped arriving, and no one "
            "is owed silence anymore. The people hold the line they spent a "
            "century building. What the wire called impossible was only ever "
            "unprofitable."
        ),
        palette="rupture",
    ),
    "ecological_collapse": Epilogue(
        headline="THE EARTH BETRAYED",
        body=(
            "The crisis was never a surprise; it was a business plan running "
            "to completion. Capital metabolized forest, watershed, and season "
            "into quarterly filings until the biosphere stopped extending "
            "credit. There is no bunker deep enough to secede from a dead "
            "metabolism. The earth was betrayed by capital, and the earth "
            "does not negotiate."
        ),
        palette="defeat",
    ),
    "fascist_consolidation": Epilogue(
        headline="ORDER IS RESTORED",
        body=(
            "That is what the wire calls it: order, restored. Wages fell, and "
            "the anger that could have become class war was routed into "
            "national costume — the oldest trick empire knows. The fash take "
            "hold of the state because the state was always shaped to receive "
            "them. We do not yield; the cadre goes under, and the work "
            "continues in the dark."
        ),
        palette="defeat",
    ),
    "red_ogv": Epilogue(
        headline="RED FLAGS OVER EMPIRE",
        body=(
            "A socialist government now administers an unbroken imperial "
            "circuit. Core wages still exceed core value; the difference "
            "still arrives from the periphery — collected, as before, only "
            "now in the people's name. The settler bargain was not "
            "repudiated, it was rebranded. When the periphery presents its "
            "ledger, it will not distinguish between the empire's managers."
        ),
        palette="defeat",
    ),
    "fragmented_collapse": Epilogue(
        headline="THE MAP SHATTERS",
        body=(
            "The center failed and nothing organized enough replaced it. "
            "Sovereignty splintered faster than solidarity could bind it — "
            "three flags, then five, each defending a shrinking perimeter of "
            "rent. Where no class rules, geography rules. Collapse is not "
            "liberation; it is the empire's debris, still falling on the "
            "same people it always fell on."
        ),
        palette="defeat",
    ),
    "unresolved": Epilogue(
        headline="THE STRUGGLE CONTINUES",
        body=(
            "One hundred years, and no verdict. The contradiction did not "
            "resolve; it deepened, changed terrain, and outlived every "
            "administration that claimed to manage it. History does not end "
            "because the observation window closes. The line holds where you "
            "built it; the rest belongs to the next century, and to whoever "
            "organizes it."
        ),
        palette="unresolved",
    ),
}
