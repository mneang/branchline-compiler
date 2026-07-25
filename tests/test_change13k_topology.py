"""Guardrails for fault isolation and graph semantics."""

from pathlib import Path

from branchline.presentation.focused_proof import (
    build_focused_proof,
)


def test_safety_inventory_remains_complete() -> None:
    proof = build_focused_proof(
        scenario_id="scenario_c"
    )

    assert [
        node["label"]
        for node in proof["nodes"]
    ] == [
        "preview.ending_b",
        "Ending B",
        "Ending A",
    ]


def test_failure_chain_stops_at_ending_b() -> None:
    proof = build_focused_proof(
        scenario_id="scenario_c"
    )

    assert [
        node["label"]
        for node in proof["causal_nodes"]
    ] == [
        "preview.ending_b",
        "Ending B",
    ]


def test_ending_a_is_independent() -> None:
    proof = build_focused_proof(
        scenario_id="scenario_c"
    )

    assert [
        node["label"]
        for node in proof["independent_nodes"]
    ] == [
        "Ending A",
    ]

    assert (
        "not dependent"
        in proof[
            "independent_nodes"
        ][0]["detail"]
    )


def test_ui_uses_split_topology() -> None:
    app = Path("app.py").read_text()

    assert "causal_nodes = focused_proof.get(" in app
    assert "independent_nodes = focused_proof.get(" in app
    assert "proof-topology split" in app
    assert "INDEPENDENT ROUTE" in app


def test_graph_key_separates_shape_and_state() -> None:
    source = Path(
        "src/branchline/presentation/"
        "judge_view.py"
    ).read_text()

    assert "SHAPE = ENTITY TYPE" in source
    assert "COLOR = CURRENT STATE" in source
    assert '"Source": "rect"' in source
    assert '"Media asset": "roundRect"' in source
    assert '"Story path": "circle"' in source
