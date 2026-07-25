"""Branchline dynamic manga release studio."""

from __future__ import annotations

import asyncio
import os
from html import escape
from pathlib import Path
from typing import Any

from nicegui import app, ui

from branchline.application.live_analysis import (
    LiveAnalysisError,
    analysis_metrics,
    analyze_story_revision,
    validate_analysis_against_release,
)
from branchline.application.live_execution import (
    LiveExecutionError,
    LiveExecutionUnavailable,
    execute_scenario_b_release,
)
from branchline.presentation.final_third import (
    build_final_third_context,
)
from branchline.presentation.focus_experience import (
    build_focus_experience,
    director_options,
)
from branchline.presentation.flow import (
    COMPLETE,
    PLANNED,
    READY,
)
from branchline.presentation.release_choreography import (
    build_causal_route,
    build_revision_story,
    build_verified_replay_stages,
    media_comparison,
    validate_replay_stage,
)
from branchline.application.verified_media import (
    VerifiedMediaError,
    load_verified_media_bundle,
    local_presentation_fallback,
)
from branchline.presentation.focused_proof import (
    build_focused_proof,
)
from branchline.presentation.director_cut import (
    build_director_cut,
)
from branchline.presentation.one_screen_release import (
    build_one_screen_command,
    workflow_options,
)
from branchline.presentation.release_spread import (
    build_release_spread,
)


ROOT = Path(__file__).resolve().parent
MANGA_DIRECTORY = ROOT / "assets" / "manga"
MEDIA_DIRECTORY = (
    ROOT / "assets" / "release_media"
)

if not MANGA_DIRECTORY.exists():
    raise RuntimeError(
        "Manga artwork is missing. Run "
        "`python scripts/generate_manga_release_art.py`."
    )

if not MEDIA_DIRECTORY.exists():
    raise RuntimeError(
        "Playable release media is missing. Run "
        "`python scripts/generate_release_media.py`."
    )

app.add_static_files(
    "/manga-art",
    str(MANGA_DIRECTORY),
)

app.add_static_files(
    "/release-media",
    str(MEDIA_DIRECTORY),
)


ui.add_head_html(
    """
    <style>
      :root {
        --ink: #05070c;
        --panel: #0b111c;
        --panel-soft: #111a2a;
        --line: rgba(226, 232, 240, .16);
        --muted: #8794a8;
        --cyan: #59d6e8;
        --amber: #edb55d;
        --rose: #eb6682;
        --violet: #a993e8;
      }

      html,
      body {
        margin: 0;
        width: 100%;
        min-height: 100%;
        background: var(--ink);
      }

      body {
        overflow: hidden;
        color: #edf2f8;
        background:
          radial-gradient(
            circle at 12% 2%,
            rgba(89, 214, 232, .10),
            transparent 29%
          ),
          radial-gradient(
            circle at 92% 7%,
            rgba(169, 147, 232, .07),
            transparent 25%
          ),
          var(--ink);
      }

      .app-shell {
        width: min(1460px, calc(100vw - 28px));
        height: 100vh;
        margin: 0 auto;
        padding: 12px 0;
        box-sizing: border-box;
        display: flex;
        flex-direction: column;
        gap: 10px;
      }

      .topbar {
        min-height: 48px;
        flex: 0 0 auto;
      }

      .brand-mark {
        letter-spacing: .29em;
      }

      .purpose-line {
        color: #b7c1d0;
        font-size: 12px;
      }

      .mode-label {
        font-size: 9px;
        font-weight: 900;
        letter-spacing: .13em;
        color: #68778d;
      }

      .incident-select {
        width: 190px;
      }

      .release-shell {
        min-height: 0;
        flex: 1 1 auto;
        display: grid;
        grid-template-rows:
          minmax(0, 1fr)
          68px
          74px;
        overflow: hidden;
        border: 1px solid var(--line);
        border-radius: 20px;
        background: #080c14;
        box-shadow:
          0 27px 75px rgba(0, 0, 0, .42);
      }

      .main-grid {
        min-height: 0;
        display: grid;
        grid-template-columns:
          minmax(0, 1.53fr)
          minmax(360px, .72fr);
      }

      .spread-stage {
        position: relative;
        min-width: 0;
        min-height: 0;
        overflow: hidden;
        border-right: 1px solid var(--line);
        background: #020306;
      }

      .spread-panels {
        position: absolute;
        inset: 0;
        display: grid;
        grid-template-columns:
          minmax(0, 1fr)
          minmax(0, 1fr);
        gap: 8px;
        padding: 8px;
        background: #020305;
      }

      .manga-panel {
        position: relative;
        min-width: 0;
        min-height: 0;
        overflow: hidden;
        isolation: isolate;
        background: #0c1018;
        filter: saturate(.83);
      }

      .manga-panel.left {
        clip-path:
          polygon(
            0 0,
            100% 0,
            91% 100%,
            0 100%
          );
      }

      .manga-panel.right {
        margin-left: -5%;
        clip-path:
          polygon(
            9% 0,
            100% 0,
            100% 100%,
            0 100%
          );
      }

      .manga-panel::after {
        content: "";
        position: absolute;
        inset: 0;
        z-index: 2;
        pointer-events: none;
        background:
          linear-gradient(
            180deg,
            rgba(3, 5, 9, .12),
            transparent 39%,
            rgba(3, 5, 9, .91) 100%
          );
      }

      .manga-panel.warning {
        box-shadow:
          inset 0 0 0 3px
          rgba(237, 181, 93, .58);
      }

      .manga-panel.safe {
        box-shadow:
          inset 0 0 0 3px
          rgba(89, 214, 232, .47);
      }

      .manga-panel.blocked {
        box-shadow:
          inset 0 0 0 4px
          rgba(235, 102, 130, .68);
      }

      .manga-image {
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
        transform: scale(1.025);
        animation:
          panel-arrival .58s
          cubic-bezier(.2, .75, .25, 1);
      }

      .panel-heading {
        position: absolute;
        z-index: 4;
        top: 22px;
        left: 22px;
        display: flex;
        flex-direction: column;
        gap: 5px;
      }

      .manga-panel.right .panel-heading {
        left: 12%;
      }

      .panel-label {
        width: fit-content;
        padding: 7px 10px;
        color: #080b11;
        background: rgba(245, 245, 241, .94);
        font-size: 10px;
        font-weight: 950;
        letter-spacing: .17em;
        transform: rotate(-1deg);
        box-shadow:
          4px 4px 0 rgba(6, 8, 12, .72);
      }

      .panel-status {
        width: fit-content;
        padding: 6px 9px;
        border-left: 3px solid var(--cyan);
        background: rgba(4, 7, 13, .78);
        color: #f8fafc;
        font-size: 11px;
        font-weight: 900;
        letter-spacing: .13em;
        backdrop-filter: blur(7px);
      }

      .warning .panel-status {
        border-color: var(--amber);
      }

      .blocked .panel-status {
        border-color: var(--rose);
        color: #ffdce4;
      }

      .panel-number {
        position: absolute;
        z-index: 4;
        right: 22px;
        bottom: 112px;
        color: rgba(255, 255, 255, .10);
        font-family: Georgia, serif;
        font-size: clamp(80px, 9vw, 150px);
        font-weight: 900;
        line-height: .8;
      }

      .story-strip {
        position: absolute;
        z-index: 6;
        left: 28px;
        right: 28px;
        bottom: 23px;
        display: grid;
        grid-template-columns:
          minmax(175px, .40fr)
          minmax(0, 1.60fr);
        overflow: hidden;
        border: 1px solid rgba(255, 255, 255, .22);
        border-left: 4px solid var(--cyan);
        background:
          linear-gradient(
            90deg,
            rgba(3, 5, 10, .95),
            rgba(3, 5, 10, .77)
          );
        box-shadow:
          0 15px 35px rgba(0, 0, 0, .38);
        backdrop-filter: blur(12px);
      }

      .story-meta {
        padding: 12px 15px;
        border-right:
          1px solid rgba(255, 255, 255, .14);
      }

      .story-copy {
        padding: 12px 18px;
      }

      .decision-rail {
        min-width: 0;
        min-height: 0;
        display: flex;
        flex-direction: column;
        gap: 14px;
        padding: 22px;
        box-sizing: border-box;
        overflow-y: auto;
        scrollbar-width: thin;
        scrollbar-color:
          rgba(89, 214, 232, .28)
          transparent;
        background:
          linear-gradient(
            180deg,
            #0d1422,
            #070b13
          );
      }

      .decision-eyebrow {
        color: var(--cyan);
        font-size: 9px;
        font-weight: 950;
        letter-spacing: .19em;
      }

      .revision-summary {
        border-left: 3px solid var(--amber);
        padding: 11px 12px;
        background:
          rgba(237, 181, 93, .07);
      }

      .diff-grid {
        display: grid;
        grid-template-columns:
          minmax(0, 1fr)
          22px
          minmax(0, 1fr);
        gap: 6px;
        align-items: stretch;
      }

      .diff-card {
        min-width: 0;
        padding: 11px;
        border: 1px solid var(--line);
        background: rgba(18, 28, 46, .66);
      }

      .diff-card.after {
        border-color:
          rgba(89, 214, 232, .40);
        background:
          rgba(27, 113, 129, .10);
      }

      .diff-arrow {
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--cyan);
        font-weight: 900;
      }

      .metric-row {
        display: grid;
        grid-template-columns:
          repeat(3, minmax(0, 1fr));
        gap: 7px;
      }

      .metric {
        min-width: 0;
        padding: 11px 9px;
        border-top: 2px solid var(--cyan);
        background: rgba(18, 28, 46, .73);
      }

      .causal-map {
        position: relative;
        display: grid;
        grid-template-columns:
          minmax(90px, .95fr)
          27px
          minmax(120px, 1.20fr)
          27px
          minmax(95px, .95fr);
        align-items: center;
        gap: 4px;
        padding: 12px;
        overflow: hidden;
        border: 1px solid var(--line);
        background: rgba(12, 19, 32, .77);
      }

      .cause-node {
        position: relative;
        z-index: 2;
        min-width: 0;
        padding: 10px 7px;
        border: 1px solid rgba(255, 255, 255, .16);
        background: rgba(6, 10, 18, .90);
        text-align: center;
        color: #e9eef7;
        font-size: 9px;
        font-weight: 900;
        letter-spacing: .10em;
      }

      .cause-node.source {
        border-color:
          rgba(237, 181, 93, .50);
      }

      .cause-node.destination {
        border-color:
          rgba(89, 214, 232, .48);
      }

      .asset-stack {
        display: flex;
        flex-direction: column;
        gap: 6px;
      }

      .cause-line {
        position: relative;
        height: 2px;
        overflow: hidden;
        background:
          rgba(148, 163, 184, .22);
      }

      .cause-line::after {
        content: "";
        position: absolute;
        inset: 0;
        background:
          linear-gradient(
            90deg,
            transparent,
            var(--cyan),
            transparent
          );
        transform: translateX(-110%);
      }

      .causal-map.animate
      .cause-line::after {
        animation:
          causal-trace .72s
          cubic-bezier(.2, .75, .25, 1)
          forwards;
      }

      .causal-map.animate
      .asset-stack
      .cause-node {
        opacity: 0;
        transform: translateY(7px);
        animation:
          cause-reveal .33s ease-out
          .42s forwards;
      }

      .causal-result {
        border-left: 2px solid var(--cyan);
        padding-left: 10px;
      }

      .plan-binding {
        border-left: 2px solid
          rgba(89, 214, 232, .55);
        padding-left: 10px;
      }

      .stage-list {
        display: flex;
        flex-direction: column;
        gap: 7px;
      }

      .stage-row {
        display: grid;
        grid-template-columns:
          23px
          minmax(0, 1fr);
        gap: 8px;
        align-items: start;
        padding: 9px 10px;
        border: 1px solid var(--line);
        background: rgba(13, 21, 35, .72);
      }

      .stage-row.complete {
        border-color:
          rgba(89, 214, 232, .28);
      }

      .stage-row.active {
        border-color:
          rgba(237, 181, 93, .48);
        background:
          rgba(115, 72, 18, .10);
      }

      .stage-row.pending {
        opacity: .48;
      }

      .verdict {
        position: relative;
        overflow: hidden;
        padding: 15px;
        border: 1px solid
          rgba(89, 214, 232, .44);
        background:
          rgba(20, 129, 147, .10);
      }

      .verdict.blocked {
        border-color:
          rgba(235, 102, 130, .52);
        background:
          rgba(142, 24, 53, .12);
      }

      .verdict::after {
        content: "";
        position: absolute;
        right: -47px;
        top: -47px;
        width: 115px;
        height: 115px;
        border:
          1px solid rgba(89, 214, 232, .21);
        border-radius: 50%;
      }

      .primary-action {
        width: 100%;
        min-height: 50px;
        border-radius: 0;
        font-weight: 950;
        letter-spacing: .015em;
        clip-path:
          polygon(
            0 0,
            96% 0,
            100% 50%,
            96% 100%,
            0 100%
          );
      }

      .secondary-action {
        width: 100%;
        min-height: 31px;
        color: #8c9aae;
      }

      .release-shell.compact {
        grid-template-rows:
          minmax(0, 1fr)
          58px;
      }

      /* -------------------------------------------------
         Change 13C: one-screen manga release room
         ------------------------------------------------- */

      header {
        min-height: 0 !important;
        padding-top: 12px !important;
        padding-bottom: 10px !important;
      }

      .panel-media-overlay {
        position: absolute;
        z-index: 30;
        inset: 0;
        min-width: 0;
        padding: 18px;
        overflow: hidden;
        background:
          linear-gradient(
            145deg,
            rgba(5, 10, 18, .985),
            rgba(8, 18, 29, .975)
          );
        backdrop-filter: blur(9px);
      }

      .verified-panel-video {
        width: 100%;
        min-height: 0;
        flex: 1 1 auto;
        overflow: hidden;
        border: 1px solid
          rgba(89, 214, 232, .34);
        background: #02050a;
      }

      .verified-panel-video video {
        width: 100%;
        height: 100%;
        max-height: 100%;
        object-fit: contain;
        background: #02050a;
      }

      .media-tab-row {
        width: fit-content;
        gap: 4px;
        padding: 3px;
        border: 1px solid var(--line);
        background: rgba(2, 6, 11, .72);
      }

      .media-tab {
        min-height: 30px;
        padding: 0 11px;
        color: #718399;
        font-size: 9px;
      }

      .media-tab.active {
        border: 1px solid
          rgba(89, 214, 232, .52);
        background:
          rgba(31, 127, 145, .13);
        color: #dffcff;
      }



      /* Change 13J: Director's Cut creator workflow */

      .director-audience {
        margin-top: 1px;
        color: #8299ad;
        font-size: 8px;
        font-weight: 800;
        letter-spacing: .12em;
        line-height: 1.15;
      }

      .director-rail {
        grid-column: 1 / -1;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        min-width: 0;
        padding: 5px 14px;
        border-bottom: 1px solid
          rgba(120, 145, 170, .17);
        background: rgba(7, 15, 27, .84);
      }

      .director-stage {
        display: flex;
        min-width: 0;
        align-items: center;
        gap: 5px;
        color: #60758a;
      }

      .director-stage-label {
        font-size: 8px;
        font-weight: 850;
        letter-spacing: .085em;
        white-space: nowrap;
      }

      .director-stage-mark {
        font-size: 9px;
        font-weight: 900;
      }

      .director-stage.done {
        color: #78dae6;
      }

      .director-stage.active {
        color: #ffffff;
      }

      .director-stage.blocked {
        color: #ff85aa;
      }

      .director-stage.skipped {
        color: #8794a3;
      }

      .director-stage-arrow {
        color: #405368;
        font-size: 9px;
      }

      .director-change {
        width: 100%;
        margin-bottom: 7px;
        padding-bottom: 7px;
        border-bottom: 1px solid
          rgba(120, 145, 170, .17);
      }

      .director-change-eyebrow,
      .director-change-label {
        color: #63dbe9;
        font-size: 7px;
        font-weight: 900;
        letter-spacing: .13em;
      }

      .director-change-subject {
        color: #8ba0b5;
        font-size: 8px;
        font-weight: 750;
      }

      .director-change-flow {
        display: grid;
        grid-template-columns:
          minmax(0, 1fr)
          auto
          minmax(0, 1fr);
        align-items: center;
        gap: 7px;
        margin-top: 5px;
      }

      .director-change-side {
        min-width: 0;
      }

      .director-change-value {
        overflow: hidden;
        color: #c7d2df;
        font-size: 9px;
        font-weight: 720;
        line-height: 1.25;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .director-change-value.after {
        color: #ffffff;
      }

      .director-change-arrow {
        color: #63dbe9;
        font-size: 12px;
        font-weight: 900;
      }

      .director-change-impact {
        margin-top: 4px;
        color: #879bb0;
        font-size: 8px;
        font-weight: 650;
      }

      .director-proof-grid {
        display: grid;
        width: 100%;
        grid-template-columns:
          repeat(3, minmax(0, 1fr));
        gap: 5px;
        margin-top: 5px;
      }

      .director-proof-cell {
        min-width: 0;
        padding: 6px 7px;
        border-left: 2px solid
          rgba(99, 219, 233, .75);
        background: rgba(17, 32, 51, .72);
      }

      .director-proof-cell.blocked {
        border-left-color:
          rgba(255, 105, 152, .88);
      }

      .director-proof-label {
        color: #6f899f;
        font-size: 6px;
        font-weight: 900;
        letter-spacing: .09em;
      }

      .director-proof-value {
        overflow: hidden;
        margin-top: 3px;
        color: #f4f7fb;
        font-size: 9px;
        font-weight: 850;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .director-proof-detail {
        display: -webkit-box;
        overflow: hidden;
        margin-top: 2px;
        color: #7890a5;
        font-size: 7px;
        font-weight: 600;
        line-height: 1.2;
        -webkit-box-orient: vertical;
        -webkit-line-clamp: 2;
      }

      .director-next {
        width: 100%;
        color: #06111d !important;
        background: #72dbe7 !important;
        font-weight: 850;
      }

      .director-next:hover {
        filter: brightness(1.06);
      }

      .director-replay {
        color: #86b9dc !important;
      }

      @media (
        max-height: 760px
      ) and (
        min-width: 900px
      ) {
        .director-change-impact {
          display: none;
        }

        .director-proof-cell {
          padding: 5px 6px;
        }

        .director-proof-detail {
          -webkit-line-clamp: 1;
        }
      }

      /* Change 13I: La Pelopina motion layer */

      /*
       * Motion principles:
       * - one causal movement per transition;
       * - no permanent looping decoration;
       * - interaction feedback stays under 220ms;
       * - reduced-motion users receive the same information.
       */

      @keyframes branchline-panel-arrive-left {
        0% {
          opacity: 0;
          transform:
            translate3d(-18px, 8px, 0)
            scale(.992);
          filter: contrast(.92);
        }

        100% {
          opacity: 1;
          transform:
            translate3d(0, 0, 0)
            scale(1);
          filter: contrast(1);
        }
      }

      @keyframes branchline-panel-arrive-right {
        0% {
          opacity: 0;
          transform:
            translate3d(18px, 8px, 0)
            scale(.992);
          filter: contrast(.92);
        }

        100% {
          opacity: 1;
          transform:
            translate3d(0, 0, 0)
            scale(1);
          filter: contrast(1);
        }
      }

      @keyframes branchline-strip-arrive {
        0% {
          opacity: 0;
          transform: translate3d(0, 10px, 0);
        }

        100% {
          opacity: 1;
          transform: translate3d(0, 0, 0);
        }
      }

      @keyframes branchline-proof-arrive {
        0% {
          opacity: 0;
          transform:
            translate3d(0, 7px, 0)
            scale(.985);
        }

        100% {
          opacity: 1;
          transform:
            translate3d(0, 0, 0)
            scale(1);
        }
      }

      @keyframes branchline-arrow-pass {
        0% {
          opacity: .1;
          transform: translateX(-5px);
        }

        55% {
          opacity: 1;
        }

        100% {
          opacity: .82;
          transform: translateX(0);
        }
      }

      @keyframes branchline-metric-confirm {
        0% {
          opacity: 0;
          transform:
            translate3d(0, 8px, 0)
            scale(.95);
        }

        70% {
          transform:
            translate3d(0, -1px, 0)
            scale(1.015);
        }

        100% {
          opacity: 1;
          transform:
            translate3d(0, 0, 0)
            scale(1);
        }
      }

      @keyframes branchline-media-reveal {
        0% {
          opacity: 0;
          transform: scale(1.012);
          filter: blur(3px);
        }

        100% {
          opacity: 1;
          transform: scale(1);
          filter: blur(0);
        }
      }

      /* Manga spread opens like a deliberate two-touch combination. */

      .manga-panel {
        isolation: isolate;
        transform-origin: center;
        will-change: transform, opacity;
        transition:
          transform 180ms ease,
          border-color 180ms ease,
          box-shadow 180ms ease,
          filter 180ms ease;
      }

      .manga-panel.left {
        animation:
          branchline-panel-arrive-left
          420ms
          cubic-bezier(.22, .8, .24, 1)
          both;
      }

      .manga-panel.right {
        animation:
          branchline-panel-arrive-right
          460ms
          55ms
          cubic-bezier(.22, .8, .24, 1)
          both;
      }

      .manga-panel:hover {
        transform: translateY(-2px);
        filter: contrast(1.025);
      }

      .manga-panel:focus-within {
        transform: translateY(-2px);
        outline: 2px solid
          rgba(103, 232, 249, .56);
        outline-offset: 2px;
      }

      /*
       * The panel border remains the primary state indicator.
       * Hover never changes semantic state colors.
       */

      .manga-panel:hover::after {
        content: "";
        position: absolute;
        z-index: 8;
        inset: 0;
        pointer-events: none;
        border-radius: inherit;
        box-shadow:
          inset 0 0 0 1px
          rgba(255, 255, 255, .08);
      }

      /* Story explanation follows the panel reveal. */

      .story-strip {
        animation:
          branchline-strip-arrive
          360ms
          110ms
          cubic-bezier(.22, .8, .24, 1)
          both;
        transition:
          border-color 180ms ease,
          background-color 180ms ease;
      }

      /* Verified B2 media fades into the same panel, never over it. */

      .panel-media-overlay {
        animation:
          branchline-media-reveal
          340ms
          cubic-bezier(.22, .8, .24, 1)
          both;
        backdrop-filter: blur(9px);
      }

      .panel-media-overlay video {
        transition:
          transform 180ms ease,
          filter 180ms ease;
      }

      .panel-media-overlay video:hover {
        transform: scale(1.004);
        filter: contrast(1.025);
      }

      /*
       * Active scenario navigation becomes obvious immediately,
       * while inactive scenarios remain quiet.
       */

      .q-tab {
        position: relative;
        transition:
          color 170ms ease,
          background-color 170ms ease,
          opacity 170ms ease;
      }

      .q-tab:not(.q-tab--active) {
        opacity: .7;
      }

      .q-tab:not(.q-tab--active):hover {
        opacity: 1;
        background:
          rgba(148, 163, 184, .055);
      }

      .q-tab--active {
        opacity: 1;
        background:
          rgba(34, 211, 238, .07);
      }

      .q-tab--active::after {
        content: "";
        position: absolute;
        right: 18px;
        bottom: 4px;
        left: 18px;
        height: 2px;
        border-radius: 999px;
        background:
          rgba(103, 232, 249, .88);
        box-shadow:
          0 0 12px
          rgba(34, 211, 238, .24);
      }

      /*
       * Buttons feel physical without becoming flashy.
       */

      .q-btn {
        transition:
          transform 145ms ease,
          filter 145ms ease,
          box-shadow 145ms ease;
      }

      .q-btn:not([disabled]):hover {
        transform: translateY(-1px);
        filter: brightness(1.055);
      }

      .q-btn:not([disabled]):active {
        transform: translateY(0) scale(.985);
      }

      .q-btn:focus-visible {
        outline: 2px solid
          rgba(103, 232, 249, .72);
        outline-offset: 3px;
      }

      /*
       * Metrics arrive as confirmation, not as a looping dashboard.
       */

      .command-metric,
      .proof-metric,
      .metric-card {
        animation:
          branchline-metric-confirm
          360ms
          cubic-bezier(.22, .8, .24, 1)
          both;
      }

      .command-metric:nth-child(2),
      .proof-metric:nth-child(2),
      .metric-card:nth-child(2) {
        animation-delay: 55ms;
      }

      .command-metric:nth-child(3),
      .proof-metric:nth-child(3),
      .metric-card:nth-child(3) {
        animation-delay: 105ms;
      }

      /* Causal proof reads from left to right. */

      .proof-node {
        animation:
          branchline-proof-arrive
          320ms
          cubic-bezier(.22, .8, .24, 1)
          both;
        transition:
          transform 160ms ease,
          border-color 160ms ease,
          background-color 160ms ease;
      }

      .proof-node:hover {
        transform: translateY(-2px);
      }

      .proof-node:nth-of-type(2) {
        animation-delay: 45ms;
      }

      .proof-node:nth-of-type(3) {
        animation-delay: 90ms;
      }

      .proof-node:nth-of-type(4) {
        animation-delay: 135ms;
      }

      .proof-node:nth-of-type(5) {
        animation-delay: 180ms;
      }

      .proof-causal-arrow {
        animation:
          branchline-arrow-pass
          300ms
          110ms
          ease-out
          both;
      }

      /*
       * Sponsor evidence needs to survive compressed demo video.
       */

      .command-sponsor-line {
        text-shadow:
          0 1px 0
          rgba(0, 0, 0, .5);
        transition:
          color 180ms ease,
          opacity 180ms ease;
      }

      .command-sponsor-line:hover {
        color: #d5eef7 !important;
      }

      .command-lineage {
        transition:
          color 180ms ease,
          opacity 180ms ease;
      }

      .command-lineage:hover {
        color: #c5d7e8 !important;
      }

      /*
       * Avoid motion sickness and keep accessibility truthful.
       */

      @media (
        prefers-reduced-motion: reduce
      ) {
        .manga-panel,
        .manga-panel.left,
        .manga-panel.right,
        .story-strip,
        .panel-media-overlay,
        .command-metric,
        .proof-metric,
        .metric-card,
        .proof-node,
        .proof-causal-arrow {
          animation: none !important;
        }

        .manga-panel,
        .q-btn,
        .q-tab,
        .proof-node,
        .panel-media-overlay video {
          transition: none !important;
        }

        .manga-panel:hover,
        .manga-panel:focus-within,
        .q-btn:not([disabled]):hover,
        .q-btn:not([disabled]):active,
        .proof-node:hover,
        .panel-media-overlay video:hover {
          transform: none !important;
        }
      }

      /* Change 13F: clean finishing pass */

      .command-lineage {
        max-width: 100%;
        overflow: hidden;
        color: #9eb1c6 !important;
        font-size: 11px !important;
        font-weight: 650;
        line-height: 1.35;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .command-sponsor-line {
        color: #b3cbd8 !important;
        font-size: 11px !important;
        font-weight: 750;
        letter-spacing: .012em;
        line-height: 1.35;
      }

      .proof-actions {
        position: sticky;
        z-index: 3;
        bottom: -1px;
        width: 100%;
        margin-top: 0;
        padding-top: 9px;
        padding-bottom: 3px;
        background: #08111f;
        border-top: 1px solid
          rgba(126, 146, 174, .20);
      }

      @media (
        max-height: 760px
      ) and (
        min-width: 900px
      ) {
        .focused-proof-card {
          width: min(1060px, 96vw);
          max-height: 94vh;
          padding: 15px 18px;
          gap: 9px;
          overflow-y: auto;
        }

        .proof-title {
          font-size: 34px;
          line-height: 1.02;
        }

        .proof-summary {
          max-width: 860px;
          font-size: 12px;
          line-height: 1.35;
        }

        .proof-legend-row {
          gap: 22px;
          padding: 7px 10px;
        }

        .proof-causal-row {
          gap: 7px;
        }

        .proof-causal-arrow {
          font-size: 21px;
        }

        .proof-node {
          min-height: 80px;
          padding: 9px 11px;
        }

        .proof-node-title {
          font-size: 13px;
        }

        .proof-node-detail {
          font-size: 10px;
        }

        .proof-metric-row {
          gap: 8px;
        }

        .proof-metric {
          padding: 8px 11px;
        }

        .proof-metric-value {
          font-size: 23px;
        }

        .proof-fact-row {
          gap: 18px;
          padding: 7px 2px;
        }

        .proof-fact-value {
          font-size: 12px;
        }

        .proof-fact-detail {
          font-size: 10px;
          line-height: 1.25;
        }

        .proof-verdict {
          padding: 6px 10px;
          font-size: 11px;
        }

        .proof-actions {
          padding-top: 7px;
        }
      }

      /* Change 13E: final-control layer */

      .manga-panel.right:has(.panel-media-overlay) {
        transform: none !important;
        clip-path: none !important;
        overflow: visible !important;
        margin-left: 0 !important;
      }

      .manga-panel.right:has(.panel-media-overlay)::before,
      .manga-panel.right:has(.panel-media-overlay)::after {
        display: none !important;
      }

      .manga-panel.right
      .panel-media-overlay {
        inset: 0 0 94px 0 !important;
        width: 100% !important;
        max-width: 100% !important;
        padding: 16px 18px 12px !important;
        overflow: hidden !important;
        transform: none !important;
        clip-path: none !important;
      }

      .panel-media-overlay > * {
        min-width: 0;
        max-width: 100%;
      }

      .verified-panel-video {
        min-height: 0 !important;
        max-height: calc(100% - 104px);
      }

      .verified-panel-video video {
        max-height: 100% !important;
        object-fit: contain !important;
      }

      .story-strip {
        z-index: 45 !important;
      }

      .command-detail,
      .command-explanation,
      .command-lineage,
      .command-sponsor-line {
        font-size: 11px !important;
      }

      .command-metric {
        padding: 9px 11px !important;
      }

      .command-metric .text-lg {
        font-size: 26px !important;
        line-height: 1 !important;
      }

      .one-screen-proof {
        font-size: 11px !important;
      }

      .focused-proof-card {
        width: min(1040px, 94vw);
        max-width: 1040px;
        max-height: 92vh;
        padding: 24px;
        gap: 18px;
        overflow: auto;
        border: 1px solid
          rgba(89, 214, 232, .30);
        background: #08111f;
      }

      .proof-eyebrow {
        color: #5de4ef;
        font-size: 11px;
        font-weight: 900;
        letter-spacing: .16em;
      }

      .proof-title {
        color: #f5f7fa;
        font-size: clamp(25px, 2.4vw, 38px);
        font-weight: 950;
        line-height: 1.05;
      }

      .proof-summary {
        max-width: 780px;
        color: #9aaabe;
        font-size: 14px;
        line-height: 1.55;
      }

      .proof-legend-row {
        width: 100%;
        align-items: center;
        gap: 28px;
        padding: 11px 14px;
        border-top: 1px solid
          rgba(126, 146, 174, .22);
        border-bottom: 1px solid
          rgba(126, 146, 174, .22);
      }

      .proof-legend-shape {
        display: inline-block;
        width: 19px;
        height: 19px;
        border: 2px solid #7590aa;
        background: rgba(69, 88, 112, .20);
      }

      .proof-legend-shape.source {
        border-radius: 2px;
      }

      .proof-legend-shape.media {
        width: 27px;
        border-radius: 7px;
      }

      .proof-legend-shape.route {
        border-radius: 50%;
      }

      .proof-legend-label {
        color: #a8b7c9;
        font-size: 12px;
        font-weight: 700;
      }

      /* Change 13K-B1: fault-isolation topology */

      .proof-topology {
        display: grid;
        width: 100%;
        grid-template-columns: minmax(0, 1fr);
        align-items: center;
        gap: 14px;
      }

      .proof-topology.split {
        grid-template-columns:
          minmax(0, 1.35fr)
          minmax(220px, .65fr);
      }

      .proof-independent-panel {
        width: 100%;
        align-items: center;
        justify-content: center;
        gap: 7px;
        padding-left: 18px;
        border-left: 1px dashed
          rgba(85, 220, 232, .42);
      }

      .proof-independent-label {
        color: #69dce8;
        font-size: 9px;
        font-weight: 900;
        letter-spacing: .14em;
        line-height: 1;
      }

      .proof-independent-panel
      .proof-node.independent {
        width: min(250px, 100%);
        min-height: 82px;
        border-style: dashed;
        background:
          rgba(15, 48, 61, .38);
      }

      @media (max-width: 800px) {
        .proof-topology.split {
          grid-template-columns: 1fr;
        }

        .proof-independent-panel {
          padding-top: 13px;
          padding-left: 0;
          border-top: 1px dashed
            rgba(85, 220, 232, .42);
          border-left: 0;
        }
      }

      .proof-causal-row {
        width: 100%;
        align-items: stretch;
        justify-content: center;
        gap: 10px;
      }

      .proof-causal-arrow {
        align-self: center;
        color: #526b85;
        font-size: 25px;
      }

      .proof-node {
        width: min(185px, 20vw);
        min-height: 102px;
        justify-content: center;
        gap: 5px;
        padding: 14px;
        border: 2px solid #61778f;
        background: rgba(14, 27, 44, .88);
      }

      .proof-node.source {
        border-radius: 2px;
      }

      .proof-node.media {
        border-radius: 10px;
      }

      .proof-node.route {
        border-radius: 52px;
      }

      .proof-node.changed,
      .proof-node.rebuild {
        border-color: #d9a84f;
      }

      .proof-node.verified {
        border-color: #55dce8;
      }

      .proof-node.missing,
      .proof-node.blocked {
        border-color: #ee7897;
        background: rgba(91, 20, 43, .30);
      }

      .proof-node-title {
        color: #f4f6f9;
        font-size: 14px;
        font-weight: 900;
        line-height: 1.2;
        text-align: center;
      }

      .proof-node-detail {
        color: #8295aa;
        font-size: 11px;
        line-height: 1.35;
        text-align: center;
      }

      .proof-metric-row {
        width: 100%;
        display: grid !important;
        grid-template-columns:
          repeat(3, minmax(0, 1fr));
        gap: 10px;
      }

      .proof-metric {
        padding: 13px 15px;
        border-left: 3px solid #58dbe8;
        background: rgba(17, 32, 51, .78);
      }

      .proof-metric-label {
        color: #71869e;
        font-size: 10px;
        font-weight: 900;
        letter-spacing: .12em;
      }

      .proof-metric-value {
        color: white;
        font-size: 27px;
        font-weight: 950;
        line-height: 1.05;
      }

      .proof-facts {
        width: 100%;
        gap: 0;
        border-top: 1px solid
          rgba(126, 146, 174, .20);
      }

      .proof-fact-row {
        width: 100%;
        align-items: start;
        gap: 22px;
        padding: 12px 2px;
        border-bottom: 1px solid
          rgba(126, 146, 174, .20);
      }

      .proof-fact-label {
        width: 150px;
        flex: 0 0 150px;
        color: #5de4ef;
        font-size: 10px;
        font-weight: 900;
        letter-spacing: .12em;
      }

      .proof-fact-value {
        color: #e8edf4;
        font-size: 13px;
        font-weight: 800;
        overflow-wrap: anywhere;
      }

      .proof-fact-detail {
        color: #718399;
        font-size: 11px;
        line-height: 1.4;
      }

      .proof-verdict {
        width: fit-content;
        padding: 8px 12px;
        border: 1px solid #55dce8;
        color: #83f1e5;
        font-size: 12px;
        font-weight: 950;
        letter-spacing: .14em;
      }

      .proof-verdict.blocked {
        border-color: #ee7897;
        color: #ffadc1;
      }

      @media (max-width: 800px) {
        .proof-causal-row {
          flex-wrap: wrap;
        }

        .proof-causal-arrow {
          transform: rotate(90deg);
        }

        .proof-node {
          width: min(250px, 70vw);
        }

        .proof-metric-row {
          grid-template-columns: 1fr;
        }

        .proof-fact-row {
          flex-direction: column;
          gap: 4px;
        }
      }

      @media (max-height: 760px) and (min-width: 900px) {
        header {
          padding-top: 7px !important;
          padding-bottom: 6px !important;
        }

        .release-shell.one-screen {
          height: calc(100vh - 86px) !important;
        }

        .one-screen-command {
          min-height: 110px;
        }

        .command-copy,
        .command-evidence,
        .command-actions {
          padding-top: 9px;
          padding-bottom: 9px;
        }
      }

      .one-screen-workflows {
        display: flex;
        align-items: stretch;
        gap: 4px;
        padding: 3px;
        border: 1px solid rgba(126, 146, 174, .21);
        background: rgba(4, 8, 14, .68);
      }

      .one-screen-workflow {
        min-height: 36px;
        padding: 0 13px;
        border: 1px solid transparent;
        color: #718399;
        font-size: 10px;
        font-weight: 850;
        letter-spacing: .02em;
        white-space: nowrap;
        transition:
          color .16s ease,
          border-color .16s ease,
          background .16s ease;
      }

      .one-screen-workflow.active {
        border-color: rgba(89, 214, 232, .55);
        background:
          linear-gradient(
            135deg,
            rgba(39, 121, 143, .17),
            rgba(7, 15, 25, .80)
          );
        color: #dffcff;
      }

      .one-screen-workflow:not(.active):hover {
        color: #bdc9d8;
        background: rgba(255, 255, 255, .025);
      }

      /*
       * Remove the permanent rail from the winning journey.
       * Its content remains available through technical proof.
       */
      .decision-rail {
        display: none !important;
      }

      main:has(> .decision-rail),
      main *:has(> .decision-rail) {
        grid-template-columns:
          minmax(0, 1fr) !important;
      }

      .release-shell.one-screen {
        grid-template-rows:
          minmax(0, 1fr)
          minmax(108px, auto) !important;
      }

      .release-shell.one-screen
      .manga-spread,
      .release-shell.one-screen
      .manga-stage {
        width: 100%;
        min-width: 0;
      }

      .one-screen-command {
        position: relative;
        z-index: 20;
        min-width: 0;
        display: grid;
        grid-template-columns:
          minmax(260px, 1.35fr)
          minmax(290px, .95fr)
          minmax(230px, .72fr);
        align-items: stretch;
        overflow: hidden;
        border-top: 2px solid rgba(89, 214, 232, .42);
        background:
          linear-gradient(
            100deg,
            rgba(7, 12, 21, .99),
            rgba(12, 21, 35, .98),
            rgba(6, 10, 18, .99)
          );
        box-shadow:
          0 -18px 45px rgba(0, 0, 0, .26);
      }

      .one-screen-command.observe {
        border-top-color:
          rgba(237, 181, 93, .56);
      }

      .one-screen-command.planned {
        border-top-color:
          rgba(169, 147, 232, .62);
      }

      .one-screen-command.working,
      .one-screen-command.verified {
        border-top-color:
          rgba(89, 214, 232, .66);
      }

      .one-screen-command.observe-danger,
      .one-screen-command.planned-danger,
      .one-screen-command.working-danger,
      .one-screen-command.blocked {
        border-top-color:
          rgba(235, 102, 130, .68);
      }

      .command-copy,
      .command-evidence,
      .command-actions {
        min-width: 0;
        padding: 13px 17px;
      }

      .command-copy {
        display: flex;
        flex-direction: column;
        justify-content: center;
        gap: 2px;
      }

      .command-evidence {
        display: flex;
        flex-direction: column;
        justify-content: center;
        gap: 7px;
        border-left: 1px solid var(--line);
        border-right: 1px solid var(--line);
      }

      .command-actions {
        display: flex;
        flex-direction: column;
        justify-content: center;
        gap: 7px;
      }

      .command-headline {
        color: #f5f7fa;
        font-size: clamp(17px, 1.32vw, 24px);
        font-weight: 950;
        line-height: 1.05;
        letter-spacing: -.025em;
      }

      .command-detail {
        max-width: 720px;
        color: #8798ad;
        font-size: 10px;
        line-height: 1.45;
      }

      .command-explanation {
        overflow: hidden;
        color: #697c93;
        font-size: 9px;
        line-height: 1.4;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .command-metrics {
        display: grid;
        grid-template-columns:
          repeat(3, minmax(0, 1fr));
        gap: 6px;
      }

      .command-metric {
        min-width: 0;
        padding: 7px 9px;
        border-left: 2px solid rgba(89, 214, 232, .72);
        background: rgba(19, 32, 51, .59);
      }

      .one-screen-command.planned
      .command-metric {
        border-left-color:
          rgba(169, 147, 232, .82);
      }

      .one-screen-command.blocked
      .command-metric {
        border-left-color:
          rgba(235, 102, 130, .84);
      }

      .command-lineage {
        overflow: hidden;
        color: #9cadc0;
        font-size: 8px;
        line-height: 1.35;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .command-sponsor-line {
        overflow: hidden;
        color: #587087;
        font-size: 8px;
        line-height: 1.35;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .command-verdict {
        width: fit-content;
        padding: 4px 8px;
        border: 1px solid rgba(89, 214, 232, .51);
        background: rgba(28, 153, 162, .09);
        color: #8bf0e3;
        font-size: 9px;
        font-weight: 950;
        letter-spacing: .13em;
      }

      .one-screen-command.blocked
      .command-verdict {
        border-color:
          rgba(235, 102, 130, .57);
        background:
          rgba(135, 26, 51, .11);
        color: #ffacc0;
      }

      .one-screen-primary {
        width: 100%;
        min-height: 44px;
        border: 1px solid rgba(89, 214, 232, .71);
        background:
          linear-gradient(
            100deg,
            rgba(41, 135, 161, .94),
            rgba(67, 153, 201, .91)
          );
        color: white;
        font-weight: 900;
      }

      .one-screen-command.blocked
      .one-screen-primary {
        border-color:
          rgba(235, 102, 130, .71);
        background:
          linear-gradient(
            100deg,
            rgba(126, 30, 53, .86),
            rgba(171, 51, 77, .88)
          );
      }

      .one-screen-proof {
        width: fit-content;
        align-self: center;
        color: #6caee0;
        font-size: 9px;
      }

      @media (max-width: 1050px) {
        .one-screen-command {
          grid-template-columns:
            minmax(240px, 1.15fr)
            minmax(260px, .92fr)
            minmax(200px, .70fr);
        }

        .one-screen-workflow {
          padding-left: 9px;
          padding-right: 9px;
        }
      }

      @media (max-width: 780px) {
        header {
          padding-top: 8px !important;
        }

        .one-screen-workflows {
          width: 100%;
          overflow-x: auto;
        }

        .one-screen-command {
          grid-template-columns: 1fr;
        }

        .command-evidence {
          border-left: 0;
          border-right: 0;
          border-top: 1px solid var(--line);
          border-bottom: 1px solid var(--line);
        }
      }

      .director-dialog {
        width: min(940px, calc(100vw - 34px));
        max-width: 940px;
        border: 1px solid var(--line);
        background:
          linear-gradient(
            145deg,
            #0e1726,
            #070b13
          );
      }

      .director-grid {
        display: grid;
        grid-template-columns:
          repeat(3, minmax(0, 1fr));
        gap: 10px;
      }

      .director-card {
        min-width: 0;
        min-height: 210px;
        display: flex;
        flex-direction: column;
        gap: 10px;
        padding: 17px;
        border: 1px solid var(--line);
        background:
          linear-gradient(
            160deg,
            rgba(20, 32, 52, .82),
            rgba(8, 13, 22, .88)
          );
        cursor: pointer;
        transition:
          transform .18s ease,
          border-color .18s ease,
          background .18s ease;
      }

      .director-card:hover {
        transform: translateY(-3px);
        border-color:
          rgba(89, 214, 232, .48);
        background:
          linear-gradient(
            160deg,
            rgba(26, 49, 67, .87),
            rgba(8, 13, 22, .92)
          );
      }

      .view-mode-button {
        min-height: 34px;
        color: #8fa0b6;
        font-size: 10px;
      }

      .focus-context-bar {
        min-width: 0;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 20px;
        padding: 9px 17px;
        overflow: hidden;
        border-top: 1px solid var(--line);
        background:
          linear-gradient(
            90deg,
            rgba(9, 15, 25, .98),
            rgba(14, 23, 37, .95)
          );
      }

      .focus-context-bar.observe {
        box-shadow:
          inset 0 2px 0 rgba(237, 181, 93, .31);
      }

      .focus-context-bar.planned {
        box-shadow:
          inset 0 2px 0 rgba(169, 147, 232, .38);
      }

      .focus-context-bar.working {
        box-shadow:
          inset 0 2px 0 rgba(89, 214, 232, .44);
      }

      .focus-context-bar.verified {
        box-shadow:
          inset 0 2px 0 rgba(89, 214, 232, .54);
      }

      .focus-context-bar.blocked {
        box-shadow:
          inset 0 2px 0 rgba(235, 102, 130, .55);
      }

      .panel-focus-stack {
        position: absolute;
        z-index: 8;
        right: 20px;
        top: 86px;
        align-items: flex-end;
        gap: 6px;
        pointer-events: none;
      }

      .manga-panel.right
      .panel-focus-stack {
        right: 22px;
      }

      .panel-focus-badge {
        width: fit-content;
        max-width: 230px;
        padding: 7px 10px;
        border: 1px solid rgba(89, 214, 232, .42);
        border-left: 3px solid var(--cyan);
        background: rgba(3, 7, 13, .88);
        color: #edf8fa;
        font-size: 9px;
        font-weight: 950;
        letter-spacing: .10em;
        box-shadow:
          0 8px 24px rgba(0, 0, 0, .32);
        backdrop-filter: blur(7px);
        animation:
          focus-badge-arrival .42s
          cubic-bezier(.2, .75, .25, 1)
          both;
      }

      .panel-focus-badge:nth-child(2) {
        animation-delay: .12s;
      }

      .panel-preserved
      .manga-image {
        filter:
          saturate(.56)
          brightness(.79)
          contrast(.95);
      }

      .panel-preserved
      .panel-focus-badge {
        border-color:
          rgba(89, 214, 232, .30);
        color: #a9f0f7;
      }

      .panel-observed {
        box-shadow:
          inset 0 0 0 3px
          rgba(237, 181, 93, .48);
      }

      .panel-observed
      .panel-focus-badge,
      .panel-affected
      .panel-focus-badge {
        border-color:
          rgba(237, 181, 93, .52);
        border-left-color: var(--amber);
        color: #ffe0a8;
      }

      .panel-affected {
        box-shadow:
          inset 0 0 0 3px
          rgba(237, 181, 93, .54),
          inset 0 -120px 100px
          rgba(116, 69, 13, .10);
      }

      .panel-working::before,
      .panel-working-danger::before {
        content: "";
        position: absolute;
        z-index: 7;
        inset: -20%;
        pointer-events: none;
        background:
          linear-gradient(
            110deg,
            transparent 39%,
            rgba(89, 214, 232, .20) 48%,
            rgba(255, 255, 255, .18) 50%,
            rgba(89, 214, 232, .15) 52%,
            transparent 61%
          );
        transform: translateX(-90%);
        animation:
          execution-sweep 1.05s
          cubic-bezier(.2, .75, .25, 1)
          forwards;
      }

      .panel-working {
        box-shadow:
          inset 0 0 0 3px
          rgba(89, 214, 232, .52);
      }

      .panel-working-danger,
      .panel-affected-danger {
        box-shadow:
          inset 0 0 0 3px
          rgba(235, 102, 130, .57);
      }

      .panel-working-danger
      .panel-focus-badge,
      .panel-affected-danger
      .panel-focus-badge,
      .panel-blocked-focus
      .panel-focus-badge {
        border-color:
          rgba(235, 102, 130, .55);
        border-left-color: var(--rose);
        color: #ffd8e0;
      }

      .panel-verified {
        box-shadow:
          inset 0 0 0 3px
          rgba(89, 214, 232, .48);
      }

      .panel-verified
      .panel-focus-badge {
        color: #aff5f8;
      }

      .panel-blocked-focus {
        box-shadow:
          inset 0 0 0 4px
          rgba(235, 102, 130, .64);
      }

      .why-dialog {
        width: min(700px, calc(100vw - 34px));
        max-width: 700px;
        border: 1px solid var(--line);
        background: #0b111d;
      }

      .why-row {
        display: grid;
        grid-template-columns:
          minmax(120px, .72fr)
          minmax(0, 1.28fr)
          auto;
        gap: 12px;
        align-items: center;
        padding: 11px 0;
        border-bottom: 1px solid var(--line);
      }

      @keyframes focus-badge-arrival {
        from {
          opacity: 0;
          transform: translateX(18px);
        }

        to {
          opacity: 1;
          transform: translateX(0);
        }
      }

      @keyframes execution-sweep {
        from {
          transform: translateX(-90%);
        }

        to {
          transform: translateX(90%);
        }
      }

      .scenario-tag {
        width: fit-content;
        padding: 5px 8px;
        border: 1px solid rgba(89, 214, 232, .28);
        background: rgba(89, 214, 232, .06);
        color: #79e1ef;
        font-size: 8px;
        font-weight: 950;
        letter-spacing: .14em;
        white-space: nowrap;
      }

      .lineage-ribbon {
        min-width: 0;
        display: grid;
        grid-template-columns:
          minmax(150px, .85fr)
          minmax(190px, 1.15fr)
          minmax(180px, 1fr);
        align-items: stretch;
        overflow: hidden;
        border-top: 1px solid var(--line);
        background:
          linear-gradient(
            90deg,
            rgba(10, 15, 25, .98),
            rgba(15, 24, 39, .92),
            rgba(9, 14, 23, .98)
          );
      }

      .lineage-step {
        min-width: 0;
        display: flex;
        flex-direction: column;
        justify-content: center;
        gap: 2px;
        padding: 9px 15px;
      }

      .lineage-movement {
        position: relative;
        min-width: 0;
        border-left: 1px solid var(--line);
        border-right: 1px solid var(--line);
      }

      .lineage-movement::before,
      .lineage-movement::after {
        content: "";
        position: absolute;
        top: 50%;
        width: 15px;
        height: 1px;
        background: rgba(89, 214, 232, .58);
      }

      .lineage-movement::before {
        left: 0;
      }

      .lineage-movement::after {
        right: 0;
      }

      .lineage-ribbon.warning {
        box-shadow:
          inset 0 2px 0 rgba(237, 181, 93, .34);
      }

      .lineage-ribbon.planned {
        box-shadow:
          inset 0 2px 0 rgba(169, 147, 232, .38);
      }

      .lineage-ribbon.verified {
        box-shadow:
          inset 0 2px 0 rgba(89, 214, 232, .42);
      }

      .lineage-ribbon.blocked {
        box-shadow:
          inset 0 2px 0 rgba(235, 102, 130, .52);
      }

      .final-receipt {
        position: relative;
        overflow: hidden;
        padding: 13px;
        border: 1px solid rgba(89, 214, 232, .28);
        background:
          linear-gradient(
            135deg,
            rgba(27, 113, 129, .13),
            rgba(8, 13, 22, .76)
          );
      }

      .final-receipt.blocked {
        border-color: rgba(235, 102, 130, .38);
        background:
          linear-gradient(
            135deg,
            rgba(130, 24, 50, .15),
            rgba(8, 13, 22, .76)
          );
      }

      .final-receipt::after {
        content: "VERIFIED";
        position: absolute;
        right: -11px;
        bottom: 2px;
        color: rgba(89, 214, 232, .06);
        font-size: 31px;
        font-weight: 950;
        letter-spacing: .08em;
        transform: rotate(-7deg);
        pointer-events: none;
      }

      .final-receipt.blocked::after {
        content: "BLOCKED";
        color: rgba(235, 102, 130, .08);
      }

      .receipt-id {
        padding: 6px 8px;
        border-left: 2px solid rgba(89, 214, 232, .48);
        background: rgba(3, 6, 11, .45);
      }

      .sponsor-strip {
        display: grid;
        grid-template-columns:
          repeat(3, minmax(0, 1fr));
        min-height: 0;
        border-top: 1px solid var(--line);
        background: #070a10;
      }

      .sponsor-cell {
        min-width: 0;
        display: flex;
        flex-direction: column;
        justify-content: center;
        gap: 2px;
        padding: 9px 16px;
        border-right: 1px solid var(--line);
      }

      .sponsor-cell:last-child {
        border-right: 0;
      }

      .proof-dialog,
      .media-dialog {
        width: min(
          1120px,
          calc(100vw - 38px)
        );
        max-width: 1120px;
        max-height: 88vh;
        overflow-y: auto;
        border: 1px solid var(--line);
        background: #0a101b;
      }

      .media-grid {
        display: grid;
        grid-template-columns:
          repeat(2, minmax(0, 1fr));
        gap: 13px;
      }

      .media-card {
        min-width: 0;
        border: 1px solid var(--line);
        background: #070b12;
      }

      .release-video {
        width: 100%;
        aspect-ratio: 16 / 9;
      }

      .mono {
        font-family:
          ui-monospace,
          SFMono-Regular,
          Menlo,
          Monaco,
          Consolas,
          monospace;
        overflow-wrap: anywhere;
      }

      @keyframes panel-arrival {
        from {
          opacity: .64;
          transform: scale(1.065);
          filter: contrast(.75);
        }

        to {
          opacity: 1;
          transform: scale(1.025);
          filter: contrast(1);
        }
      }

      @keyframes causal-trace {
        from {
          transform: translateX(-110%);
        }

        to {
          transform: translateX(110%);
        }
      }

      @keyframes cause-reveal {
        to {
          opacity: 1;
          transform: translateY(0);
        }
      }

      @media (max-width: 1000px) {
        body {
          overflow-y: auto;
        }

        .app-shell {
          width: min(100% - 18px, 1460px);
          height: auto;
          min-height: 100vh;
        }

        .release-shell {
          grid-template-rows:
            auto
            auto
            auto;
        }

        .main-grid {
          grid-template-columns: 1fr;
        }

        .spread-stage {
          min-height: 570px;
          border-right: 0;
          border-bottom: 1px solid var(--line);
        }

        .decision-rail {
          min-height: 545px;
        }
      }

      @media (max-width: 700px) {
        .director-grid {
          grid-template-columns: 1fr;
        }

        .why-row {
          grid-template-columns: 1fr;
          gap: 4px;
        }

        .media-grid {
          grid-template-columns: 1fr;
        }

        .causal-map {
          grid-template-columns: 1fr;
        }

        .cause-line {
          width: 2px;
          height: 20px;
          margin: 0 auto;
        }

        .diff-grid {
          grid-template-columns: 1fr;
        }

        .diff-arrow {
          transform: rotate(90deg);
        }

        .story-strip {
          left: 13px;
          right: 13px;
          grid-template-columns: 1fr;
        }

        .story-meta {
          display: none;
        }

        .sponsor-strip {
          grid-template-columns: 1fr;
        }

        .sponsor-cell {
          border-right: 0;
          border-bottom: 1px solid var(--line);
        }
      }

      @media (prefers-reduced-motion: reduce) {
        .manga-image,
        .cause-line::after,
        .asset-stack .cause-node {
          animation: none !important;
          opacity: 1 !important;
          transform: none !important;
        }
      }
    </style>
    """,
    shared=True,
)


def proof_row(
    label: str,
    value: Any,
) -> None:
    with ui.row().classes(
        "w-full items-start justify-between "
        "gap-5 py-2 border-b border-slate-800"
    ):
        ui.label(label).classes(
            "text-xs text-slate-500"
        )

        ui.label(str(value)).classes(
            "mono max-w-[70%] text-right "
            "text-xs text-slate-200"
        )



def build_dialogue_evidence_bundle() -> dict[str, Any]:
    """Return the canonical recorded dialogue-release comparison."""
    return {
        "mode": "VERIFIED_GENBLAZE_EVIDENCE",
        "status": "VERIFIED GENBLAZE CASE",
        "reason": (
            "Canonical release evidence replay. "
            "Direct B2 playback is demonstrated by Visual revision."
        ),
        "previous_release_id": "baseline-v1",
        "release_id": "shared-dialogue-v2",
        "expires_in_seconds": None,
        "previous": {
            "label": "Original shared line",
            "url": (
                "/release-media/"
                "shared_dialogue_before.mp4"
            ),
            "sha256": None,
            "size_bytes": None,
            "media_type": "video/mp4",
            "remote_verified": False,
            "object_key": None,
        },
        "current": {
            "label": "Verified rebuilt line",
            "url": (
                "/release-media/"
                "shared_dialogue_after.mp4"
            ),
            "sha256": None,
            "size_bytes": None,
            "media_type": "video/mp4",
            "remote_verified": False,
            "object_key": None,
        },
    }



def _panel_text_values(
    value: Any,
) -> list[str]:
    """Flatten creator-facing panel evidence into normalized text."""
    if isinstance(value, str):
        return [
            value.upper()
        ]

    if isinstance(value, dict):
        values: list[str] = []

        for item in value.values():
            values.extend(
                _panel_text_values(item)
            )

        return values

    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):
        values = []

        for item in value:
            values.extend(
                _panel_text_values(item)
            )

        return values

    return []


def _precise_panel_status(
    panel: dict[str, Any],
    *,
    key: str,
) -> str:
    """Clarify preview-only rebuilds without workflow coupling."""
    raw_status = str(
        panel.get(
            key,
            "",
        )
    ).strip()

    evidence = " | ".join(
        _panel_text_values(
            panel
        )
    )

    preview_rebuild = (
        "PREVIEW" in evidence
        and "REBUILD" in evidence
    )

    artwork_preserved = (
        "ARTWORK" in evidence
        and "PRESERVE" in evidence
    )

    if (
        raw_status == "REBUILD"
        and preview_rebuild
        and artwork_preserved
    ):
        return "PREVIEW REBUILD"

    return raw_status


def render_panel(
    panel: dict[str, str],
    *,
    position: str,
    number: str,
    focus_class: str = "",
    focus_badges: list[str] | None = None,
    media_bundle: dict[str, Any] | None = None,
    media_tab: str = "current",
    media_loading: bool = False,
    on_media_tab: Any = None,
    on_media_close: Any = None,
) -> None:
    badges = focus_badges or []

    with ui.element("article").classes(
        f"manga-panel {position} "
        f"{panel['tone']} {focus_class}"
    ):
        if (
            position == "right"
            and media_loading
        ):
            with ui.column().classes(
                "panel-media-overlay "
                "items-center justify-center gap-3"
            ):
                ui.spinner(
                    size="xl",
                    color="cyan",
                )

                ui.label(
                    "VERIFYING B2 MEDIA"
                ).classes(
                    "text-xs font-black "
                    "tracking-[0.16em] "
                    "text-cyan-300"
                )

                ui.label(
                    "Retrieving and hashing both "
                    "release previews before playback."
                ).classes(
                    "max-w-[420px] text-center "
                    "text-[10px] text-slate-400"
                )

        elif (
            position == "right"
            and media_bundle is not None
        ):
            selected = media_bundle[
                media_tab
            ]

            verified_mode = (
                media_bundle["mode"]
                == "VERIFIED_B2_PLAYBACK"
            )

            evidence_mode = (
                media_bundle["mode"]
                == "VERIFIED_GENBLAZE_EVIDENCE"
            )

            with ui.column().classes(
                "panel-media-overlay gap-3"
            ):
                with ui.row().classes(
                    "w-full items-start "
                    "justify-between gap-3"
                ):
                    with ui.column().classes(
                        "gap-0 min-w-0"
                    ):
                        ui.label(
                            (
                                "VERIFIED B2 MEDIA"
                                if verified_mode
                                else (
                                    "VERIFIED GENBLAZE CASE"
                                    if evidence_mode
                                    else
                                    "LOCAL PRESENTATION FALLBACK"
                                )
                            )
                        ).classes(
                            (
                                "text-[9px] font-black "
                                "tracking-[0.16em] "
                                "text-cyan-300"
                                if verified_mode
                                else
                                "text-[9px] font-black "
                                "tracking-[0.16em] "
                                "text-amber-300"
                            )
                        )

                        ui.label(
                            (
                                "Compiled Ending B route"
                                if verified_mode
                                else (
                                    "Shared dialogue release evidence"
                                    if evidence_mode
                                    else
                                    "Remote playback unavailable"
                                )
                            )
                        ).classes(
                            "text-base font-black text-white"
                        )

                    ui.button(
                        icon="close",
                        on_click=on_media_close,
                    ).props(
                        "flat round dense"
                    )

                with ui.row().classes(
                    "media-tab-row"
                ):
                    for tab_id, label in (
                        (
                            "previous",
                            "Before revision",
                        ),
                        (
                            "current",
                            "Verified release",
                        ),
                    ):
                        ui.button(
                            label,
                            on_click=lambda
                            selected_tab=tab_id: (
                                on_media_tab(
                                    selected_tab
                                )
                            ),
                        ).props(
                            "flat dense no-caps"
                        ).classes(
                            "media-tab"
                            + (
                                " active"
                                if media_tab
                                == tab_id
                                else ""
                            )
                        )

                ui.video(
                    selected["url"]
                ).props(
                    "controls playsinline "
                    "preload=metadata"
                ).classes(
                    "verified-panel-video"
                )

                if verified_mode:
                    with ui.row().classes(
                        "w-full items-center "
                        "justify-between gap-3"
                    ):
                        ui.label(
                            "SERVED FROM B2 · "
                            "SHA-256 VERIFIED · "
                            "5-MINUTE URL"
                        ).classes(
                            "text-[10px] font-black "
                            "tracking-[0.10em] "
                            "text-emerald-300"
                        )

                        ui.label(
                            selected["sha256"][:16]
                            + "…"
                        ).classes(
                            "mono text-[10px] "
                            "text-slate-400"
                        )

                elif evidence_mode:
                    ui.label(
                        "VERIFIED GENBLAZE RELEASE EVIDENCE"
                    ).classes(
                        "text-[10px] font-black "
                        "tracking-[0.10em] "
                        "text-cyan-300"
                    )

                    ui.label(
                        media_bundle["reason"]
                    ).classes(
                        "text-[10px] leading-relaxed "
                        "text-slate-400"
                    )

                else:
                    ui.label(
                        media_bundle["reason"]
                    ).classes(
                        "text-[10px] leading-relaxed "
                        "text-amber-200"
                    )

                    ui.label(
                        "This video is a local presentation "
                        "copy and is not being represented "
                        "as direct B2 playback."
                    ).classes(
                        "text-[10px] leading-relaxed "
                        "text-slate-400"
                    )
        ui.image(
            panel["image"]
        ).props(
            "fit=cover"
        ).classes(
            "manga-image"
        )

        with ui.column().classes(
            "panel-heading"
        ):
            ui.label(
                panel["label"]
            ).classes(
                "panel-label"
            )

            ui.label(
                _precise_panel_status(
                    panel,
                    key="status",
                )
            ).classes(
                "panel-status"
            )

        if badges:
            with ui.column().classes(
                "panel-focus-stack"
            ):
                for badge in badges:
                    ui.label(
                        badge
                    ).classes(
                        "panel-focus-badge"
                    )

        ui.label(number).classes(
            "panel-number"
        )


def render_metric(
    metric: dict[str, str],
) -> None:
    with ui.column().classes(
        "metric gap-0"
    ):
        ui.label(
            metric["label"]
        ).classes(
            "text-[8px] font-black "
            "tracking-[0.15em] text-slate-500"
        )

        ui.label(
            metric["value"]
        ).classes(
            "text-2xl font-black text-white"
        )

        ui.label(
            metric["detail"]
        ).classes(
            "text-[9px] text-slate-500"
        )


def render_revision_diff(
    revision: dict[str, Any],
) -> None:
    with ui.column().classes(
        "revision-summary gap-1"
    ):
        ui.label(
            revision["subject"].upper()
        ).classes(
            "text-[9px] font-black "
            "tracking-[0.16em] text-amber-300"
        )

        ui.label(
            revision["summary"]
        ).classes(
            "text-xs leading-relaxed text-slate-300"
        )

    with ui.element("div").classes(
        "diff-grid"
    ):
        with ui.column().classes(
            "diff-card gap-1"
        ):
            ui.label(
                "BEFORE"
            ).classes(
                "text-[8px] font-black "
                "tracking-[0.15em] text-slate-600"
            )

            ui.label(
                revision["before"]
            ).classes(
                "text-xs font-bold "
                "leading-relaxed text-slate-300"
            )

        ui.label("→").classes(
            "diff-arrow"
        )

        with ui.column().classes(
            "diff-card after gap-1"
        ):
            ui.label(
                "AFTER"
            ).classes(
                "text-[8px] font-black "
                "tracking-[0.15em] text-cyan-400"
            )

            ui.label(
                revision["after"]
            ).classes(
                "text-xs font-bold "
                "leading-relaxed text-white"
            )


def render_causal_map(
    causal: dict[str, Any],
) -> None:
    asset_nodes = "".join(
        (
            '<div class="cause-node">'
            f"{escape(asset)}"
            "</div>"
        )
        for asset in causal["assets"]
    )

    ui.html(
        f"""
        <div class="causal-map animate">
          <div class="cause-node source">
            {escape(causal["source"])}
          </div>

          <div class="cause-line"></div>

          <div class="asset-stack">
            {asset_nodes}
          </div>

          <div class="cause-line"></div>

          <div class="cause-node destination">
            {escape(causal["destination"])}
          </div>
        </div>
        """,
        sanitize=False,
    )

    with ui.column().classes(
        "causal-result gap-0"
    ):
        ui.label(
            causal["result"]
        ).classes(
            "text-xs font-black text-white"
        )

        ui.label(
            causal["preserved"]
        ).classes(
            "text-[10px] text-emerald-300"
        )


def render_stages(
    stages: list[dict[str, str]],
    *,
    completed: set[str],
    active_stage: str | None,
) -> None:
    with ui.column().classes(
        "stage-list w-full"
    ):
        for stage in stages:
            stage_id = stage["id"]

            if stage_id in completed:
                tone = "complete"
                icon_name = "check_circle"
                icon_class = "text-cyan-300"

            elif stage_id == active_stage:
                tone = "active"
                icon_name = "pending"
                icon_class = "text-amber-300"

            else:
                tone = "pending"
                icon_name = "radio_button_unchecked"
                icon_class = "text-slate-600"

            with ui.element("div").classes(
                f"stage-row {tone}"
            ):
                ui.icon(
                    icon_name
                ).classes(
                    f"text-lg {icon_class}"
                )

                with ui.column().classes(
                    "gap-0"
                ):
                    ui.label(
                        stage["label"]
                    ).classes(
                        "text-xs font-bold text-white"
                    )

                    ui.label(
                        stage["detail"]
                    ).classes(
                        "text-[10px] leading-relaxed "
                        "text-slate-500"
                    )


def mode_label(
    *,
    phase: str,
    busy: bool,
    analysis: dict[str, Any] | None,
    execution_mode: str | None,
) -> str:
    if execution_mode == "LIVE_EXECUTION":
        if busy:
            return "LIVE B2 EXECUTION IN PROGRESS"

        if phase == COMPLETE:
            return "LIVE EXECUTION · REMOTE VERIFIED"

    if execution_mode == "VERIFIED_REPLAY_FALLBACK":
        return "VERIFIED REPLAY FALLBACK"

    if busy:
        return (
            "VERIFIED EXECUTION REPLAY IN PROGRESS"
        )

    if phase == COMPLETE:
        return (
            "VERIFIED EVIDENCE · REMOTE CHECKED"
        )

    if analysis is not None:
        return (
            "LIVE ANALYSIS · VERIFIED EXECUTION REPLAY"
        )

    return (
        "LIVE ANALYSIS READY · VERIFIED EXECUTION REPLAY"
    )


def render_workflow_segments(
    *,
    scenario_id: str,
    on_select: Any,
    disabled: bool,
) -> None:
    with ui.row().classes(
        "one-screen-workflows"
    ):
        for option in workflow_options():
            active = (
                option["id"]
                == scenario_id
            )

            button = ui.button(
                option["label"],
                icon=option["icon"],
                on_click=lambda
                selected=option["id"]: (
                    on_select(selected)
                ),
            ).props(
                "flat dense no-caps"
            ).classes(
                "one-screen-workflow"
                + (
                    " active"
                    if active
                    else ""
                )
            )

            button.tooltip(
                option["description"]
            )

            if disabled:
                button.props(
                    "disable"
                )


def render_one_screen_command(
    *,
    command: dict[str, Any],
    on_primary: Any,
    on_proof: Any,
    disabled: bool,
) -> None:
    with ui.element("section").classes(
        "one-screen-command "
        + command["tone"]
    ):
        director_cut = command.get(
            "director_cut"
        ) or {}
        replay_callback = command.get(
            "on_replay"
        )
        next_workflow_callback = command.get(
            "on_next_workflow"
        )

        if director_cut:
            render_director_release_rail(
                director_cut["rail"]
            )

        with ui.column().classes(
            "command-copy"
        ):
            if director_cut:
                render_director_change(
                    director_cut["change"]
                )

            ui.label(
                command["step"]
            ).classes(
                "text-[8px] font-black "
                "tracking-[0.17em] text-cyan-300"
            )

            ui.label(
                command["headline"]
            ).classes(
                "command-headline"
            )

            ui.label(
                command["detail"]
            ).classes(
                "command-detail"
            )

            if command["explanation"]:
                ui.label(
                    command["explanation"]
                ).classes(
                    "command-explanation"
                )

        with ui.column().classes(
            "command-evidence"
        ):
            if command["verdict"]:
                ui.label(
                    command["verdict"]
                ).classes(
                    "command-verdict"
                )

            if command["metrics"]:
                with ui.element("div").classes(
                    "command-metrics"
                ):
                    for metric in command[
                        "metrics"
                    ]:
                        with ui.column().classes(
                            "command-metric gap-0"
                        ):
                            ui.label(
                                metric["label"]
                            ).classes(
                                "text-[7px] font-black "
                                "tracking-[0.13em] "
                                "text-slate-600"
                            )

                            ui.label(
                                metric["value"]
                            ).classes(
                                "text-lg font-black "
                                "leading-none text-white"
                            )

            if command["lineage"]:
                ui.label(
                    command["lineage"]
                ).classes(
                    "command-lineage mono"
                )

            if director_cut:
                render_director_proof_cells(
                    director_cut[
                        "proof_cells"
                    ]
                )
            elif command["sponsor_line"]:
                ui.label(
                    command["sponsor_line"]
                ).classes(
                    "command-sponsor-line"
                )

        with ui.column().classes(
            "command-actions"
        ):
            primary = ui.button(
                command["primary_label"],
                on_click=on_primary,
            ).props(
                "unelevated no-caps"
            ).classes(
                "one-screen-primary"
            )

            if (
                disabled
                or command["primary_kind"]
                == "disabled"
            ):
                primary.props(
                    "disable loading"
                )

            ui.button(
                "Technical proof",
                icon="fact_check",
                on_click=on_proof,
            ).props(
                "flat dense no-caps"
            ).classes(
                "one-screen-proof"
            )

            if (
                director_cut
                and director_cut.get(
                    "next_workflow"
                )
                and next_workflow_callback
                and not disabled
            ):
                next_action = director_cut[
                    "next_workflow"
                ]

                ui.button(
                    next_action["label"],
                    icon="arrow_forward",
                    on_click=lambda target=(
                        next_action[
                            "scenario_id"
                        ]
                    ): next_workflow_callback(
                        target
                    ),
                ).props(
                    "unelevated no-caps"
                ).classes(
                    "director-next"
                )

            if (
                director_cut
                and director_cut.get(
                    "replay"
                )
                and replay_callback
                and not disabled
            ):
                ui.button(
                    director_cut[
                        "replay"
                    ]["label"],
                    icon="replay",
                    on_click=replay_callback,
                ).props(
                    "flat dense no-caps"
                ).classes(
                    "director-replay"
                )



def render_director_release_rail(
    rail: list[dict[str, str]],
) -> None:
    """Render the six-stage release progression."""
    marks = {
        "done": "✓",
        "active": "●",
        "pending": "○",
        "blocked": "×",
        "skipped": "—",
    }

    with ui.element("div").classes(
        "director-rail"
    ):
        for index, stage in enumerate(
            rail
        ):
            with ui.element("div").classes(
                "director-stage "
                + stage["status"]
            ):
                ui.label(
                    stage["label"]
                ).classes(
                    "director-stage-label"
                )

                ui.label(
                    marks[
                        stage["status"]
                    ]
                ).classes(
                    "director-stage-mark"
                )

            if index < len(rail) - 1:
                ui.label(
                    "→"
                ).classes(
                    "director-stage-arrow"
                )


def render_director_change(
    change: dict[str, str],
) -> None:
    """Expose the exact creator-visible change."""
    with ui.column().classes(
        "director-change gap-0"
    ):
        with ui.row().classes(
            "w-full items-center "
            "justify-between gap-3"
        ):
            ui.label(
                change["eyebrow"]
            ).classes(
                "director-change-eyebrow"
            )

            ui.label(
                change["subject"]
            ).classes(
                "director-change-subject"
            )

        with ui.element("div").classes(
            "director-change-flow"
        ):
            with ui.column().classes(
                "director-change-side gap-0"
            ):
                ui.label(
                    change["before_label"]
                ).classes(
                    "director-change-label"
                )

                ui.label(
                    change["before"]
                ).classes(
                    "director-change-value before"
                )

            ui.label(
                "→"
            ).classes(
                "director-change-arrow"
            )

            with ui.column().classes(
                "director-change-side gap-0"
            ):
                ui.label(
                    change["after_label"]
                ).classes(
                    "director-change-label"
                )

                ui.label(
                    change["after"]
                ).classes(
                    "director-change-value after"
                )

        ui.label(
            change["impact"]
        ).classes(
            "director-change-impact"
        )


def render_director_proof_cells(
    proof_cells: list[dict[str, str]],
) -> None:
    """Render Genblaze, B2, and Branchline proof cells."""
    with ui.element("div").classes(
        "director-proof-grid"
    ):
        for cell in proof_cells:
            with ui.column().classes(
                "director-proof-cell gap-0 "
                + cell["tone"]
            ):
                ui.label(
                    cell["label"]
                ).classes(
                    "director-proof-label"
                )

                ui.label(
                    cell["value"]
                ).classes(
                    "director-proof-value"
                )

                ui.label(
                    cell["detail"]
                ).classes(
                    "director-proof-detail"
                )


def render_focus_bar(
    context: dict[str, str],
) -> None:
    with ui.element("section").classes(
        "focus-context-bar "
        + context["tone"]
    ):
        with ui.column().classes(
            "gap-0 min-w-0"
        ):
            ui.label(
                context["label"]
            ).classes(
                "text-[8px] font-black "
                "tracking-[0.17em] text-cyan-300"
            )

            ui.label(
                context["value"]
            ).classes(
                "truncate text-sm font-black text-white"
            )

        ui.label(
            context["detail"]
        ).classes(
            "truncate text-[10px] text-slate-500"
        )


def render_lineage_ribbon(
    lineage: dict[str, str],
) -> None:
    with ui.element("section").classes(
        "lineage-ribbon "
        + lineage["tone"]
    ):
        with ui.column().classes(
            "lineage-step gap-0"
        ):
            ui.label(
                "PREVIOUS RELEASE"
            ).classes(
                "text-[8px] font-black "
                "tracking-[0.16em] text-slate-600"
            )

            ui.label(
                lineage["source"]
            ).classes(
                "mono truncate text-xs "
                "font-bold text-slate-200"
            )

        with ui.column().classes(
            "lineage-step lineage-movement "
            "items-center gap-0 text-center"
        ):
            ui.label(
                lineage["eyebrow"]
            ).classes(
                "text-[8px] font-black "
                "tracking-[0.16em] text-cyan-300"
            )

            ui.label(
                lineage["movement"]
            ).classes(
                "text-xs font-black text-white"
            )

            ui.label(
                lineage["caption"]
            ).classes(
                "max-w-[520px] truncate "
                "text-[9px] text-slate-500"
            )

        with ui.column().classes(
            "lineage-step gap-0"
        ):
            ui.label(
                "CURRENT RELEASE"
            ).classes(
                "text-[8px] font-black "
                "tracking-[0.16em] text-slate-600"
            )

            ui.label(
                lineage["target"]
            ).classes(
                "mono truncate text-xs "
                "font-bold text-white"
            )


def render_final_receipt(
    receipt: dict[str, Any] | None,
) -> None:
    if receipt is None:
        return

    with ui.column().classes(
        "final-receipt "
        + receipt["tone"]
        + " gap-2"
    ):
        with ui.row().classes(
            "w-full items-start justify-between gap-3"
        ):
            with ui.column().classes(
                "gap-0"
            ):
                ui.label(
                    receipt["eyebrow"]
                ).classes(
                    "text-[8px] font-black "
                    "tracking-[0.17em] text-cyan-300"
                )

                ui.label(
                    receipt["title"]
                ).classes(
                    "text-sm font-black text-white"
                )

            ui.label(
                receipt["status"]
            ).classes(
                "text-[9px] font-black "
                "tracking-[0.12em] text-emerald-300"
            )

        ui.label(
            receipt["line_one"]
        ).classes(
            "text-[10px] leading-relaxed text-slate-300"
        )

        ui.label(
            receipt["line_two"]
        ).classes(
            "text-[10px] leading-relaxed text-slate-400"
        )

        with ui.column().classes(
            "receipt-id w-full gap-0"
        ):
            ui.label(
                "RELEASE"
            ).classes(
                "text-[7px] font-black "
                "tracking-[0.15em] text-slate-600"
            )

            ui.label(
                receipt["release_id"]
            ).classes(
                "mono truncate text-[9px] text-slate-300"
            )

            if receipt["approval_id"]:
                ui.label(
                    "Approval "
                    + receipt["approval_id"]
                ).classes(
                    "mono truncate text-[8px] text-slate-600"
                )

        ui.label(
            receipt["storage"]
        ).classes(
            "text-[9px] leading-relaxed text-slate-500"
        )


@ui.page("/")
def index() -> None:
    ui.dark_mode().enable()

    state: dict[str, Any] = {
        "scenario_id": "scenario_a",
        "phase": READY,
        "analysis": None,
        "analysis_error": None,
        "stage_error": None,
        "busy": False,
        "completed_stages": [],
        "active_stage": None,
        "execution_mode": None,
        "execution_result": None,
        "live_stage_detail": None,
        "fallback_reason": None,
        "proof_mode": False,
        "verified_media": None,
        "verified_media_tab": "current",
        "verified_media_loading": False,
    }

    def reset_execution_state() -> None:
        state["analysis_error"] = None
        state["stage_error"] = None
        state["busy"] = False
        state["completed_stages"] = []
        state["active_stage"] = None
        state["execution_mode"] = None
        state["execution_result"] = None
        state["live_stage_detail"] = None
        state["fallback_reason"] = None
        state["verified_media"] = None
        state["verified_media_tab"] = "current"
        state["verified_media_loading"] = False

    def choose_scenario(
        scenario_id: str,
    ) -> None:
        if state["busy"]:
            return

        state["scenario_id"] = scenario_id
        state["phase"] = READY
        state["analysis"] = None

        reset_execution_state()
        screen.refresh()

    def set_proof_mode(
        enabled: bool,
    ) -> None:
        if state["busy"]:
            return

        state["proof_mode"] = enabled
        screen.refresh()

    def set_verified_media_tab(
        tab: str,
    ) -> None:
        if tab not in {
            "previous",
            "current",
        }:
            return

        state["verified_media_tab"] = tab
        screen.refresh()

    def close_verified_media() -> None:
        state["verified_media"] = None
        state["verified_media_tab"] = "current"
        screen.refresh()

    async def open_dialogue_media() -> None:
        if state["verified_media_loading"]:
            return

        state["verified_media_loading"] = True
        state["verified_media"] = None

        await screen.refresh()

        state["verified_media"] = (
            build_dialogue_evidence_bundle()
        )
        state["verified_media_tab"] = "current"
        state["verified_media_loading"] = False

        await screen.refresh()

    async def open_verified_media() -> None:
        if state[
            "verified_media_loading"
        ]:
            return

        state[
            "verified_media_loading"
        ] = True

        state["verified_media"] = None

        await screen.refresh()

        current_release = None

        execution = state.get(
            "execution_result"
        )

        if isinstance(
            execution,
            dict,
        ):
            candidate = execution.get(
                "release"
            )

            if isinstance(
                candidate,
                dict,
            ):
                current_release = candidate

        try:
            bundle = await asyncio.to_thread(
                load_verified_media_bundle,
                current_release=current_release,
            )

        except VerifiedMediaError as exc:
            bundle = (
                local_presentation_fallback(
                    reason=str(exc),
                )
            )

        state["verified_media"] = bundle
        state["verified_media_tab"] = (
            "current"
        )
        state[
            "verified_media_loading"
        ] = False

        await screen.refresh()

    async def run_verified_replay(
        *,
        target_view: dict[str, Any],
    ) -> bool:
        stages = build_verified_replay_stages(
            state["scenario_id"]
        )

        state["busy"] = True
        state["stage_error"] = None
        state["completed_stages"] = []
        state["active_stage"] = None

        await screen.refresh()

        try:
            for stage in stages:
                state["active_stage"] = stage[
                    "id"
                ]

                await screen.refresh()

                validate_replay_stage(
                    stage,
                    scenario_id=state[
                        "scenario_id"
                    ],
                    scenario=target_view[
                        "scenario"
                    ],
                    analysis=state[
                        "analysis"
                    ],
                )

                # This delay presents verified stages clearly.
                # It is not described as execution duration.
                await asyncio.sleep(0.34)

                state[
                    "completed_stages"
                ].append(
                    stage["id"]
                )

                state["active_stage"] = None

                await screen.refresh()
                await asyncio.sleep(0.12)

        except RuntimeError as exc:
            state["stage_error"] = str(exc)
            state["active_stage"] = None
            state["busy"] = False

            await screen.refresh()
            return False

        state["busy"] = False
        state["active_stage"] = None
        return True

    async def run_live_scenario_b() -> bool:
        analysis = state["analysis"]

        if analysis is None:
            state["stage_error"] = (
                "Live execution requires a current dependency plan."
            )
            await screen.refresh()
            return False

        state["busy"] = True
        state["execution_mode"] = "LIVE_EXECUTION"
        state["execution_result"] = None
        state["fallback_reason"] = None
        state["stage_error"] = None
        state["live_stage_detail"] = (
            "Binding creator approval to the current plan…"
        )

        await screen.refresh()

        event_queue: asyncio.Queue[
            dict[str, str]
        ] = asyncio.Queue()

        loop = asyncio.get_running_loop()

        def receive_progress(
            event: dict[str, str],
        ) -> None:
            loop.call_soon_threadsafe(
                event_queue.put_nowait,
                event,
            )

        execution_task = asyncio.create_task(
            asyncio.to_thread(
                execute_scenario_b_release,
                analysis=analysis,
                approved_by=(
                    "interactive-release-operator"
                ),
                progress=receive_progress,
            )
        )

        while not execution_task.done():
            try:
                event = await asyncio.wait_for(
                    event_queue.get(),
                    timeout=0.20,
                )

            except TimeoutError:
                continue

            state["active_stage"] = event[
                "stage"
            ]

            state["live_stage_detail"] = event[
                "detail"
            ]

            await screen.refresh()

        while not event_queue.empty():
            event = event_queue.get_nowait()

            state["active_stage"] = event[
                "stage"
            ]

            state["live_stage_detail"] = event[
                "detail"
            ]

        try:
            result = await execution_task

        except (
            LiveExecutionUnavailable,
            LiveExecutionError,
        ) as exc:
            state["busy"] = False
            state["active_stage"] = None
            state["execution_mode"] = (
                "VERIFIED_REPLAY_FALLBACK"
            )
            state["fallback_reason"] = str(
                exc
            )
            state["live_stage_detail"] = None

            await screen.refresh()
            return False

        state["execution_result"] = result
        state["execution_mode"] = "LIVE_EXECUTION"
        state["busy"] = False
        state["active_stage"] = None
        state["live_stage_detail"] = (
            "Fresh release completed and independently verified."
        )

        await screen.refresh()
        return True

    async def advance() -> None:
        if state["busy"]:
            return

        scenario_id = state[
            "scenario_id"
        ]

        phase = state["phase"]

        if phase == COMPLETE:
            state["phase"] = READY
            state["analysis"] = None
            reset_execution_state()

            await screen.refresh()
            return

        if phase == READY:
            if scenario_id in {
                "scenario_a",
                "scenario_b",
            }:
                try:
                    analysis = (
                        analyze_story_revision(
                            scenario_id
                        )
                    )

                    planned_view = (
                        build_release_spread(
                            scenario_id,
                            PLANNED,
                        )
                    )

                    validate_analysis_against_release(
                        analysis,
                        planned_view[
                            "scenario"
                        ],
                    )

                    state["analysis"] = analysis
                    state["analysis_error"] = None
                    state["phase"] = PLANNED

                except LiveAnalysisError as exc:
                    state["analysis"] = None
                    state["analysis_error"] = str(
                        exc
                    )

                    await screen.refresh()
                    return

                await screen.refresh()
                return

            # Scenario C performs a real evidence check directly.
            complete_view = build_release_spread(
                scenario_id,
                COMPLETE,
            )

            succeeded = await run_verified_replay(
                target_view=complete_view
            )

            if succeeded:
                state["phase"] = COMPLETE
                await screen.refresh()

            return

        if phase == PLANNED:
            complete_view = build_release_spread(
                scenario_id,
                COMPLETE,
            )

            if scenario_id == "scenario_b":
                succeeded = (
                    await run_live_scenario_b()
                )

                if succeeded:
                    state["phase"] = COMPLETE
                    await screen.refresh()
                    return

                # Honest judging fallback: never label replay as live.
                succeeded = await run_verified_replay(
                    target_view=complete_view
                )

            else:
                succeeded = await run_verified_replay(
                    target_view=complete_view
                )

            if succeeded:
                state["phase"] = COMPLETE
                await screen.refresh()

    @ui.refreshable
    def screen() -> None:
        scenario_id = state[
            "scenario_id"
        ]

        phase = state["phase"]

        view = build_release_spread(
            scenario_id,
            phase,
        )

        scenario = view["scenario"]
        proof = scenario["provenance"]

        analysis = state["analysis"]
        execution = state["execution_result"]

        revision = build_revision_story(
            scenario_id,
            analysis,
        )

        causal = build_causal_route(
            scenario_id
        )

        comparison = media_comparison(
            scenario_id
        )

        replay_stages = (
            build_verified_replay_stages(
                scenario_id
            )
        )

        final_third = build_final_third_context(
            scenario_id=scenario_id,
            phase=phase,
            scenario=scenario,
            analysis=analysis,
            execution=execution,
        )

        focus = build_focus_experience(
            scenario_id=scenario_id,
            phase=phase,
            busy=state["busy"],
            proof_mode=state["proof_mode"],
            execution_mode=state[
                "execution_mode"
            ],
            active_stage=state[
                "active_stage"
            ],
        )

        one_screen = build_one_screen_command(
            scenario_id=scenario_id,
            phase=phase,
            busy=state["busy"],
            active_stage=state[
                "active_stage"
            ],
            analysis=analysis,
            execution=execution,
        )
        one_screen["director_cut"] = build_director_cut(
            scenario_id=scenario_id,
            phase=phase,
            busy=state["busy"],
            active_stage=state[
                "active_stage"
            ],
        )
        one_screen["on_replay"] = advance
        one_screen[
            "on_next_workflow"
        ] = choose_scenario


        if (
            state["verified_media"] is not None
            and scenario_id
            in {
                "scenario_a",
                "scenario_b",
            }
            and phase == COMPLETE
        ):
            one_screen = {
                **one_screen,
                "primary_label": (
                    "Close verified playback"
                ),
                "primary_kind": "close_media",
            }


        if (
            analysis is not None
            and phase == PLANNED
        ):
            view["metrics"] = (
                analysis_metrics(
                    analysis
                )
            )

        if (
            execution is not None
            and phase == COMPLETE
        ):
            view["publication_status"] = (
                execution[
                    "publication_status"
                ]
            )

            view["blocked"] = False

            view["metrics"] = [
                {
                    "label": "OBJECTS",
                    "value": (
                        f"{execution['assets_verified']}/6"
                    ),
                    "detail": "remote verified",
                },
                {
                    "label": "ROUTES",
                    "value": (
                        f"{execution['paths_verified']}/2"
                    ),
                    "detail": "release healthy",
                },
                {
                    "label": "STALE",
                    "value": str(
                        execution[
                            "stale_assets_remaining"
                        ]
                    ),
                    "detail": "remaining",
                },
            ]

            view["sponsor_strip"] = [
                {
                    "label": "GENBLAZE",
                    "value": (
                        "Verified voice provenance reused"
                    ),
                    "detail": (
                        "0 new AI requests required"
                    ),
                },
                {
                    "label": "BACKBLAZE B2",
                    "value": "6 / 6 objects verified",
                    "detail": execution[
                        "release_id"
                    ],
                },
                {
                    "label": "RELEASE CHECK",
                    "value": "SAFE TO PUBLISH",
                    "detail": (
                        "Fresh approval · 2 / 2 routes"
                    ),
                },
            ]

        view["sponsor_strip"] = (
            final_third["sponsor_strip"]
        )

        with ui.dialog() as director_dialog:
            with ui.card().classes(
                "director-dialog p-5"
            ):
                with ui.row().classes(
                    "w-full items-start "
                    "justify-between gap-4"
                ):
                    with ui.column().classes(
                        "gap-0"
                    ):
                        ui.label(
                            "CHANGE DIRECTOR"
                        ).classes(
                            "text-[9px] font-black "
                            "tracking-[0.18em] "
                            "text-cyan-300"
                        )

                        ui.label(
                            "What changed in your story?"
                        ).classes(
                            "text-2xl font-black text-white"
                        )

                        ui.label(
                            "Every option runs a real, "
                            "evidence-backed workflow."
                        ).classes(
                            "text-xs text-slate-500"
                        )

                    ui.button(
                        icon="close",
                        on_click=director_dialog.close,
                    ).props(
                        "flat round dense"
                    )

                with ui.element("div").classes(
                    "director-grid w-full mt-3"
                ):
                    for option in director_options():
                        selected = (
                            option["id"]
                            == scenario_id
                        )

                        with ui.column().classes(
                            "director-card"
                            + (
                                " border-cyan-400/60"
                                if selected
                                else ""
                            )
                        ):
                            with ui.row().classes(
                                "w-full items-center "
                                "justify-between gap-2"
                            ):
                                ui.icon(
                                    option["icon"]
                                ).classes(
                                    "text-2xl text-cyan-300"
                                )

                                ui.label(
                                    option["tag"]
                                ).classes(
                                    "scenario-tag"
                                )

                            ui.label(
                                option["title"]
                            ).classes(
                                "text-lg font-black text-white"
                            )

                            ui.label(
                                option["summary"]
                            ).classes(
                                "text-xs leading-relaxed "
                                "text-slate-400"
                            )

                            ui.label(
                                option["result"]
                            ).classes(
                                "mt-auto text-[10px] "
                                "font-black text-cyan-200"
                            )

                            ui.button(
                                (
                                    "Selected"
                                    if selected
                                    else "Use this change"
                                ),
                                on_click=lambda
                                scenario=option["id"]: (
                                    choose_scenario(
                                        scenario
                                    ),
                                    director_dialog.close(),
                                ),
                            ).props(
                                "flat dense no-caps"
                            ).classes(
                                "w-full"
                            )

        with ui.dialog() as why_dialog:
            with ui.card().classes(
                "why-dialog p-5"
            ):
                with ui.row().classes(
                    "w-full items-start "
                    "justify-between gap-4"
                ):
                    with ui.column().classes(
                        "gap-1"
                    ):
                        ui.label(
                            "DEPENDENCY EXPLANATION"
                        ).classes(
                            "text-[9px] font-black "
                            "tracking-[0.18em] "
                            "text-cyan-300"
                        )

                        ui.label(
                            focus["why"]["title"]
                        ).classes(
                            "text-xl font-black text-white"
                        )

                        ui.label(
                            focus["why"]["summary"]
                        ).classes(
                            "text-xs leading-relaxed "
                            "text-slate-400"
                        )

                    ui.button(
                        icon="close",
                        on_click=why_dialog.close,
                    ).props(
                        "flat round dense"
                    )

                with ui.column().classes(
                    "w-full gap-0 mt-3"
                ):
                    for item in focus[
                        "why"
                    ]["items"]:
                        with ui.element(
                            "div"
                        ).classes(
                            "why-row"
                        ):
                            ui.label(
                                item["label"]
                            ).classes(
                                "text-xs font-bold "
                                "text-white"
                            )

                            ui.label(
                                item["reason"]
                            ).classes(
                                "text-[10px] "
                                "leading-relaxed "
                                "text-slate-500"
                            )

                            ui.label(
                                item["action"]
                            ).classes(
                                "text-[9px] font-black "
                                "tracking-[0.12em] "
                                "text-cyan-300"
                            )

        # FOCUSED CAUSAL PROOF
        with ui.dialog() as proof_dialog:
            focused_proof = build_focused_proof(
                scenario_id=scenario_id,
                execution=state.get(
                    "execution_result"
                ),
            )

            with ui.card().classes(
                "focused-proof-card"
            ):
                with ui.row().classes(
                    "w-full items-start "
                    "justify-between gap-4"
                ):
                    with ui.column().classes(
                        "min-w-0 gap-1"
                    ):
                        ui.label(
                            focused_proof["eyebrow"]
                        ).classes(
                            "proof-eyebrow"
                        )

                        ui.label(
                            focused_proof["title"]
                        ).classes(
                            "proof-title"
                        )

                        ui.label(
                            focused_proof["summary"]
                        ).classes(
                            "proof-summary"
                        )

                    ui.button(
                        icon="close",
                        on_click=proof_dialog.close,
                    ).props(
                        "flat round dense"
                    )

                with ui.row().classes(
                    "proof-legend-row"
                ):
                    for item in focused_proof["legend"]:
                        with ui.row().classes(
                            "items-center gap-2"
                        ):
                            ui.element(
                                "span"
                            ).classes(
                                "proof-legend-shape "
                                + item["kind"]
                            )

                            ui.label(
                                item["label"]
                            ).classes(
                                "proof-legend-label"
                            )

                causal_nodes = focused_proof.get(
                    "causal_nodes",
                    focused_proof["nodes"],
                )

                independent_nodes = focused_proof.get(
                    "independent_nodes",
                    [],
                )

                topology_classes = (
                    "proof-topology split"
                    if independent_nodes
                    else "proof-topology"
                )

                with ui.element("div").classes(
                    topology_classes
                ):
                    with ui.row().classes(
                        "proof-causal-row"
                    ):
                        for index, node in enumerate(
                            causal_nodes
                        ):
                            if index:
                                ui.icon(
                                    "east"
                                ).classes(
                                    "proof-causal-arrow"
                                )

                            with ui.column().classes(
                                "proof-node "
                                + node["kind"]
                                + " "
                                + node["state"]
                            ):
                                ui.label(
                                    node["label"]
                                ).classes(
                                    "proof-node-title"
                                )

                                ui.label(
                                    node["detail"]
                                ).classes(
                                    "proof-node-detail"
                                )

                    if independent_nodes:
                        with ui.column().classes(
                            "proof-independent-panel"
                        ):
                            ui.label(
                                "INDEPENDENT ROUTE"
                            ).classes(
                                "proof-independent-label"
                            )

                            for node in independent_nodes:
                                with ui.column().classes(
                                    "proof-node independent "
                                    + node["kind"]
                                    + " "
                                    + node["state"]
                                ):
                                    ui.label(
                                        node["label"]
                                    ).classes(
                                        "proof-node-title"
                                    )

                                    ui.label(
                                        node["detail"]
                                    ).classes(
                                        "proof-node-detail"
                                    )

                with ui.row().classes(
                    "proof-metric-row"
                ):
                    for metric in focused_proof["metrics"]:
                        with ui.column().classes(
                            "proof-metric"
                        ):
                            ui.label(
                                metric["label"]
                            ).classes(
                                "proof-metric-label"
                            )

                            ui.label(
                                metric["value"]
                            ).classes(
                                "proof-metric-value"
                            )

                with ui.column().classes(
                    "proof-facts"
                ):
                    for fact in focused_proof["facts"]:
                        with ui.row().classes(
                            "proof-fact-row"
                        ):
                            ui.label(
                                fact["label"]
                            ).classes(
                                "proof-fact-label"
                            )

                            with ui.column().classes(
                                "min-w-0 flex-1 gap-0"
                            ):
                                ui.label(
                                    fact["value"]
                                ).classes(
                                    "proof-fact-value"
                                )

                                ui.label(
                                    fact["detail"]
                                ).classes(
                                    "proof-fact-detail"
                                )

                ui.label(
                    focused_proof["verdict"]
                ).classes(
                    "proof-verdict "
                    + focused_proof["tone"]
                )

                with ui.row().classes(
                    "proof-actions "
                    "w-full justify-end gap-3"
                ):
                    ui.button(
                        "View complete dependency graph",
                        icon="account_tree",
                        on_click=lambda: (
                            full_graph_dialog.open()
                        ),
                    ).props(
                        "outline no-caps"
                    )

                    ui.button(
                        "Close",
                        on_click=proof_dialog.close,
                    ).props(
                        "unelevated no-caps"
                    )

        with ui.dialog() as full_graph_dialog:
            with ui.card().classes(
                "proof-dialog p-6"
            ):
                with ui.row().classes(
                    "w-full items-center "
                    "justify-between gap-4"
                ):
                    with ui.column().classes(
                        "gap-0"
                    ):
                        ui.label(
                            "TECHNICAL RELEASE PROOF"
                        ).classes(
                            "text-[9px] font-black "
                            "tracking-[0.18em] "
                            "text-cyan-300"
                        )

                        ui.label(
                            "Dependency, provenance, "
                            "and remote verification"
                        ).classes(
                            "text-xl font-black text-white"
                        )

                    ui.button(
                        icon="close",
                        on_click=full_graph_dialog.close,
                    ).props(
                        "flat round dense"
                    )

                with ui.row().classes(
                    "w-full gap-5 "
                    "items-start flex-wrap"
                ):
                    ui.echart(
                        scenario[
                            "graph_options"
                        ]
                    ).style(
                        "height: 420px; "
                        "width: min(100%, 690px);"
                    )

                    with ui.column().classes(
                        "flex-1 min-w-[280px]"
                    ):
                        proof_row(
                            "Generation engine",
                            proof[
                                "generation_engine"
                            ],
                        )

                        proof_row(
                            "Provider",
                            proof["provider"],
                        )

                        proof_row(
                            "Model",
                            proof["model"],
                        )

                        proof_row(
                            "Genblaze run",
                            proof["run_id"],
                        )

                        proof_row(
                            "B2 release record",
                            proof[
                                "b2_object_key"
                            ],
                        )

                        proof_row(
                            "Remote verification",
                            (
                                "VERIFIED"
                                if proof[
                                    "remote_verified"
                                ]
                                else "INCOMPLETE"
                            ),
                        )

                        if analysis is not None:
                            proof_row(
                                "Live plan SHA-256",
                                analysis[
                                    "plan_sha256"
                                ],
                            )

                        if execution is not None:
                            proof_row(
                                "Execution mode",
                                execution["mode"],
                            )

                            proof_row(
                                "Fresh approval",
                                execution[
                                    "approval_id"
                                ],
                            )

                            proof_row(
                                "Fresh release",
                                execution[
                                    "release_id"
                                ],
                            )

                            proof_row(
                                "B2 release record",
                                execution[
                                    "release_object_key"
                                ],
                            )

                            proof_row(
                                "B2 guard record",
                                execution[
                                    "guard_report_object_key"
                                ],
                            )

        with ui.dialog() as media_dialog:
            with ui.card().classes(
                "media-dialog p-5"
            ):
                with ui.row().classes(
                    "w-full items-center "
                    "justify-between gap-4"
                ):
                    with ui.column().classes(
                        "gap-0"
                    ):
                        ui.label(
                            "VERIFIED MEDIA COMPARISON"
                        ).classes(
                            "text-[9px] font-black "
                            "tracking-[0.18em] "
                            "text-cyan-300"
                        )

                        ui.label(
                            comparison["caption"]
                        ).classes(
                            "text-lg font-black text-white"
                        )

                    ui.button(
                        icon="close",
                        on_click=media_dialog.close,
                    ).props(
                        "flat round dense"
                    )

                with ui.element("div").classes(
                    "media-grid w-full"
                ):
                    with ui.column().classes(
                        "media-card p-3 gap-2"
                    ):
                        ui.label(
                            comparison[
                                "before_label"
                            ]
                        ).classes(
                            "text-[10px] font-black "
                            "tracking-[0.15em] "
                            "text-amber-300"
                        )

                        ui.video(
                            comparison["before"]
                        ).props(
                            "controls preload=metadata"
                        ).classes(
                            "release-video"
                        )

                    with ui.column().classes(
                        "media-card p-3 gap-2"
                    ):
                        ui.label(
                            comparison[
                                "after_label"
                            ]
                        ).classes(
                            "text-[10px] font-black "
                            "tracking-[0.15em] "
                            "text-cyan-300"
                        )

                        ui.video(
                            comparison["after"]
                        ).props(
                            "controls preload=metadata"
                        ).classes(
                            "release-video"
                        )

                ui.label(
                    "These are original presentation copies of "
                    "the B2-verified release media."
                ).classes(
                    "text-[10px] text-slate-600"
                )

        with ui.column().classes(
            "app-shell"
        ):
            with ui.row().classes(
                "topbar w-full items-center "
                "justify-between gap-4"
            ):
                with ui.column().classes(
                    "gap-0"
                ):
                    ui.label(
                        "BRANCHLINE"
                    ).classes(
                        "brand-mark text-[10px] "
                        "font-black text-cyan-300"
                    )

                    ui.label(
                        "FOR VISUAL NOVEL & "
                        "INTERACTIVE COMIC TEAMS"
                    ).classes(
                        "director-audience"
                    )

                    ui.label(
                        "Revise a branching story without "
                        "publishing stale media."
                    ).classes(
                        "text-lg font-black text-white"
                    )

                    ui.label(
                        "Rebuild only what changed. "
                        "Verify every route."
                    ).classes(
                        "purpose-line"
                    )

                with ui.row().classes(
                    "items-center gap-3"
                ):
                    ui.label(
                        mode_label(
                            phase=phase,
                            busy=state["busy"],
                            analysis=analysis,
                            execution_mode=state[
                                "execution_mode"
                            ],
                        )
                    ).classes(
                        "mode-label hidden md:block"
                    )

                    render_workflow_segments(
                        scenario_id=scenario_id,
                        on_select=choose_scenario,
                        disabled=state["busy"],
                    )

            shell_classes = (
                "release-shell one-screen w-full"
            )

            with ui.element("main").classes(
                shell_classes
            ):
                with ui.element("div").classes(
                    "main-grid"
                ):
                    with ui.element(
                        "section"
                    ).classes(
                        "spread-stage"
                    ):
                        with ui.element(
                            "div"
                        ).classes(
                            "spread-panels"
                        ):
                            render_panel(
                                view["panels"][0],
                                position="left",
                                number="A",
                                focus_class=focus[
                                    "panels"
                                ]["left"]["class"],
                                focus_badges=focus[
                                    "panels"
                                ]["left"]["badges"],
                            )

                            render_panel(
                                view["panels"][1],
                                position="right",
                                number="B",
                                focus_class=focus[
                                    "panels"
                                ]["right"]["class"],
                                focus_badges=focus[
                                    "panels"
                                ]["right"]["badges"],
                                media_bundle=(
                                    state[
                                        "verified_media"
                                    ]
                                    if (
                                        scenario_id
                                        in {
                                            "scenario_a",
                                            "scenario_b",
                                        }
                                        and phase
                                        == COMPLETE
                                    )
                                    else None
                                ),
                                media_tab=state[
                                    "verified_media_tab"
                                ],
                                media_loading=(
                                    state[
                                        "verified_media_loading"
                                    ]
                                    and scenario_id
                                    in {
                                        "scenario_a",
                                        "scenario_b",
                                    }
                                ),
                                on_media_tab=(
                                    set_verified_media_tab
                                ),
                                on_media_close=(
                                    close_verified_media
                                ),
                            )

                        with ui.element(
                            "div"
                        ).classes(
                            "story-strip"
                        ):
                            with ui.column().classes(
                                "story-meta gap-1"
                            ):
                                ui.label(
                                    view["story_label"]
                                ).classes(
                                    "text-[8px] font-black "
                                    "tracking-[0.15em] "
                                    "text-cyan-300"
                                )

                                ui.label(
                                    view[
                                        "chapter_label"
                                    ]
                                ).classes(
                                    "text-xs font-bold "
                                    "text-white"
                                )

                            with ui.column().classes(
                                "story-copy gap-1"
                            ):
                                ui.label(
                                    "CURRENT STORY LINE"
                                ).classes(
                                    "text-[8px] font-black "
                                    "tracking-[0.18em] "
                                    "text-slate-500"
                                )

                                ui.label(
                                    f"“{view['dialogue_line']}”"
                                ).classes(
                                    "text-sm md:text-base "
                                    "font-semibold text-white"
                                )

                    with ui.element("aside").classes(
                        "decision-rail"
                    ):
                        with ui.column().classes(
                            "gap-2"
                        ):
                            ui.label(
                                view["copy"]["eyebrow"]
                            ).classes(
                                "decision-eyebrow"
                            )

                            ui.label(
                                view["copy"]["title"]
                            ).classes(
                                "text-3xl md:text-4xl "
                                "font-black leading-tight "
                                "text-white"
                            )

                            ui.label(
                                view["copy"]["body"]
                            ).classes(
                                "text-xs leading-relaxed "
                                "text-slate-400"
                            )

                        if phase == READY:
                            render_revision_diff(
                                revision
                            )

                        if (
                            phase == PLANNED
                            and not state["busy"]
                        ):
                            ui.label(
                                "LIVE DEPENDENCY ANALYSIS"
                            ).classes(
                                "text-[9px] font-black "
                                "tracking-[0.17em] "
                                "text-cyan-300"
                            )

                            with ui.element(
                                "div"
                            ).classes(
                                "metric-row"
                            ):
                                for metric in view[
                                    "metrics"
                                ]:
                                    render_metric(
                                        metric
                                    )

                            render_causal_map(
                                causal
                            )

                            ui.button(
                                "Why these assets?",
                                icon="help_outline",
                                on_click=why_dialog.open,
                            ).props(
                                "flat dense no-caps"
                            ).classes(
                                "w-fit text-xs text-cyan-200"
                            )

                            with ui.column().classes(
                                "plan-binding gap-1"
                            ):
                                ui.label(
                                    "SELECTIVE REBUILD PLAN"
                                ).classes(
                                    "text-[8px] font-black "
                                    "tracking-[0.16em] "
                                    "text-cyan-300"
                                )

                                ui.label(
                                    revision["plan"]
                                ).classes(
                                    "text-[11px] "
                                    "leading-relaxed "
                                    "text-slate-300"
                                )

                                if analysis is not None:
                                    ui.label(
                                        "Approval binds to "
                                        + analysis[
                                            "plan_sha256"
                                        ][:16]
                                        + "…"
                                    ).classes(
                                        "mono text-[9px] "
                                        "text-slate-600"
                                    )

                        if state["busy"]:
                            with ui.column().classes(
                                "gap-2"
                            ):
                                if (
                                    state["execution_mode"]
                                    == "LIVE_EXECUTION"
                                ):
                                    ui.label(
                                        "LIVE B2 EXECUTION"
                                    ).classes(
                                        "text-[9px] font-black "
                                        "tracking-[0.17em] "
                                        "text-cyan-300"
                                    )

                                    ui.spinner(
                                        size="lg",
                                        color="cyan",
                                    )

                                    ui.label(
                                        state[
                                            "live_stage_detail"
                                        ]
                                        or (
                                            "Executing the "
                                            "approved release…"
                                        )
                                    ).classes(
                                        "text-xs "
                                        "leading-relaxed "
                                        "text-slate-300"
                                    )

                                    ui.label(
                                        "The prior healthy release "
                                        "remains untouched."
                                    ).classes(
                                        "text-[10px] "
                                        "text-emerald-300"
                                    )

                                else:
                                    ui.label(
                                        "VERIFIED EXECUTION REPLAY"
                                    ).classes(
                                        "text-[9px] font-black "
                                        "tracking-[0.17em] "
                                        "text-amber-300"
                                    )

                                    ui.label(
                                        "Each stage advances only "
                                        "after its stored evidence "
                                        "passes validation."
                                    ).classes(
                                        "text-[10px] "
                                        "leading-relaxed "
                                        "text-slate-500"
                                    )

                                    render_stages(
                                        replay_stages,
                                        completed=set(
                                            state[
                                                "completed_stages"
                                            ]
                                        ),
                                        active_stage=state[
                                            "active_stage"
                                        ],
                                    )

                        if (
                            phase == COMPLETE
                            and not state["busy"]
                        ):
                            if view["metrics"]:
                                with ui.element(
                                    "div"
                                ).classes(
                                    "metric-row"
                                ):
                                    for metric in view[
                                        "metrics"
                                    ]:
                                        render_metric(
                                            metric
                                        )

                            verdict_class = (
                                "verdict blocked"
                                if view["blocked"]
                                else "verdict"
                            )

                            with ui.column().classes(
                                f"{verdict_class} gap-1"
                            ):
                                ui.label(
                                    "PUBLICATION DECISION"
                                ).classes(
                                    "text-[8px] font-black "
                                    "tracking-[0.17em] "
                                    "text-slate-500"
                                )

                                ui.label(
                                    view[
                                        "publication_status"
                                    ]
                                ).classes(
                                    "text-2xl font-black "
                                    "text-white"
                                )

                                ui.label(
                                    (
                                        "Unsafe route stopped "
                                        "before release."
                                        if view["blocked"]
                                        else
                                        "Mission completed "
                                        "and verified."
                                    )
                                ).classes(
                                    "text-xs text-slate-300"
                                )

                            render_final_receipt(
                                final_third[
                                    "final_receipt"
                                ]
                            )

                            ui.button(
                                "Play before / after media",
                                icon="play_circle",
                                on_click=media_dialog.open,
                            ).props(
                                "outline dense no-caps "
                                "color=cyan-5"
                            ).classes(
                                "secondary-action"
                            )

                        if state["fallback_reason"]:
                            with ui.column().classes(
                                "gap-1 border-l-2 "
                                "border-amber-400 "
                                "bg-amber-950/20 p-3"
                            ):
                                ui.label(
                                    "HONEST FALLBACK"
                                ).classes(
                                    "text-[9px] font-black "
                                    "tracking-[0.16em] "
                                    "text-amber-300"
                                )

                                ui.label(
                                    "Live execution was unavailable. "
                                    "Branchline displayed the stored, "
                                    "remotely verified release instead."
                                ).classes(
                                    "text-xs text-amber-100"
                                )

                                ui.label(
                                    state["fallback_reason"]
                                ).classes(
                                    "text-[9px] "
                                    "text-slate-500"
                                )

                        if state["analysis_error"]:
                            with ui.column().classes(
                                "gap-1 border-l-2 "
                                "border-rose-400 "
                                "bg-rose-950/20 p-3"
                            ):
                                ui.label(
                                    "ANALYSIS STOPPED"
                                ).classes(
                                    "text-[9px] font-black "
                                    "tracking-[0.16em] "
                                    "text-rose-300"
                                )

                                ui.label(
                                    state[
                                        "analysis_error"
                                    ]
                                ).classes(
                                    "text-xs text-rose-100"
                                )

                        if state["stage_error"]:
                            with ui.column().classes(
                                "gap-1 border-l-2 "
                                "border-rose-400 "
                                "bg-rose-950/20 p-3"
                            ):
                                ui.label(
                                    "REPLAY VERIFICATION STOPPED"
                                ).classes(
                                    "text-[9px] font-black "
                                    "tracking-[0.16em] "
                                    "text-rose-300"
                                )

                                ui.label(
                                    state["stage_error"]
                                ).classes(
                                    "text-xs text-rose-100"
                                )

                        with ui.column().classes(
                            "mt-auto w-full gap-1"
                        ):
                            if state["busy"]:
                                action_label = (
                                    "Executing selective rebuild…"
                                    if state["execution_mode"]
                                    == "LIVE_EXECUTION"
                                    else
                                    "Verifying stored release…"
                                )
                            elif phase == READY:
                                action_label = (
                                    "Verify reachable media"
                                    if scenario_id
                                    == "scenario_c"
                                    else "Analyze revision"
                                )
                            elif phase == PLANNED:
                                action_label = (
                                    "Approve selective rebuild"
                                )
                            else:
                                action_label = (
                                    "Replay demonstration"
                                )

                            action_props = (
                                "outline no-caps "
                                "color=blue-grey-5"
                                if phase == COMPLETE
                                else
                                "unelevated no-caps "
                                "color=primary"
                            )

                            action_button = ui.button(
                                action_label,
                                on_click=advance,
                            ).props(
                                action_props
                            ).classes(
                                "primary-action"
                            )

                            if state["busy"]:
                                action_button.props(
                                    "disable loading"
                                )

                            ui.button(
                                "View technical proof",
                                on_click=proof_dialog.open,
                            ).props(
                                "flat dense no-caps"
                            ).classes(
                                "secondary-action text-xs"
                            )

                primary_callback = advance

                if (
                    one_screen["primary_kind"]
                    == "media"
                ):
                    primary_callback = (
                        open_verified_media
                        if scenario_id
                        == "scenario_b"
                        else (
                            open_dialogue_media
                            if scenario_id
                            == "scenario_a"
                            else media_dialog.open
                        )
                    )

                elif (
                    one_screen["primary_kind"]
                    == "close_media"
                ):
                    primary_callback = (
                        close_verified_media
                    )

                elif (
                    one_screen["primary_kind"]
                    == "proof"
                ):
                    primary_callback = (
                        proof_dialog.open
                    )

                render_one_screen_command(
                    command=one_screen,
                    on_primary=primary_callback,
                    on_proof=proof_dialog.open,
                    disabled=(
                        state["busy"]
                        or state[
                            "verified_media_loading"
                        ]
                    ),
                )

    screen()


if __name__ in {
    "__main__",
    "__mp_main__",
}:
    ui.run(
        host="0.0.0.0",
        port=int(
            os.getenv("PORT", "8080")
        ),
        title="Branchline",
        show=False,
        reload=False,
    )
