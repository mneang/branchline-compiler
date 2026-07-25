"""Prevent focused proof from shadowing the complete judge proof."""

from __future__ import annotations

import ast
from pathlib import Path


def app_tree() -> ast.Module:
    source = Path("app.py").read_text()
    return ast.parse(
        source,
        filename="app.py",
    )


def assigned_name(
    node: ast.AST,
) -> str | None:
    if isinstance(
        node,
        ast.Assign,
    ):
        for target in node.targets:
            if isinstance(
                target,
                ast.Name,
            ):
                return target.id

    if isinstance(
        node,
        ast.AnnAssign,
    ) and isinstance(
        node.target,
        ast.Name,
    ):
        return node.target.id

    return None


def assigned_value(
    node: ast.AST,
) -> ast.AST | None:
    if isinstance(
        node,
        ast.Assign,
    ):
        return node.value

    if isinstance(
        node,
        ast.AnnAssign,
    ):
        return node.value

    return None


def is_build_focused_proof_call(
    value: ast.AST | None,
) -> bool:
    return (
        isinstance(
            value,
            ast.Call,
        )
        and isinstance(
            value.func,
            ast.Name,
        )
        and value.func.id
        == "build_focused_proof"
    )


def subscript_key(
    node: ast.Subscript,
) -> str | None:
    key = node.slice

    if isinstance(
        key,
        ast.Constant,
    ) and isinstance(
        key.value,
        str,
    ):
        return key.value

    return None


def test_focused_proof_has_its_own_local_name() -> None:
    tree = app_tree()

    focused_assignments = [
        node
        for node in ast.walk(tree)
        if assigned_name(node)
        == "focused_proof"
        and is_build_focused_proof_call(
            assigned_value(node)
        )
    ]

    shadowing_assignments = [
        node
        for node in ast.walk(tree)
        if assigned_name(node)
        == "proof"
        and is_build_focused_proof_call(
            assigned_value(node)
        )
    ]

    assert len(focused_assignments) == 1
    assert shadowing_assignments == []


def test_focused_proof_renderer_uses_expected_fields() -> None:
    tree = app_tree()

    focused_keys = {
        subscript_key(node)
        for node in ast.walk(tree)
        if isinstance(
            node,
            ast.Subscript,
        )
        and isinstance(
            node.value,
            ast.Name,
        )
        and node.value.id
        == "focused_proof"
    }

    assert {
        "title",
        "summary",
        "nodes",
        "metrics",
        "facts",
        "verdict",
    }.issubset(
        focused_keys
    )


def test_complete_proof_schema_remains_separate() -> None:
    tree = app_tree()

    complete_proof_keys = {
        subscript_key(node)
        for node in ast.walk(tree)
        if isinstance(
            node,
            ast.Subscript,
        )
        and isinstance(
            node.value,
            ast.Name,
        )
        and node.value.id == "proof"
    }

    assert "generation_engine" in complete_proof_keys
