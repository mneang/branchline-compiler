"""Branchline manga release studio."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from nicegui import app, ui

from branchline.presentation.flow import (
    COMPLETE,
    READY,
    next_phase,
)
from branchline.presentation.release_spread import (
    build_release_spread,
)


ROOT = Path(__file__).resolve().parent
MANGA_DIRECTORY = ROOT / "assets" / "manga"

if not MANGA_DIRECTORY.exists():
    raise RuntimeError(
        "Manga release artwork is missing. Run "
        "`python scripts/generate_manga_release_art.py`."
    )

app.add_static_files(
    "/manga-art",
    str(MANGA_DIRECTORY),
)


ui.add_head_html(
    """
    <style>
      :root {
        --ink: #05070c;
        --paper: #f4f1e9;
        --panel: #0c111c;
        --line: rgba(226, 232, 240, .17);
        --muted: #8d99ab;
        --cyan: #5ed8ec;
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
            rgba(94, 216, 236, .11),
            transparent 30%
          ),
          radial-gradient(
            circle at 92% 8%,
            rgba(169, 147, 232, .08),
            transparent 27%
          ),
          var(--ink);
      }

      .app-shell {
        width: min(1450px, calc(100vw - 30px));
        height: 100vh;
        margin: 0 auto;
        padding: 13px 0;
        display: flex;
        flex-direction: column;
        gap: 11px;
        box-sizing: border-box;
      }

      .topbar {
        min-height: 48px;
        flex: 0 0 auto;
      }

      .brand-mark {
        letter-spacing: .29em;
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
          76px;
        overflow: hidden;
        border: 1px solid var(--line);
        border-radius: 21px;
        background: #080c14;
        box-shadow:
          0 28px 78px rgba(0, 0, 0, .42);
      }

      .main-grid {
        min-height: 0;
        display: grid;
        grid-template-columns:
          minmax(0, 1.58fr)
          minmax(335px, .68fr);
      }

      .spread-stage {
        position: relative;
        min-width: 0;
        min-height: 0;
        overflow: hidden;
        background: #020306;
        border-right: 1px solid var(--line);
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
        filter: saturate(.85);
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
        background:
          linear-gradient(
            180deg,
            rgba(3, 5, 9, .12),
            transparent 38%,
            rgba(3, 5, 9, .90) 100%
          );
        pointer-events: none;
      }

      .manga-panel.warning {
        box-shadow:
          inset 0 0 0 3px
          rgba(237, 181, 93, .58);
      }

      .manga-panel.safe {
        box-shadow:
          inset 0 0 0 3px
          rgba(94, 216, 236, .47);
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
        background: rgba(4, 7, 13, .77);
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
        bottom: 104px;
        color: rgba(255, 255, 255, .10);
        font-family: Georgia, serif;
        font-size: clamp(80px, 9vw, 150px);
        font-weight: 900;
        line-height: .8;
      }

      .story-strip {
        position: absolute;
        z-index: 6;
        left: 29px;
        right: 29px;
        bottom: 24px;
        display: grid;
        grid-template-columns:
          minmax(165px, .38fr)
          minmax(0, 1.62fr);
        overflow: hidden;
        border: 1px solid rgba(255, 255, 255, .23);
        border-left: 4px solid var(--cyan);
        background:
          linear-gradient(
            90deg,
            rgba(3, 5, 10, .94),
            rgba(3, 5, 10, .76)
          );
        box-shadow:
          0 15px 35px rgba(0, 0, 0, .38);
        backdrop-filter: blur(12px);
      }

      .story-meta {
        padding: 13px 15px;
        border-right:
          1px solid rgba(255, 255, 255, .15);
      }

      .story-copy {
        padding: 13px 18px;
      }

      .decision-rail {
        min-width: 0;
        min-height: 0;
        display: flex;
        flex-direction: column;
        gap: 17px;
        padding: 25px;
        box-sizing: border-box;
        background:
          linear-gradient(
            180deg,
            #0d1422,
            #070b13
          );
      }

      .decision-eyebrow {
        color: var(--cyan);
        font-size: 10px;
        font-weight: 950;
        letter-spacing: .19em;
      }

      .active-change {
        padding: 13px 14px;
        border-left: 3px solid var(--amber);
        background: rgba(237, 181, 93, .08);
      }

      .metric-row {
        display: grid;
        grid-template-columns:
          repeat(3, minmax(0, 1fr));
        gap: 8px;
      }

      .metric {
        min-width: 0;
        padding: 12px 10px;
        border-top: 2px solid var(--cyan);
        background: rgba(18, 28, 46, .72);
      }

      .verdict {
        position: relative;
        overflow: hidden;
        padding: 17px;
        border: 1px solid
          rgba(94, 216, 236, .44);
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
          1px solid rgba(94, 216, 236, .21);
        border-radius: 50%;
      }

      .primary-action {
        width: 100%;
        min-height: 52px;
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

      .secondary-proof {
        min-height: 30px;
        color: #8290a4;
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
        padding: 10px 17px;
        border-right: 1px solid var(--line);
      }

      .sponsor-cell:last-child {
        border-right: 0;
      }

      .proof-dialog {
        width: min(1080px, calc(100vw - 38px));
        max-width: 1080px;
        max-height: 86vh;
        overflow-y: auto;
        border: 1px solid var(--line);
        background: #0a101b;
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

      @media (max-width: 990px) {
        body {
          overflow-y: auto;
        }

        .app-shell {
          width: min(100% - 18px, 1450px);
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
          min-height: 520px;
        }
      }

      @media (max-width: 650px) {
        .spread-stage {
          min-height: 525px;
        }

        .story-strip {
          left: 14px;
          right: 14px;
          grid-template-columns: 1fr;
        }

        .story-meta {
          display: none;
        }

        .manga-panel.right .panel-heading {
          left: 15%;
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
        .manga-image {
          animation: none;
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
            "text-[9px] font-black "
            "tracking-[0.16em] text-slate-500"
        )

        ui.label(
            metric["value"]
        ).classes(
            "text-2xl font-black text-white"
        )

        ui.label(
            metric["detail"]
        ).classes(
            "text-[10px] text-slate-500"
        )


@ui.page("/")
def index() -> None:
    ui.dark_mode().enable()

    state = {
        "scenario_id": "scenario_b",
        "phase": READY,
    }

    def choose_scenario(
        scenario_id: str,
    ) -> None:
        state["scenario_id"] = scenario_id
        state["phase"] = READY
        screen.refresh()

    def advance() -> None:
        state["phase"] = next_phase(
            state["scenario_id"],
            state["phase"],
        )

        screen.refresh()

    @ui.refreshable
    def screen() -> None:
        view = build_release_spread(
            state["scenario_id"],
            state["phase"],
        )

        phase = view["phase"]
        scenario = view["scenario"]
        proof = scenario["provenance"]

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
                            "text-[10px] font-black "
                            "tracking-[0.18em] "
                            "text-cyan-300"
                        )

                        ui.label(
                            "Dependency graph, provenance, "
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
                    "w-full gap-5 items-start flex-wrap"
                ):
                    ui.echart(
                        scenario["graph_options"]
                    ).style(
                        "height: 420px; "
                        "width: min(100%, 690px);"
                    )

                    with ui.column().classes(
                        "flex-1 min-w-[280px]"
                    ):
                        proof_row(
                            "Generation engine",
                            proof["generation_engine"],
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
                            proof["b2_object_key"],
                        )

                        proof_row(
                            "Remote verification",
                            (
                                "VERIFIED"
                                if proof["remote_verified"]
                                else "INCOMPLETE"
                            ),
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
                        "Release studio for branching stories"
                    ).classes(
                        "text-lg font-black text-white"
                    )

                with ui.row().classes(
                    "items-center gap-3"
                ):
                    ui.label(
                        "VERIFIED EVIDENCE REPLAY"
                    ).classes(
                        "hidden md:block text-[9px] "
                        "font-black tracking-[0.14em] "
                        "text-slate-600"
                    )

                    ui.select(
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
                        value=state["scenario_id"],
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

            with ui.element("main").classes(
                "release-shell w-full"
            ):
                with ui.element("div").classes(
                    "main-grid"
                ):
                    with ui.element("section").classes(
                        "spread-stage"
                    ):
                        with ui.element("div").classes(
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

                        with ui.element("div").classes(
                            "story-strip"
                        ):
                            with ui.column().classes(
                                "story-meta gap-1"
                            ):
                                ui.label(
                                    view["story_label"]
                                ).classes(
                                    "text-[9px] font-black "
                                    "tracking-[0.15em] "
                                    "text-cyan-300"
                                )

                                ui.label(
                                    view["chapter_label"]
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
                                "text-sm leading-relaxed "
                                "text-slate-400"
                            )

                        if phase == READY:
                            with ui.column().classes(
                                "active-change gap-1"
                            ):
                                ui.label(
                                    "ACTIVE CHANGE"
                                ).classes(
                                    "text-[9px] font-black "
                                    "tracking-[0.16em] "
                                    "text-amber-300"
                                )

                                ui.label(
                                    view["active_change"]
                                ).classes(
                                    "mono text-sm font-bold "
                                    "text-white"
                                )

                                ui.label(
                                    "Impact has not been "
                                    "calculated yet."
                                ).classes(
                                    "text-[11px] "
                                    "text-slate-500"
                                )

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

                        if phase != READY:
                            with ui.column().classes(
                                "gap-2 border-l-2 "
                                "border-cyan-500/50 "
                                "pl-3"
                            ):
                                ui.label(
                                    (
                                        "APPROVAL-SAFE PLAN"
                                        if phase != COMPLETE
                                        else
                                        "VERIFIED OUTCOME"
                                    )
                                ).classes(
                                    "text-[9px] font-black "
                                    "tracking-[0.16em] "
                                    "text-slate-500"
                                )

                                ui.label(
                                    view["copy"]["body"]
                                ).classes(
                                    "text-xs leading-relaxed "
                                    "text-slate-300"
                                )

                        if phase == COMPLETE:
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
                                    "text-[9px] font-black "
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

                        with ui.column().classes(
                            "mt-auto w-full gap-1"
                        ):
                            action_props = (
                                "outline no-caps "
                                "color=blue-grey-5"
                                if phase == COMPLETE
                                else
                                "unelevated no-caps "
                                "color=primary"
                            )

                            ui.button(
                                view["action_label"],
                                on_click=advance,
                            ).props(
                                action_props
                            ).classes(
                                "primary-action"
                            )

                            ui.button(
                                "View technical proof",
                                on_click=proof_dialog.open,
                            ).props(
                                "flat dense no-caps"
                            ).classes(
                                "secondary-proof w-full "
                                "text-xs"
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
