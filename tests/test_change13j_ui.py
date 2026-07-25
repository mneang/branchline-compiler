"""UI guardrails for the Director's Cut splice."""

from pathlib import Path


def source() -> str:
    return Path("app.py").read_text()


def test_director_cut_is_attached() -> None:
    app = source()

    assert (
        "from branchline.presentation.director_cut import"
        in app
    )

    assert (
        'one_screen["director_cut"] = '
        "build_director_cut("
        in app
    )

    assert (
        'one_screen["on_replay"] = advance'
        in app
    )


def test_creator_change_and_release_rail_render() -> None:
    app = source()

    assert "render_director_change(" in app
    assert "render_director_release_rail(" in app
    assert "director-change-flow" in app
    assert "director-stage-label" in app


def test_proof_cells_and_replay_render() -> None:
    app = source()

    assert "render_director_proof_cells(" in app
    assert "director-proof-grid" in app
    assert "director-replay" in app
    assert 'icon="replay"' in app


def test_target_audience_is_visible() -> None:
    app = source()

    assert "director-audience" in app
    assert (
        "FOR VISUAL NOVEL & "
        in app
    )


def test_director_cut_fits_short_desktop_viewport() -> None:
    app = source()

    assert "max-height: 760px" in app
    assert (
        ".director-change-impact {\n"
        "          display: none;"
        in app
    )
