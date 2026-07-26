"""Contracts for Branchline command-action hierarchy."""

from pathlib import Path


def app_source() -> str:
    return Path("app.py").read_text()


def test_close_media_uses_a_distinct_button_class() -> None:
    source = app_source()

    assert (
        'command["primary_kind"]'
        in source
    )

    assert (
        '== "close_media"'
        in source
    )

    assert (
        '"close-media-action"'
        in source
    )

    assert (
        '"one-screen-primary"'
        in source
    )


def test_close_action_does_not_share_primary_class() -> None:
    source = app_source()

    assert (
        '"close-media-action"\n'
        '                if is_close_media\n'
        '                else "one-screen-primary"'
        in source
    )


def test_close_action_is_visually_secondary() -> None:
    source = app_source()

    assert (
        "CHANGE 13K-H · ACTION HIERARCHY LOCK"
        in source
    )

    assert (
        ".close-media-action"
        in source
    )

    assert (
        "background-image:"
        in source
    )

    assert (
        "box-shadow: none"
        in source
    )


def test_close_action_uses_outline_props() -> None:
    source = app_source()

    assert (
        '"outline no-caps color=blue-grey-4"'
        in source
    )
