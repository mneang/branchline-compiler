"""Official Genblaze and Backblaze alignment guardrails."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.build_selective_release import (
    SelectiveReleaseError,
    build_lineage_pipeline,
    extract_parent_run_id,
    require_parent_run_id,
)


class FakePipeline:
    """Small probe for Pipeline.from_result behavior."""

    def __init__(
        self,
        name: str,
    ) -> None:
        self.name = name
        self.parent_run_id = None

    def from_result(
        self,
        previous: object,
    ) -> "FakePipeline":
        self.parent_run_id = (
            previous.run.run_id
        )

        return self


def test_lineage_pipeline_uses_previous_run() -> None:
    pipeline = build_lineage_pipeline(
        "parent-run-123",
        pipeline_factory=FakePipeline,
    )

    assert pipeline.name == (
        "branchline-selective-shared-dialogue"
    )

    assert pipeline.parent_run_id == (
        "parent-run-123"
    )


def test_baseline_run_id_is_required() -> None:
    assert require_parent_run_id(
        {
            "genblaze": {
                "run_id": "baseline-run",
            }
        }
    ) == "baseline-run"

    with pytest.raises(
        SelectiveReleaseError
    ):
        require_parent_run_id(
            {
                "genblaze": {}
            }
        )


def test_parent_id_can_be_read_from_models() -> None:
    value = SimpleNamespace(
        run=SimpleNamespace(
            parent_run_id="baseline-run"
        )
    )

    assert extract_parent_run_id(
        value
    ) == "baseline-run"

    assert extract_parent_run_id(
        {
            "run": {
                "parent_run_id": (
                    "baseline-run"
                )
            }
        }
    ) == "baseline-run"


def test_selective_release_records_verified_lineage() -> None:
    source = Path(
        "scripts/build_selective_release.py"
    ).read_text()

    assert ".from_result(previous)" in source
    assert '"parent_run_id"' in source
    assert '"stored_parent_run_id"' in source
    assert '"lineage_verified"' in source

    assert (
        "Stored Genblaze manifest did not "
        in source
    )


def test_proof_assigns_each_integrity_layer() -> None:
    source = Path(
        "src/branchline/presentation/"
        "focused_proof.py"
    ).read_text()

    assert '"label": "GENBLAZE"' in source
    assert "BACKBLAZE B2 BYTES" in source
    assert "BRANCHLINE GUARD" in source

    assert "Canonical generation manifest verified" in source
    assert "remotely re-hashed" in source
    assert "2 / 2 routes · 0 stale" in source
