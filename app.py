"""Branchline creator release cockpit."""

from __future__ import annotations

import os

from nicegui import ui

from branchline.presentation.judge_view import (
    load_scenarios,
)


SCENARIOS = load_scenarios()


ui.add_head_html(
    """
    <style>
      body {
        background:
          radial-gradient(circle at 10% 0%,
            rgba(37, 99, 235, 0.18), transparent 30%),
          radial-gradient(circle at 90% 5%,
            rgba(168, 85, 247, 0.15), transparent 28%),
          #070b14;
        color: #e2e8f0;
      }

      .branchline-card {
        background: rgba(15, 23, 42, 0.82);
        border: 1px solid rgba(100, 116, 139, 0.32);
        border-radius: 18px;
        box-shadow: 0 18px 50px rgba(0, 0, 0, 0.22);
        backdrop-filter: blur(12px);
      }

      .metric-card {
        min-height: 132px;
        background: linear-gradient(
          145deg,
          rgba(30, 41, 59, 0.95),
          rgba(15, 23, 42, 0.92)
        );
        border: 1px solid rgba(100, 116, 139, 0.34);
        border-radius: 16px;
      }

      .scenario-button {
        border: 1px solid rgba(100, 116, 139, 0.42);
        border-radius: 12px;
      }

      .safe-state {
        background: rgba(16, 185, 129, 0.13);
        border: 1px solid rgba(52, 211, 153, 0.45);
      }

      .blocked-state {
        background: rgba(239, 68, 68, 0.13);
        border: 1px solid rgba(248, 113, 113, 0.48);
      }

      .stage-complete {
        border-left: 3px solid #38bdf8;
      }

      .mono-value {
        font-family:
          ui-monospace,
          SFMono-Regular,
          Menlo,
          Monaco,
          Consolas,
          monospace;
        overflow-wrap: anywhere;
      }
    </style>
    """,
    shared=True,
)


def metric_card(
    label: str,
    value: str,
    detail: str,
) -> None:
    """Render one prominent scoreboard metric."""
    with ui.card().classes(
        "metric-card flex-1 min-w-[190px] p-5"
    ):
        ui.label(label).classes(
            "text-xs uppercase tracking-[0.14em] "
            "text-slate-400 font-semibold"
        )

        ui.label(value).classes(
            "text-4xl font-black text-white mt-2"
        )

        ui.label(detail).classes(
            "text-sm text-slate-400 mt-2"
        )


def identifier_list(
    title: str,
    values: list[str],
    *,
    empty_text: str,
) -> None:
    """Render a concise list of technical identifiers."""
    with ui.column().classes(
        "gap-2 flex-1 min-w-[250px]"
    ):
        ui.label(title).classes(
            "text-xs uppercase tracking-[0.14em] "
            "text-slate-400 font-semibold"
        )

        if not values:
            ui.label(empty_text).classes(
                "text-sm text-slate-500"
            )
            return

        for value in values:
            ui.label(value).classes(
                "mono-value text-sm text-slate-200 "
                "bg-slate-900/70 rounded-lg px-3 py-2 w-full"
            )


@ui.page("/")
def index() -> None:
    """Render the Branchline judge experience."""
    ui.dark_mode().enable()

    state = {
        "scenario_id": "scenario_b",
    }

    @ui.refreshable
    def dashboard() -> None:
        view = SCENARIOS[
            state["scenario_id"]
        ]

        is_blocked = (
            view["publication_status"]
            == "BLOCKED"
        )

        with ui.column().classes(
            "w-full gap-5"
        ):
            with ui.card().classes(
                "branchline-card w-full p-6"
            ):
                with ui.row().classes(
                    "w-full items-start justify-between gap-5"
                ):
                    with ui.column().classes(
                        "gap-2 max-w-4xl"
                    ):
                        with ui.row().classes(
                            "items-center gap-3"
                        ):
                            ui.badge(
                                view["mode"],
                                color="blue-grey-8",
                            ).props("outline")

                            ui.badge(
                                view["short_name"],
                                color="indigo-7",
                            )

                        ui.label(
                            view["title"]
                        ).classes(
                            "text-3xl md:text-4xl "
                            "font-black text-white"
                        )

                        ui.label(
                            view["trigger"]
                        ).classes(
                            "text-base md:text-lg "
                            "text-slate-300"
                        )

                    status_classes = (
                        "blocked-state"
                        if is_blocked
                        else "safe-state"
                    )

                    with ui.column().classes(
                        f"{status_classes} rounded-2xl "
                        "px-5 py-4 min-w-[230px]"
                    ):
                        ui.label(
                            "PUBLICATION DECISION"
                        ).classes(
                            "text-xs tracking-[0.14em] "
                            "font-semibold text-slate-400"
                        )

                        ui.label(
                            view["publication_status"]
                        ).classes(
                            "text-xl font-black mt-1"
                        )

                        ui.label(
                            view["status_message"]
                        ).classes(
                            "text-xs text-slate-400 mt-2"
                        )

            with ui.row().classes(
                "w-full gap-4 flex-wrap"
            ):
                for metric in view["metrics"]:
                    metric_card(
                        metric["label"],
                        metric["value"],
                        metric["detail"],
                    )

            with ui.row().classes(
                "w-full gap-5 items-stretch"
            ):
                with ui.card().classes(
                    "branchline-card p-5 "
                    "w-full xl:w-[68%]"
                ):
                    with ui.row().classes(
                        "w-full justify-between items-center"
                    ):
                        with ui.column().classes("gap-1"):
                            ui.label(
                                "Live dependency view"
                            ).classes(
                                "text-xl font-bold text-white"
                            )

                            ui.label(
                                "Hover or drag to inspect "
                                "source → asset → path relationships."
                            ).classes(
                                "text-sm text-slate-400"
                            )

                        ui.badge(
                            "DYNAMIC GRAPH",
                            color="cyan-8",
                        ).props("outline")

                    ui.echart(
                        view["graph_options"]
                    ).style(
                        "height: 470px; width: 100%;"
                    )

                with ui.card().classes(
                    "branchline-card p-5 "
                    "w-full xl:flex-1"
                ):
                    ui.label(
                        "Verified workflow"
                    ).classes(
                        "text-xl font-bold text-white"
                    )

                    stages = [
                        (
                            "1",
                            "Observe",
                            "Story or remote-media change detected.",
                        ),
                        (
                            "2",
                            "Diagnose",
                            "Affected assets and paths calculated.",
                        ),
                        (
                            "3",
                            "Approve",
                            "Exact rebuild plan bound to approval.",
                        ),
                        (
                            "4",
                            "Act",
                            (
                                "Selective media release executed."
                                if not is_blocked
                                else
                                "Unsafe publication prevented."
                            ),
                        ),
                        (
                            "5",
                            "Verify",
                            "Remote objects and paths checked.",
                        ),
                        (
                            "6",
                            "Record",
                            "Canonical evidence stored in B2.",
                        ),
                    ]

                    for number, title, detail in stages:
                        with ui.row().classes(
                            "stage-complete w-full "
                            "items-start gap-3 pl-4 py-2"
                        ):
                            ui.badge(
                                number,
                                color="light-blue-8",
                            )

                            with ui.column().classes(
                                "gap-0"
                            ):
                                ui.label(title).classes(
                                    "font-bold text-slate-100"
                                )

                                ui.label(detail).classes(
                                    "text-xs text-slate-400"
                                )

            with ui.card().classes(
                "branchline-card w-full p-5"
            ):
                ui.label(
                    "Decision breakdown"
                ).classes(
                    "text-xl font-bold text-white"
                )

                with ui.row().classes(
                    "w-full gap-5 flex-wrap mt-2"
                ):
                    identifier_list(
                        "Changed sources",
                        view["changed_sources"],
                        empty_text=(
                            "Remote object failure, "
                            "not a source edit"
                        ),
                    )

                    identifier_list(
                        "Rebuilt assets",
                        view["rebuilt_assets"],
                        empty_text=(
                            "No rebuild completed "
                            "because publication was blocked"
                        ),
                    )

                    identifier_list(
                        "Reused assets",
                        view["reused_assets"],
                        empty_text=(
                            "Healthy assets were verified "
                            "rather than released"
                        ),
                    )

                    identifier_list(
                        "Failed assets",
                        view["failed_assets"],
                        empty_text="No failed assets",
                    )

            with ui.row().classes(
                "w-full gap-5 items-stretch"
            ):
                with ui.card().classes(
                    "branchline-card p-5 flex-1"
                ):
                    ui.label(
                        "Reachable path health"
                    ).classes(
                        "text-xl font-bold text-white"
                    )

                    for path in view["paths"]:
                        path_color = (
                            "positive"
                            if path["verified"]
                            else "negative"
                        )

                        with ui.row().classes(
                            "w-full items-center "
                            "justify-between rounded-xl "
                            "bg-slate-900/60 px-4 py-3 mt-3"
                        ):
                            with ui.column().classes(
                                "gap-0"
                            ):
                                ui.label(
                                    path["path_id"]
                                ).classes(
                                    "mono-value font-semibold"
                                )

                                ui.label(
                                    f"{len(path['required_assets'])} "
                                    "required assets"
                                ).classes(
                                    "text-xs text-slate-400"
                                )

                            ui.badge(
                                path["status"],
                                color=path_color,
                            )

                provenance = view["provenance"]

                with ui.card().classes(
                    "branchline-card p-5 flex-1"
                ):
                    ui.label(
                        "Sponsor-native evidence"
                    ).classes(
                        "text-xl font-bold text-white"
                    )

                    evidence_rows = [
                        (
                            "Generation engine",
                            provenance[
                                "generation_engine"
                            ],
                        ),
                        (
                            "Provider",
                            provenance["provider"],
                        ),
                        (
                            "Model",
                            provenance["model"],
                        ),
                        (
                            "Run ID",
                            provenance["run_id"],
                        ),
                        (
                            "B2 record",
                            provenance[
                                "b2_object_key"
                            ],
                        ),
                        (
                            "Remote verification",
                            (
                                "VERIFIED"
                                if provenance[
                                    "remote_verified"
                                ]
                                else "INCOMPLETE"
                            ),
                        ),
                    ]

                    for label, value in evidence_rows:
                        with ui.column().classes(
                            "gap-0 mt-3"
                        ):
                            ui.label(label).classes(
                                "text-xs uppercase "
                                "tracking-[0.12em] "
                                "text-slate-500"
                            )

                            ui.label(str(value)).classes(
                                "mono-value text-sm "
                                "text-slate-200"
                            )

    def select_scenario(
        scenario_id: str,
    ) -> None:
        state["scenario_id"] = scenario_id
        dashboard.refresh()

    with ui.column().classes(
        "w-full max-w-[1500px] mx-auto "
        "px-5 md:px-8 py-7 gap-5"
    ):
        with ui.row().classes(
            "w-full items-center justify-between gap-5"
        ):
            with ui.column().classes("gap-1"):
                ui.label("BRANCHLINE").classes(
                    "text-sm tracking-[0.28em] "
                    "font-black text-cyan-400"
                )

                ui.label(
                    "Change one scene. Rebuild only "
                    "what it affects."
                ).classes(
                    "text-2xl md:text-3xl "
                    "font-black text-white"
                )

                ui.label(
                    "Publish no stale branches."
                ).classes(
                    "text-base text-slate-400"
                )

            ui.badge(
                "CORE ENGINE VERIFIED",
                color="green-8",
            ).props("outline")

        with ui.row().classes(
            "w-full gap-3 flex-wrap"
        ):
            for scenario_id, scenario in SCENARIOS.items():
                label = (
                    f"{scenario['short_name']} · "
                    f"{scenario['title']}"
                )

                ui.button(
                    label,
                    on_click=lambda sid=scenario_id: (
                        select_scenario(sid)
                    ),
                ).props(
                    "outline no-caps"
                ).classes(
                    "scenario-button"
                )

        dashboard()

        ui.label(
            "Verified Replay uses real release and guard "
            "evidence produced by Branchline. "
            "It does not present cached execution as live."
        ).classes(
            "text-xs text-slate-500 text-center w-full pb-4"
        )


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
