"""Contracts for the verified-media presentation finish."""

from pathlib import Path


def app_source() -> str:
    return Path("app.py").read_text()


def test_media_finish_copy_is_concise() -> None:
    source = app_source()

    assert (
        "Verified dialogue release"
        in source
    )

    assert (
        "Approved Genblaze release evidence."
        in source
    )

    assert (
        "Next, Visual Revision verifies "
        "selective reuse directly from B2."
        in source
    )

    assert (
        "Close playback"
        in source
    )


def test_media_open_state_is_attached() -> None:
    source = app_source()

    assert (
        'state["verified_media"] is not None'
        in source
    )

    assert (
        "media-open"
        in source
    )

    assert (
        ".one-screen-command.media-open"
        in source
    )


def test_media_dialog_is_bounded_and_16_by_9() -> None:
    source = app_source()

    assert (
        "CHANGE 13K-F · INIESTA MEDIA FINISH"
        in source
    )

    assert (
        "max-width: 760px"
        in source
    )

    assert (
        "aspect-ratio:"
        in source
    )

    assert (
        "16 / 9"
        in source
    )

    assert (
        "object-fit: contain"
        in source
    )
