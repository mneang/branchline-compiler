"""Branchline cinematic release cockpit."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from nicegui import app, ui

from branchline.presentation.anime_ui import (
    install_anime_style,
    render_scene_fx,
    render_story_quote,
)
from branchline.presentation.cinematic import (
    build_cinematic_view,
)
from branchline.presentation.flow import (
    COMPLETE,
    PLANNED,
    READY,
    next_phase,
)


ART_DIRECTORY = (
    Path(__file__).resolve().parent
    / "assets"
    / "ui"
)

if not ART_DIRECTORY.exists():
    raise RuntimeError(
        "Original UI art is missing. Run "
        "`python scripts/generate_ui_art.py`."
    )

app.add_static_files(
    "/ui-art",
    str(ART_DIRECTORY),
)


ui.add_head_html(
    """
    <style>
      :root {
        --ink: #060914;
        --panel: rgba(12, 18, 33, .92);
        --line: rgba(148, 163, 184, .23);
        --muted: #94a3b8;
        --cyan: #67e8f9;
        --safe: #52e3a4;
        --warning: #fbbf70;
        --danger: #fb7185;
      }

      body {
        margin: 0;
        min-height: 100vh;
        overflow-x: hidden;
        background:
          radial-gradient(circle at 8% 4%,
            rgba(56, 189, 248, .15), transparent 28%),
          radial-gradient(circle at 92% 8%,
            rgba(217, 70, 239, .11), transparent 26%),
          var(--ink);
        color: #e8edf7;
      }

      .app-shell {
        width: min(1400px, calc(100vw - 34px));
        margin: 0 auto;
      }

      .brand-subtitle {
        letter-spacing: .28em;
      }

      .scenario-button {
        min-height: 34px;
        border-radius: 999px;
        padding: 0 15px;
      }

      .cockpit {
        background:
          linear-gradient(145deg,
            rgba(17, 25, 44, .95),
            rgba(8, 13, 25, .95));
        border: 1px solid var(--line);
        border-radius: 24px;
        box-shadow:
          0 26px 80px rgba(0, 0, 0, .38);
        overflow: hidden;
      }

      .progress-rail {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 8px;
      }

      .progress-step {
        height: 4px;
        border-radius: 999px;
        background: rgba(100, 116, 139, .25);
        transition:
          background .35s ease,
          box-shadow .35s ease;
      }

      .progress-step.done {
        background: linear-gradient(
          90deg,
          #38bdf8,
          #67e8f9
        );
        box-shadow:
          0 0 18px rgba(103, 232, 249, .35);
      }

      .hero-grid {
        display: grid;
        grid-template-columns:
          minmax(0, 1.35fr)
          minmax(340px, .82fr);
        min-height: 660px;
      }

      .scene-stage {
        position: relative;
        min-height: 660px;
        overflow: hidden;
        isolation: isolate;
        background: #10172a;
      }

      .scene-stage::after {
        content: "";
        position: absolute;
        inset: 0;
        z-index: 2;
        pointer-events: none;
        background:
          linear-gradient(
            180deg,
            rgba(4, 8, 18, .25) 0%,
            rgba(4, 8, 18, .02) 36%,
            rgba(4, 8, 18, .93) 100%
          ),
          linear-gradient(
            90deg,
            rgba(4, 8, 18, .05),
            rgba(4, 8, 18, .18)
          );
      }

      .scene-stage.blocked::after {
        background:
          linear-gradient(
            180deg,
            rgba(58, 8, 24, .28),
            rgba(20, 5, 14, .25) 35%,
            rgba(20, 5, 14, .96)
          );
      }

      .scene-image {
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
        transform: scale(1.015);
        animation: scene-arrival .7s ease-out;
      }

      .scene-content {
        position: absolute;
        inset: 0;
        z-index: 3;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        padding: 30px;
      }

      .scene-chip {
        width: fit-content;
        border: 1px solid rgba(255, 255, 255, .28);
        background: rgba(5, 10, 22, .52);
        backdrop-filter: blur(10px);
        border-radius: 999px;
        padding: 8px 13px;
      }

      .scene-title {
        max-width: 720px;
        text-shadow:
          0 5px 30px rgba(0, 0, 0, .75);
      }

      .route-card {
        flex: 1;
        min-width: 180px;
        border: 1px solid rgba(255, 255, 255, .18);
        background: rgba(5, 10, 22, .64);
        backdrop-filter: blur(12px);
        border-radius: 14px;
        padding: 13px 15px;
      }

      .route-card.safe {
        border-color: rgba(82, 227, 164, .48);
      }

      .route-card.warning {
        border-color: rgba(251, 191, 112, .55);
      }

      .route-card.blocked {
        border-color: rgba(251, 113, 133, .65);
        background: rgba(61, 13, 30, .72);
      }

      .decision-panel {
        background:
          linear-gradient(
            180deg,
            rgba(11, 17, 31, .97),
            rgba(7, 12, 23, .98)
          );
        border-left: 1px solid var(--line);
      }

      .active-change {
        border: 1px solid rgba(251, 191, 112, .34);
        background: rgba(120, 72, 22, .12);
        border-radius: 15px;
      }

      .plan-block {
        border: 1px solid var(--line);
        background: rgba(22, 31, 52, .7);
        border-radius: 15px;
      }

      .metric-tile {
        flex: 1;
        min-width: 105px;
        border: 1px solid var(--line);
        background: rgba(21, 30, 51, .76);
        border-radius: 14px;
        padding: 14px;
      }

      .publication-seal {
        border-radius: 18px;
        padding: 18px;
      }

      .publication-seal.safe {
        border: 1px solid rgba(82, 227, 164, .5);
        background: rgba(16, 120, 80, .14);
      }

      .publication-seal.blocked {
        border: 1px solid rgba(251, 113, 133, .58);
        background: rgba(130, 24, 58, .16);
      }

      .primary-action {
        width: 100%;
        min-height: 55px;
        border-radius: 14px;
        font-weight: 900;
        letter-spacing: .01em;
      }

      .proof-panel {
        border-top: 1px solid var(--line);
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

      @keyframes scene-arrival {
        from {
          opacity: 0;
          transform: scale(1.045);
        }

        to {
          opacity: 1;
          transform: scale(1.015);
        }
      }

      @media (max-width: 980px) {
        body {
          overflow-y: auto;
        }

        .hero-grid {
          grid-template-columns: 1fr;
        }

        .scene-stage {
          min-height: 530px;
        }

        .decision-panel {
          border-left: 0;
          border-top: 1px solid var(--line);
        }
      }

      @media (max-width: 620px) {
        .app-shell {
          width: min(100% - 20px, 1400px);
        }

        .scene-stage {
          min-height: 500px;
        }

        .scene-content {
          padding: 20px;
        }
      }
    </style>
    """,
    shared=True,
)


def metric_tile(
    label: str,
    value: str,
    detail: str,
) -> None:
    with ui.column().classes(
        "metric-tile gap-1"
    ):
        ui.label(label).classes(
            "text-[10px] font-black "
            "tracking-[0.16em] text-slate-500"
        )

        ui.label(value).classes(
            "text-3xl font-black text-white"
        )

        ui.label(detail).classes(
            "text-[11px] text-slate-400"
        )


def proof_row(
    label: str,
    value: Any,
) -> None:
    with ui.row().classes(
        "w-full justify-between items-start "
        "gap-4 py-2 border-b border-slate-800"
    ):
        ui.label(label).classes(
            "text-xs text-slate-500"
        )

        ui.label(str(value)).classes(
            "mono text-xs text-slate-200 "
            "text-right max-w-[68%]"
        )


def progress_rail(
    phase: str,
) -> None:
    completed = {
        READY: 1,
        PLANNED: 2,
        COMPLETE: 3,
    }[phase]

    with ui.element("div").classes(
        "progress-rail w-full"
    ):
        for index in range(1, 4):
            classes = (
                "progress-step done"
                if index <= completed
                else "progress-step"
            )

            ui.element("div").classes(
                classes
            )


def route_card(
    route: dict[str, str],
) -> None:
    with ui.column().classes(
        f"route-card {route['tone']} gap-1"
    ):
        ui.label(
            route["label"]
        ).classes(
            "text-[11px] font-black "
            "tracking-[0.15em] text-slate-300"
        )

        ui.label(
            route["status"]
        ).classes(
            "text-sm font-black text-white"
        )


install_anime_style()


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
        experience = build_cinematic_view(
            state["scenario_id"],
            state["phase"],
        )

        scenario = experience[
            "scenario"
        ]

        phase = experience[
            "phase"
        ]

        with ui.column().classes(
            "app-shell min-h-screen py-4 gap-4"
        ):
            # Compact brand and scenario navigation.
            with ui.row().classes(
                "w-full items-center "
                "justify-between gap-4 flex-wrap"
            ):
                with ui.column().classes(
                    "gap-0"
                ):
                    ui.label(
                        "BRANCHLINE"
                    ).classes(
                        "brand-subtitle text-[11px] "
                        "font-black text-cyan-300"
                    )

                    ui.label(
                        "Change one scene. "
                        "Publish no stale branches."
                    ).classes(
                        "text-lg md:text-xl "
                        "font-black text-white"
                    )

                with ui.row().classes(
                    "gap-2 flex-wrap"
                ):
                    options = [
                        (
                            "scenario_b",
                            "SELECTIVE REBUILD",
                        ),
                        (
                            "scenario_c",
                            "SAFETY CHECK",
                        ),
                        (
                            "scenario_a",
                            "SHARED CHANGE",
                        ),
                    ]

                    for scenario_id, label in options:
                        selected = (
                            scenario_id
                            == state[
                                "scenario_id"
                            ]
                        )

                        props = (
                            "unelevated no-caps "
                            "color=primary"
                            if selected
                            else "outline no-caps "
                            "color=blue-grey-6"
                        )

                        ui.button(
                            label,
                            on_click=lambda sid=scenario_id: (
                                choose_scenario(sid)
                            ),
                        ).props(
                            props
                        ).classes(
                            "scenario-button text-[11px]"
                        )

            with ui.card().classes(
                "cockpit w-full p-0"
            ):
                with ui.column().classes(
                    "w-full gap-0"
                ):
                    with ui.column().classes(
                        "w-full px-6 pt-5 pb-4 gap-2"
                    ):
                        with ui.row().classes(
                            "w-full justify-between "
                            "items-center"
                        ):
                            ui.label(
                                experience[
                                    "step_label"
                                ]
                            ).classes(
                                "text-[10px] font-black "
                                "tracking-[0.16em] "
                                "text-slate-500"
                            )

                            ui.label(
                                "VERIFIED REPLAY"
                            ).classes(
                                "text-[10px] font-black "
                                "tracking-[0.14em] "
                                "text-cyan-400"
                            )

                        progress_rail(
                            phase
                        )

                    with ui.element(
                        "div"
                    ).classes(
                        "hero-grid w-full"
                    ):
                        # Cinematic story canvas.
                        scene_classes = (
                            "scene-stage "
                            f"phase-{phase} "
                            f"accent-{experience['accent']}"
                        )

                        if experience["blocked"]:
                            scene_classes += " blocked"

                        with ui.element(
                            "section"
                        ).classes(
                            scene_classes
                        ):
                            ui.image(
                                experience["image"]
                            ).props(
                                "fit=cover"
                            ).classes(
                                "scene-image"
                            )

                            render_scene_fx(
                                experience
                            )

                            with ui.element(
                                "div"
                            ).classes(
                                "scene-content"
                            ):
                                with ui.row().classes(
                                    "w-full justify-between "
                                    "items-start gap-3"
                                ):
                                    ui.label(
                                        experience[
                                            "story_label"
                                        ]
                                    ).classes(
                                        "scene-chip text-[10px] "
                                        "font-black tracking-[0.16em]"
                                    )

                                    ui.label(
                                        experience[
                                            "route_label"
                                        ]
                                    ).classes(
                                        "scene-chip text-[10px] "
                                        "font-black tracking-[0.16em]"
                                    )

                                with ui.column().classes(
                                    "gap-5"
                                ):
                                    if experience[
                                        "blocked"
                                    ]:
                                        with ui.row().classes(
                                            "items-center gap-2"
                                        ):
                                            ui.icon(
                                                "lock"
                                            ).classes(
                                                "text-rose-300 text-2xl"
                                            )

                                            ui.label(
                                                "ROUTE LOCKED"
                                            ).classes(
                                                "font-black "
                                                "tracking-[0.16em] "
                                                "text-rose-200"
                                            )

                                    with ui.column().classes(
                                        "scene-title gap-2"
                                    ):
                                        ui.label(
                                            experience[
                                                "chapter_label"
                                            ]
                                        ).classes(
                                            "text-[10px] font-black "
                                            "tracking-[0.18em] "
                                            "text-cyan-200/90"
                                        )

                                        render_story_quote(
                                            experience
                                        )

                                        ui.label(
                                            experience[
                                                "scene_title"
                                            ]
                                        ).classes(
                                            "text-3xl md:text-5xl "
                                            "font-black leading-tight "
                                            "text-white"
                                        )

                                        ui.label(
                                            experience[
                                                "scene_caption"
                                            ]
                                        ).classes(
                                            "max-w-2xl text-sm "
                                            "md:text-base leading-relaxed "
                                            "text-slate-200"
                                        )

                                    with ui.row().classes(
                                        "w-full gap-3 flex-wrap"
                                    ):
                                        for route in experience[
                                            "route_cards"
                                        ]:
                                            route_card(
                                                route
                                            )

                        # Focused creator decision.
                        with ui.column().classes(
                            "decision-panel p-6 gap-5"
                        ):
                            with ui.column().classes(
                                "gap-2"
                            ):
                                ui.label(
                                    experience[
                                        "copy"
                                    ]["headline"]
                                ).classes(
                                    "text-2xl md:text-3xl "
                                    "font-black leading-tight "
                                    "text-white"
                                )

                                ui.label(
                                    experience[
                                        "copy"
                                    ]["supporting"]
                                ).classes(
                                    "text-sm leading-relaxed "
                                    "text-slate-400"
                                )

                            if phase == READY:
                                with ui.column().classes(
                                    "active-change p-4 gap-2"
                                ):
                                    ui.label(
                                        "ACTIVE CHANGE"
                                    ).classes(
                                        "text-[10px] font-black "
                                        "tracking-[0.16em] "
                                        "text-amber-300"
                                    )

                                    ui.label(
                                        experience[
                                            "active_change"
                                        ]
                                    ).classes(
                                        "mono text-base "
                                        "font-bold text-white"
                                    )

                                    ui.label(
                                        "No release decision has "
                                        "been revealed yet."
                                    ).classes(
                                        "text-xs text-slate-500"
                                    )

                            if phase == PLANNED:
                                with ui.row().classes(
                                    "w-full gap-3"
                                ):
                                    for metric in experience[
                                        "summary_metrics"
                                    ]:
                                        metric_tile(
                                            metric[
                                                "label"
                                            ],
                                            metric[
                                                "value"
                                            ],
                                            metric[
                                                "detail"
                                            ],
                                        )

                                with ui.column().classes(
                                    "plan-block p-4 gap-3"
                                ):
                                    ui.label(
                                        "EXACT PLAN"
                                    ).classes(
                                        "text-[10px] font-black "
                                        "tracking-[0.16em] "
                                        "text-slate-500"
                                    )

                                    for asset_id in scenario[
                                        "rebuilt_assets"
                                    ]:
                                        with ui.row().classes(
                                            "w-full items-center gap-2"
                                        ):
                                            ui.icon(
                                                "auto_fix_high"
                                            ).classes(
                                                "text-rose-300"
                                            )

                                            ui.label(
                                                asset_id
                                            ).classes(
                                                "mono text-xs "
                                                "text-slate-200"
                                            )

                                    if scenario[
                                        "reused_assets"
                                    ]:
                                        ui.separator().classes(
                                            "bg-slate-800"
                                        )

                                        ui.label(
                                            f"{len(scenario['reused_assets'])} "
                                            "verified B2 assets remain "
                                            "byte-identical."
                                        ).classes(
                                            "text-xs text-emerald-300"
                                        )

                            if phase == COMPLETE:
                                seal_class = (
                                    "publication-seal blocked"
                                    if experience[
                                        "blocked"
                                    ]
                                    else "publication-seal safe"
                                )

                                with ui.column().classes(
                                    f"{seal_class} gap-1"
                                ):
                                    ui.label(
                                        "PUBLICATION DECISION"
                                    ).classes(
                                        "text-[10px] font-black "
                                        "tracking-[0.16em] "
                                        "text-slate-400"
                                    )

                                    ui.label(
                                        scenario[
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
                                            if experience[
                                                "blocked"
                                            ]
                                            else
                                            "Mission completed "
                                            "and verified."
                                        )
                                    ).classes(
                                        "text-xs text-slate-300"
                                    )

                                with ui.row().classes(
                                    "w-full gap-3"
                                ):
                                    for metric in experience[
                                        "summary_metrics"
                                    ]:
                                        metric_tile(
                                            metric[
                                                "label"
                                            ],
                                            metric[
                                                "value"
                                            ],
                                            metric[
                                                "detail"
                                            ],
                                        )

                            with ui.column().classes(
                                "mt-auto gap-3"
                            ):
                                ui.button(
                                    experience[
                                        "primary_action"
                                    ],
                                    on_click=advance,
                                ).props(
                                    "unelevated no-caps "
                                    "color=primary"
                                ).classes(
                                    "primary-action"
                                )

                                ui.label(
                                    "Real stored evidence. "
                                    "No cached result is labeled live."
                                ).classes(
                                    "text-[10px] text-center "
                                    "text-slate-600"
                                )

                    # Optional proof stays below the primary interaction.
                    if phase != READY:
                        with ui.expansion(
                            "Inspect dependency graph and sponsor proof",
                            icon="verified",
                        ).classes(
                            "proof-panel w-full "
                            "px-6 py-2"
                        ):
                            with ui.row().classes(
                                "w-full gap-5 "
                                "items-start flex-wrap py-4"
                            ):
                                ui.echart(
                                    scenario[
                                        "graph_options"
                                    ]
                                ).style(
                                    "height: 360px; "
                                    "width: min(100%, 720px);"
                                )

                                proof = scenario[
                                    "provenance"
                                ]

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
                                        proof[
                                            "provider"
                                        ],
                                    )

                                    proof_row(
                                        "Model",
                                        proof[
                                            "model"
                                        ],
                                    )

                                    proof_row(
                                        "Genblaze run",
                                        proof[
                                            "run_id"
                                        ],
                                    )

                                    proof_row(
                                        "B2 record",
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
