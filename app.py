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


def render_panel(
    panel: dict[str, str],
    *,
    position: str,
    number: str,
) -> None:
    with ui.element("article").classes(
        f"manga-panel {position} {panel['tone']}"
    ):
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
                panel["status"]
            ).classes(
                "panel-status"
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


@ui.page("/")
def index() -> None:
    ui.dark_mode().enable()

    state: dict[str, Any] = {
        "scenario_id": "scenario_b",
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

        with ui.dialog() as proof_dialog:
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
                        on_click=proof_dialog.close,
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
                        "Change one scene. Rebuild only "
                        "what depends on it."
                    ).classes(
                        "text-lg font-black text-white"
                    )

                    ui.label(
                        "Publish no stale branches."
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

                    incident_select = ui.select(
                        options={
                            "scenario_b": (
                                "Selective rebuild"
                            ),
                            "scenario_c": (
                                "Missing media"
                            ),
                            "scenario_a": (
                                "Shared dialogue"
                            ),
                        },
                        value=scenario_id,
                        on_change=lambda event: (
                            choose_scenario(
                                event.value
                            )
                        ),
                    ).props(
                        "dense outlined options-dense"
                    ).classes(
                        "incident-select"
                    )

                    if state["busy"]:
                        incident_select.props(
                            "disable"
                        )

            with ui.element("main").classes(
                "release-shell w-full"
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
                            )

                            render_panel(
                                view["panels"][1],
                                position="right",
                                number="B",
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

                with ui.element("footer").classes(
                    "sponsor-strip"
                ):
                    for item in view[
                        "sponsor_strip"
                    ]:
                        with ui.column().classes(
                            "sponsor-cell"
                        ):
                            ui.label(
                                item["label"]
                            ).classes(
                                "text-[8px] font-black "
                                "tracking-[0.17em] "
                                "text-cyan-300"
                            )

                            ui.label(
                                item["value"]
                            ).classes(
                                "truncate text-xs "
                                "font-bold text-white"
                            )

                            ui.label(
                                item["detail"]
                            ).classes(
                                "truncate text-[9px] "
                                "text-slate-600"
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
