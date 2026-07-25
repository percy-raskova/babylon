"""Behavioral contract for TopologyView declared-future absence (Task 5)."""

from babylon.tui.shell.views.topology_view import render_absence


def test_absent_node_kinds_render_as_declared_future_stub():
    out = render_absence("coalition")
    assert "coalition" in out
    assert "not yet" in out.lower() or "declared-future" in out.lower()
    # never fabricates a node id
    assert "node_" not in out
