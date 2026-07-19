"""Anime-inspired visual treatment for Branchline.

The presentation remains English-only and uses motion solely to communicate
release state. It does not imitate any existing franchise or character.
"""

from __future__ import annotations

from html import escape
from typing import Any

from nicegui import ui


ANIME_STYLE = """
<style>
  /*
   * Key-art treatment
   * -----------------
   * Subtle manga framing, halftone texture, directional motion and
   * visual-novel dialogue. Every effect corresponds to workflow state.
   */

  .scene-stage {
    --scene-accent: 103, 232, 249;
    --scene-secondary: 59, 130, 246;
  }

  .scene-stage.accent-cyan {
    --scene-accent: 103, 232, 249;
    --scene-secondary: 34, 211, 238;
  }

  .scene-stage.accent-violet {
    --scene-accent: 196, 181, 253;
    --scene-secondary: 129, 140, 248;
  }

  .scene-stage.accent-rose {
    --scene-accent: 251, 113, 133;
    --scene-secondary: 244, 63, 94;
  }

  .anime-fx {
    position: absolute;
    inset: 0;
    z-index: 2;
    overflow: hidden;
    pointer-events: none;
  }

  /* Restrained halftone texture rather than a noisy comic-book filter. */
  .anime-halftone {
    position: absolute;
    inset: 0;
    opacity: .075;
    background-image:
      radial-gradient(
        circle,
        rgba(255, 255, 255, .95) 0 1px,
        transparent 1.4px
      );
    background-size: 8px 8px;
    mask-image:
      linear-gradient(
        120deg,
        transparent 6%,
        black 48%,
        transparent 90%
      );
  }

  /* Cinematic focus around the active route. */
  .anime-focus-glow {
    position: absolute;
    width: 58%;
    height: 78%;
    right: -12%;
    top: 4%;
    border-radius: 50%;
    opacity: .34;
    filter: blur(72px);
    background:
      radial-gradient(
        circle,
        rgba(var(--scene-accent), .82),
        transparent 68%
      );
    transition:
      opacity .55s ease,
      transform .7s ease;
  }

  .phase-ready .anime-focus-glow {
    opacity: .21;
    transform: translate3d(5%, 2%, 0) scale(.9);
  }

  .phase-planned .anime-focus-glow {
    opacity: .48;
    transform: translate3d(0, 0, 0) scale(1);
  }

  .phase-complete .anime-focus-glow {
    opacity: .57;
    transform: translate3d(-2%, -1%, 0) scale(1.08);
  }

  /*
   * Directional lines appear only after analysis. They communicate that
   * Branchline has discovered a propagation route through the media graph.
   */
  .anime-motion-field {
    position: absolute;
    inset: -20%;
    opacity: 0;
    transform: rotate(-8deg) translateX(7%);
    background:
      repeating-linear-gradient(
        104deg,
        transparent 0 30px,
        rgba(var(--scene-accent), .12) 31px 33px,
        transparent 34px 65px
      );
    mask-image:
      linear-gradient(
        90deg,
        transparent,
        black 48%,
        transparent 95%
      );
    transition:
      opacity .45s ease,
      transform .8s cubic-bezier(.2, .75, .25, 1);
  }

  .phase-planned .anime-motion-field,
  .phase-complete .anime-motion-field {
    opacity: .72;
    transform: rotate(-8deg) translateX(0);
  }

  .phase-complete .anime-motion-field {
    opacity: .38;
  }

  /* Four restrained framing corners make the scene feel like key art. */
  .anime-corner {
    position: absolute;
    width: 60px;
    height: 60px;
    opacity: .72;
  }

  .anime-corner.top-left {
    left: 22px;
    top: 22px;
    border-left: 2px solid rgba(var(--scene-accent), .8);
    border-top: 2px solid rgba(var(--scene-accent), .8);
  }

  .anime-corner.top-right {
    right: 22px;
    top: 22px;
    border-right: 2px solid rgba(var(--scene-accent), .8);
    border-top: 2px solid rgba(var(--scene-accent), .8);
  }

  .anime-corner.bottom-left {
    left: 22px;
    bottom: 22px;
    border-left: 2px solid rgba(var(--scene-accent), .8);
    border-bottom: 2px solid rgba(var(--scene-accent), .8);
  }

  .anime-corner.bottom-right {
    right: 22px;
    bottom: 22px;
    border-right: 2px solid rgba(var(--scene-accent), .8);
    border-bottom: 2px solid rgba(var(--scene-accent), .8);
  }

  .anime-route-ribbon {
    position: absolute;
    right: 25px;
    top: 112px;
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 13px;
    border:
      1px solid rgba(var(--scene-accent), .45);
    border-radius: 999px;
    background: rgba(5, 10, 22, .55);
    backdrop-filter: blur(10px);
    box-shadow:
      0 0 30px rgba(var(--scene-accent), .12);
  }

  .anime-route-ribbon::before {
    content: "";
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: rgb(var(--scene-accent));
    box-shadow:
      0 0 14px rgba(var(--scene-accent), .9);
  }

  .anime-route-ribbon span {
    color: rgba(241, 245, 249, .92);
    font-size: 10px;
    font-weight: 900;
    letter-spacing: .16em;
  }

  /* Visual-novel story line: one sentence only. */
  .vn-dialogue {
    position: relative;
    width: fit-content;
    max-width: 620px;
    margin-bottom: 3px;
    padding: 10px 15px 11px 18px;
    border-left:
      3px solid rgb(var(--scene-accent));
    border-radius: 0 12px 12px 0;
    background:
      linear-gradient(
        90deg,
        rgba(5, 10, 22, .88),
        rgba(5, 10, 22, .48)
      );
    box-shadow:
      0 10px 28px rgba(0, 0, 0, .24);
    backdrop-filter: blur(9px);
  }

  .vn-dialogue-label {
    display: block;
    margin-bottom: 3px;
    color: rgba(var(--scene-accent), .95);
    font-size: 9px;
    font-weight: 900;
    letter-spacing: .18em;
  }

  .vn-dialogue-line {
    margin: 0;
    color: rgba(248, 250, 252, .96);
    font-size: 14px;
    font-weight: 650;
    letter-spacing: .01em;
    line-height: 1.45;
  }

  /*
   * Planned-state asset rows feel like route selections rather than
   * enterprise table rows.
   */
  .plan-block {
    position: relative;
    overflow: hidden;
  }

  .plan-block::before {
    content: "";
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 3px;
    background:
      linear-gradient(
        180deg,
        rgb(var(--scene-accent)),
        rgba(var(--scene-secondary), .15)
      );
  }

  .metric-tile {
    transition:
      transform .28s ease,
      border-color .28s ease,
      background .28s ease;
  }

  .metric-tile:hover {
    transform: translateY(-2px);
    border-color: rgba(var(--scene-accent), .42);
    background: rgba(27, 39, 65, .86);
  }

  /* Publication result arrives like a restrained final episode card. */
  .publication-seal {
    position: relative;
    overflow: hidden;
  }

  .publication-seal::after {
    content: "";
    position: absolute;
    width: 180px;
    height: 180px;
    right: -76px;
    top: -95px;
    border:
      1px solid rgba(var(--scene-accent), .25);
    border-radius: 50%;
    box-shadow:
      0 0 55px rgba(var(--scene-accent), .17);
  }

  .phase-complete .scene-image {
    animation:
      anime-resolution .85s
      cubic-bezier(.2, .75, .25, 1);
  }

  .blocked .anime-focus-glow {
    background:
      radial-gradient(
        circle,
        rgba(251, 113, 133, .7),
        transparent 68%
      );
  }

  .blocked .anime-motion-field {
    opacity: .24;
    background:
      repeating-linear-gradient(
        104deg,
        transparent 0 30px,
        rgba(251, 113, 133, .12) 31px 33px,
        transparent 34px 65px
      );
  }

  @keyframes anime-resolution {
    from {
      opacity: .72;
      transform: scale(1.055);
      filter: saturate(.72) brightness(.86);
    }

    to {
      opacity: 1;
      transform: scale(1.015);
      filter: saturate(1) brightness(1);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .anime-focus-glow,
    .anime-motion-field,
    .scene-image,
    .metric-tile {
      animation: none !important;
      transition: none !important;
    }
  }

  @media (max-width: 700px) {
    .anime-route-ribbon {
      display: none;
    }

    .anime-corner {
      width: 38px;
      height: 38px;
    }

    .vn-dialogue {
      max-width: calc(100vw - 75px);
    }
  }
</style>
"""


def install_anime_style() -> None:
    """Install the shared cinematic style layer."""
    ui.add_head_html(
        ANIME_STYLE,
        shared=True,
    )


def render_scene_fx(
    experience: dict[str, Any],
) -> None:
    """Render state-aware visual effects over the story scene."""
    route_label = escape(
        str(experience["route_label"])
    )

    ui.html(
        f"""
        <div class="anime-fx" aria-hidden="true">
          <div class="anime-focus-glow"></div>
          <div class="anime-motion-field"></div>
          <div class="anime-halftone"></div>

          <div class="anime-corner top-left"></div>
          <div class="anime-corner top-right"></div>
          <div class="anime-corner bottom-left"></div>
          <div class="anime-corner bottom-right"></div>

          <div class="anime-route-ribbon">
            <span>{route_label} · ACTIVE ROUTE</span>
          </div>
        </div>
        """,
        sanitize=False,
    ).classes(
        "absolute inset-0 pointer-events-none"
    )


def render_story_quote(
    experience: dict[str, Any],
) -> None:
    """Render one concise visual-novel story line."""
    dialogue_line = escape(
        str(experience["dialogue_line"])
    )

    ui.html(
        f"""
        <blockquote class="vn-dialogue">
          <span class="vn-dialogue-label">
            CURRENT STORY LINE
          </span>
          <p class="vn-dialogue-line">
            “{dialogue_line}”
          </p>
        </blockquote>
        """,
        sanitize=False,
    )
