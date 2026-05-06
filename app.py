# Copyright (c) 2025 Artemii Remizov
# Licensed under CC BY-NC 4.0 — https://creativecommons.org/licenses/by-nc/4.0/
#
# CardioSim v3.0 — Plotly Dash application
# Avanzolini et al. (1988) lumped-parameter model · McSharry ECG synthesis

import json
import numpy as np
import pandas as pd

import dash
from dash import dcc, html, Input, Output, State, ctx, no_update
import dash_bootstrap_components as dbc

from model import CLINICAL_PRESETS, STATE_LABELS, CATEGORY_COLORS, build_params
from metrics import run_sim, classify_metric
from plots import make_monitor_plot, make_pv_loop, make_all_variables

# ─────────────────────────────────────────────────────────────
# App initialisation
# ─────────────────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.DARKLY,
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css",
    ],
    title="CardioSim — Cardiovascular Simulator",
    suppress_callback_exceptions=True,
)
server = app.server  # for gunicorn / production deployment


# ─────────────────────────────────────────────────────────────
# Serialisation helpers (numpy → JSON → numpy round-trip)
# ─────────────────────────────────────────────────────────────
def _arr(v):
    return v.tolist() if isinstance(v, np.ndarray) else v


def serialize_result(result):
    if result is None:
        return None
    m = result["metrics"]
    params = {
        k: (list(v) if isinstance(v, (np.ndarray, list)) and k == "X0" else _arr(v))
        for k, v in result["params"].items()
    }
    return {
        "t":      result["t"].tolist(),
        "X":      result["X"].tolist(),
        "ecg":    result["ecg"].tolist(),
        "preset": result["preset"],
        "params": params,
        "metrics": {
            "co":       float(m["co"]),
            "sv":       float(m["sv"]),
            "sys":      float(m["sys"]),
            "dia":      float(m["dia"]),
            "map_val":  float(m["map_val"]),
            "pp":       float(m["pp"]),
            "lv_vol":   m["lv_vol"].tolist(),
            "lvp":      m["lvp"].tolist(),
            "lvof":     m["lvof"].tolist(),
            "lvp_full": m["lvp_full"].tolist(),
        },
        "rr": result["rr"].tolist() if result["rr"] is not None else None,
    }


def deserialize_result(data):
    if data is None:
        return None
    m = data["metrics"]
    params = {}
    for k, v in data["params"].items():
        if k == "X0":
            params[k] = list(v)           # keep as plain list for solve_ivp
        elif isinstance(v, list):
            params[k] = np.array(v)
        else:
            params[k] = v
    return {
        "t":      np.array(data["t"]),
        "X":      np.array(data["X"]),
        "ecg":    np.array(data["ecg"]),
        "preset": data["preset"],
        "params": params,
        "metrics": {
            "co":       m["co"],
            "sv":       m["sv"],
            "sys":      m["sys"],
            "dia":      m["dia"],
            "map_val":  m["map_val"],
            "pp":       m["pp"],
            "lv_vol":   np.array(m["lv_vol"]),
            "lvp":      np.array(m["lvp"]),
            "lvof":     np.array(m["lvof"]),
            "lvp_full": np.array(m["lvp_full"]),
        },
        "rr": np.array(data["rr"]) if data["rr"] is not None else None,
    }


# ─────────────────────────────────────────────────────────────
# UI Component helpers
# ─────────────────────────────────────────────────────────────
STATUS_COLOR = {"normal": "success", "warning": "warning", "danger": "danger"}


def make_metric_card(label, value_str, unit, status, delta=None):
    color = STATUS_COLOR[status]
    delta_badge = (
        dbc.Badge(
            delta,
            color="danger" if "↑" in delta else "success",
            className="ms-1",
            style={"fontSize": "0.65rem"},
        )
        if delta else html.Span()
    )
    return dbc.Col(
        dbc.Card(
            dbc.CardBody([
                html.P(label,
                       className="text-muted mb-1",
                       style={"fontSize": "0.68rem", "fontWeight": 700,
                              "textTransform": "uppercase", "letterSpacing": "0.06em"}),
                html.Div([
                    html.Span(value_str,
                              className=f"text-{color} metric-value",
                              style={"fontSize": "1.55rem", "fontWeight": 700}),
                    delta_badge,
                ]),
                html.Small(unit, className="text-muted"),
            ], className="p-2"),
            className=f"metric-card border-start border-{color} border-3 h-100",
        ),
        xs=6, sm=4, lg=2,
        className="mb-2",
    )


def category_badge(cat):
    labels = {"normal": "Normal", "arrhythmia": "Arrhythmia",
              "structural": "Structural", "critical": "Critical"}
    colors = {"normal": "success", "arrhythmia": "warning",
              "structural": "primary", "critical": "danger"}
    return dbc.Badge(labels.get(cat, cat), color=colors.get(cat, "secondary"),
                     className="ms-2", style={"fontSize": "0.65rem"})


def slider_row(label, slider_id, badge_id, unit, **kwargs):
    return html.Div([
        html.Div([
            html.Span(label, className="text-muted",
                      style={"fontSize": "0.8rem", "fontWeight": 500}),
            html.Span([
                dbc.Badge("–", id=badge_id, color="primary",
                          className="ms-2", style={"fontSize": "0.7rem",
                                                   "fontFamily": "monospace"}),
                html.Span(f" {unit}", className="text-muted",
                          style={"fontSize": "0.72rem"}),
            ]),
        ], className="d-flex justify-content-between align-items-center mb-1"),
        dcc.Slider(id=slider_id, **kwargs,
                   marks=None, tooltip={"always_visible": False}),
    ], className="mb-3")


def preset_gallery():
    cards = []
    for name, info in CLINICAL_PRESETS.items():
        cat = info["category"]
        border_color = {"normal": "#10b981", "arrhythmia": "#f59e0b",
                        "structural": "#3b82f6", "critical": "#ef4444"}.get(cat, "#64748b")
        cards.append(dbc.Col(
            html.Div([
                html.Div([
                    html.Span(name, className="preset-name"),
                    category_badge(cat),
                ], className="d-flex align-items-center mb-1"),
                html.Div(info["desc"], className="preset-desc"),
            ], className="preset-gallery-card",
               style={"borderLeftColor": border_color, "borderLeftWidth": "3px",
                      "borderLeftStyle": "solid"}),
            xs=12, sm=6, className="mb-2",
        ))
    return dbc.Row(cards, className="g-2")


# ─────────────────────────────────────────────────────────────
# Layout
# ─────────────────────────────────────────────────────────────
_PRESET_OPTIONS = [{"label": k, "value": k} for k in CLINICAL_PRESETS]

navbar = dbc.NavbarSimple(
    brand=html.Span(["CardioSim", html.Span(".", className="brand-dot")]),
    brand_href="#",
    color="dark",
    dark=True,
    fixed="top",
    children=[
        dbc.NavItem(dbc.Badge(
            "Avanzolini 1988  ·  McSharry ECG  ·  v3.0",
            color="secondary",
            className="me-3",
            style={"fontSize": "0.7rem", "fontWeight": 400},
        )),
        dbc.NavItem(dbc.NavLink(
            [html.I(className="bi bi-github"), "  Source"],
            href="https://github.com/artremizov/CardiacArrhythmia",
            target="_blank",
            style={"fontSize": "0.85rem"},
        )),
    ],
)

left_panel = html.Div([
    # ── Preset ──
    dbc.Card([
        dbc.CardHeader("Clinical Preset"),
        dbc.CardBody([
            dcc.Dropdown(
                id="preset-dropdown",
                options=_PRESET_OPTIONS,
                value="Healthy Adult",
                clearable=False,
                style={"fontSize": "0.85rem"},
            ),
            html.Div(id="preset-badge", className="mt-2"),
            html.Div(id="preset-desc",
                     className="mt-2 border-start border-primary ps-2",
                     style={"fontSize": "0.78rem", "color": "#94a3b8",
                            "borderLeftWidth": "2px !important"}),
        ]),
    ], className="mb-2"),

    # ── Compare toggle ──
    dbc.Card([
        dbc.CardBody([
            dbc.Switch(id="compare-switch", label="Compare Two Conditions", value=False,
                       className="mb-2"),
            html.Div(id="preset2-container", style={"display": "none"}, children=[
                html.Div("Comparison Preset",
                         className="text-muted mb-1",
                         style={"fontSize": "0.72rem", "fontWeight": 700,
                                "textTransform": "uppercase", "letterSpacing": "0.05em"}),
                dcc.Dropdown(
                    id="preset2-dropdown",
                    options=_PRESET_OPTIONS,
                    value="Heart Failure (Systolic)",
                    clearable=False,
                    style={"fontSize": "0.85rem"},
                ),
                html.Div(id="preset2-desc",
                         className="mt-2 border-start border-danger ps-2",
                         style={"fontSize": "0.78rem", "color": "#94a3b8"}),
            ]),
        ]),
    ], className="mb-2"),

    # ── Parameters ──
    dbc.Card([
        dbc.CardHeader("Parameters"),
        dbc.CardBody([
            slider_row("Heart Rate", "hr-slider", "hr-badge", "bpm",
                       min=30, max=400, step=1, value=75),
            slider_row("Contractility", "contract-slider", "contract-badge", "%",
                       min=10, max=160, step=1, value=100),
            slider_row("Peripheral Resistance", "resist-slider", "resist-badge", "",
                       min=0.4, max=2.5, step=0.05, value=1.0),
            slider_row("Arterial Compliance", "compl-slider", "compl-badge", "",
                       min=0.6, max=2.2, step=0.02, value=1.46),
        ]),
    ], className="mb-2"),

    # ── Simulation controls ──
    dbc.Card([
        dbc.CardHeader("Simulation"),
        dbc.CardBody([
            slider_row("Duration", "duration-slider", "duration-badge", "s",
                       min=2.0, max=20.0, step=0.5, value=6.0),
            slider_row("Plot window", "plot-window-slider", "plot-window-badge", "s",
                       min=0.5, max=6.0, step=0.25, value=2.5),
            dbc.Button(
                [dbc.Spinner(size="sm", spinner_style={"width": "0.9rem", "height": "0.9rem"}),
                 html.Span("  Run Simulation", id="run-btn-text")],
                id="run-btn", color="primary",
                className="w-100 mt-2", n_clicks=0,
            ),
            html.Div(id="sim-error", className="mt-2 text-danger",
                     style={"fontSize": "0.8rem"}),
        ]),
    ], className="mb-2"),
], className="control-card")

right_panel = html.Div([
    # ── Welcome hero (shown before first run) ──
    html.Div(id="welcome-panel", children=[
        html.Div([
            html.Div([
                html.H2([
                    html.Span("Cardio", style={"fontWeight": 800}),
                    html.Span("Sim", style={"color": "#0ea5e9", "fontWeight": 800}),
                ], className="mb-1", style={"letterSpacing": "-0.03em"}),
                html.P("Interactive hemodynamic simulator · Closed-loop 12-ODE cardiovascular model",
                       className="text-muted mb-3", style={"fontSize": "0.9rem"}),
                html.Hr(style={"borderColor": "rgba(148,163,184,0.15)"}),
                html.P("Select a clinical preset from the left panel and click Run Simulation.",
                       className="text-muted mb-3", style={"fontSize": "0.85rem"}),
                preset_gallery(),
            ], className="welcome-hero"),
        ]),
    ]),

    # ── Results section (shown after run) ──
    html.Div(id="results-section", style={"display": "none"}, children=[
        # Metric cards
        html.Div(id="metrics-row", className="mb-3"),

        # Tabs
        dbc.Tabs([
            dbc.Tab(label="Monitor",       tab_id="monitor",   activeTabClassName="fw-semibold"),
            dbc.Tab(label="PV Loop",       tab_id="pv-loop",   activeTabClassName="fw-semibold"),
            dbc.Tab(label="All Variables", tab_id="all-vars",  activeTabClassName="fw-semibold"),
            dbc.Tab(label="Export",        tab_id="export",    activeTabClassName="fw-semibold"),
        ], id="main-tabs", active_tab="monitor", className="mb-3"),

        html.Div(id="tab-content"),
    ]),
])

footer = html.Footer(
    dbc.Container(
        dbc.Row([
            dbc.Col(html.Span([
                "CardioSim v3.0  ·  ",
                html.A("Avanzolini et al. 1988", href="#", className="text-muted"),
                "  ·  McSharry ECG  ·  © 2025 Artemii Remizov, WSU  ·  ",
                html.A("CC BY-NC 4.0", href="https://creativecommons.org/licenses/by-nc/4.0/",
                       target="_blank", className="text-muted"),
            ]), className="text-center"),
        ]),
        fluid=True,
    ),
    className="footer-bar mt-4",
)

app.layout = dbc.Container([
    # Invisible state stores
    dcc.Store(id="sim-result-1", storage_type="memory"),
    dcc.Store(id="sim-result-2", storage_type="memory"),
    dcc.Store(id="compare-mode-store", data=False, storage_type="memory"),
    # Downloads
    dcc.Download(id="dl-wave1"),
    dcc.Download(id="dl-pv1"),
    dcc.Download(id="dl-full1"),
    dcc.Download(id="dl-wave2"),
    dcc.Download(id="dl-pv2"),
    dcc.Download(id="dl-full2"),

    navbar,

    dbc.Row([
        dbc.Col(left_panel, xs=12, md=3, className="mb-3"),
        dbc.Col(right_panel, xs=12, md=9),
    ], className="mt-3 g-3"),

    footer,
], fluid=True, className="px-3 px-md-4")


# ─────────────────────────────────────────────────────────────
# Callbacks
# ─────────────────────────────────────────────────────────────

# 1. Load preset defaults into sliders + update description badge
@app.callback(
    Output("hr-slider",       "value"),
    Output("contract-slider", "value"),
    Output("resist-slider",   "value"),
    Output("compl-slider",    "value"),
    Output("preset-desc",     "children"),
    Output("preset-badge",    "children"),
    Input("preset-dropdown",  "value"),
)
def load_preset(preset):
    info = CLINICAL_PRESETS[preset]
    badge = category_badge(info["category"])
    return info["hr"], info["contract"], info["resist"], info["compl"], info["desc"], badge


# 1b. Second preset description
@app.callback(
    Output("preset2-desc", "children"),
    Input("preset2-dropdown", "value"),
)
def load_preset2_desc(preset):
    return CLINICAL_PRESETS[preset]["desc"]


# 2. Slider live-value badges
@app.callback(
    Output("hr-badge",           "children"),
    Output("contract-badge",     "children"),
    Output("resist-badge",       "children"),
    Output("compl-badge",        "children"),
    Output("duration-badge",     "children"),
    Output("plot-window-badge",  "children"),
    Input("hr-slider",           "value"),
    Input("contract-slider",     "value"),
    Input("resist-slider",       "value"),
    Input("compl-slider",        "value"),
    Input("duration-slider",     "value"),
    Input("plot-window-slider",  "value"),
)
def update_badges(hr, contract, resist, compl, dur, pw):
    return str(hr), str(contract), f"{resist:.2f}", f"{compl:.2f}", f"{dur:.1f}", f"{pw:.2f}"


# 3. Plot window slider bounded by sim duration
@app.callback(
    Output("plot-window-slider", "max"),
    Output("plot-window-slider", "value"),
    Input("duration-slider",     "value"),
    State("plot-window-slider",  "value"),
)
def clamp_plot_window(dur, pw):
    new_max = dur
    new_pw  = min(pw, dur)
    return new_max, new_pw


# 4. Compare mode toggle
@app.callback(
    Output("compare-mode-store",  "data"),
    Output("preset2-container",   "style"),
    Input("compare-switch",       "value"),
)
def toggle_compare(on):
    style = {} if on else {"display": "none"}
    return on, style


# 5a. Run simulation 1
@app.callback(
    Output("sim-result-1", "data"),
    Output("sim-error",    "children"),
    Input("run-btn",       "n_clicks"),
    State("preset-dropdown",  "value"),
    State("hr-slider",        "value"),
    State("contract-slider",  "value"),
    State("resist-slider",    "value"),
    State("compl-slider",     "value"),
    State("duration-slider",  "value"),
    prevent_initial_call=True,
)
def run_simulation_1(n_clicks, preset, hr, contract, resist, compl, duration):
    params = build_params(preset, hr, contract, resist, compl)
    result = run_sim(params, duration, preset)
    if result is None:
        return no_update, "Solver failed to converge. Try adjusting parameters or increasing duration."
    return serialize_result(result), ""


# 5b. Run simulation 2 (only when compare mode active)
@app.callback(
    Output("sim-result-2",    "data"),
    Input("run-btn",          "n_clicks"),
    State("preset2-dropdown", "value"),
    State("duration-slider",  "value"),
    State("compare-mode-store", "data"),
    prevent_initial_call=True,
)
def run_simulation_2(n_clicks, preset2, duration, compare_on):
    if not compare_on:
        return None
    info2  = CLINICAL_PRESETS[preset2]
    params2 = build_params(preset2, info2["hr"], info2["contract"],
                           info2["resist"], info2["compl"])
    result2 = run_sim(params2, duration, preset2)
    return serialize_result(result2)


# 6. Show/hide welcome vs results + render metric cards
@app.callback(
    Output("welcome-panel",   "style"),
    Output("results-section", "style"),
    Output("metrics-row",     "children"),
    Input("sim-result-1",     "data"),
    Input("sim-result-2",     "data"),
    Input("compare-mode-store", "data"),
)
def update_metrics_display(data1, data2, compare_on):
    if data1 is None:
        return {}, {"display": "none"}, []

    r1 = deserialize_result(data1)
    r2 = deserialize_result(data2) if compare_on and data2 else None
    m1 = r1["metrics"]

    def fmt(v, dec=1):
        return f"{v:.{dec}f}"

    def delta_str(v1, v2):
        if v2 is None or v1 == 0:
            return None
        pct = (v2 - v1) / abs(v1) * 100
        arrow = "↑" if pct > 0 else "↓"
        return f"{arrow} {abs(pct):.1f}%"

    m2 = r2["metrics"] if r2 else None
    cards = [
        make_metric_card("Cardiac Output", fmt(m1["co"]),  "L/min",
                         classify_metric("co",  m1["co"]),
                         delta_str(m1["co"],  m2["co"]  if m2 else None)),
        make_metric_card("Stroke Volume",  fmt(m1["sv"], 0), "cm³",
                         classify_metric("sv",  m1["sv"]),
                         delta_str(m1["sv"],  m2["sv"]  if m2 else None)),
        make_metric_card("Systolic BP",    fmt(m1["sys"], 0), "mmHg",
                         classify_metric("sys", m1["sys"]),
                         delta_str(m1["sys"], m2["sys"] if m2 else None)),
        make_metric_card("Diastolic BP",   fmt(m1["dia"], 0), "mmHg",
                         classify_metric("dia", m1["dia"]),
                         delta_str(m1["dia"], m2["dia"] if m2 else None)),
        make_metric_card("Mean Art. Press.", fmt(m1["map_val"], 0), "mmHg",
                         classify_metric("map", m1["map_val"]),
                         delta_str(m1["map_val"], m2["map_val"] if m2 else None)),
        make_metric_card("Pulse Pressure",  fmt(m1["pp"], 0), "mmHg",
                         classify_metric("pp",  m1["pp"]),
                         delta_str(m1["pp"],  m2["pp"]  if m2 else None)),
    ]

    return {"display": "none"}, {}, dbc.Row(cards, className="g-2")


# 7. Tab content routing
@app.callback(
    Output("tab-content",       "children"),
    Input("main-tabs",          "active_tab"),
    Input("sim-result-1",       "data"),
    Input("sim-result-2",       "data"),
    Input("plot-window-slider", "value"),
    Input("compare-mode-store", "data"),
)
def render_tab(active_tab, data1, data2, plot_window, compare_on):
    if data1 is None:
        return html.Div()

    r1 = deserialize_result(data1)
    r2 = deserialize_result(data2) if compare_on and data2 else None
    t_end   = r1["t"][-1]
    t_start = max(0.0, t_end - plot_window)
    t_range = [t_start, t_end]

    if active_tab == "monitor":
        fig = make_monitor_plot(r1, t_range, r2)
        return dcc.Loading(
            dcc.Graph(figure=fig, id="monitor-graph",
                      config={"displayModeBar": False},
                      style={"height": "700px"}),
            color="#0ea5e9", type="circle",
        )

    elif active_tab == "pv-loop":
        fig = make_pv_loop(r1, r2)
        pv_graph = dcc.Loading(
            dcc.Graph(figure=fig, id="pv-loop-graph",
                      config={"displayModeBar": False},
                      style={"height": "480px"}),
            color="#0ea5e9", type="circle",
        )
        education = html.Div([
            html.H6("Pressure–Volume Loop", className="fw-bold mb-2",
                    style={"color": "#0ea5e9"}),
            html.P("The PV loop traces LV pressure vs. volume over one complete cardiac cycle.",
                   className="text-muted", style={"fontSize": "0.82rem"}),
            html.Hr(style={"borderColor": "rgba(148,163,184,0.15)"}),
            html.Div([
                html.Div("① Isovolumic Contraction",
                         style={"fontSize": "0.78rem", "fontWeight": 600, "color": "#e2e8f0"}),
                html.Div("Mitral & aortic valves closed. Pressure rises steeply.",
                         className="text-muted mb-2", style={"fontSize": "0.75rem"}),
                html.Div("② Ejection",
                         style={"fontSize": "0.78rem", "fontWeight": 600, "color": "#e2e8f0"}),
                html.Div("Aortic valve opens. Volume falls as blood is ejected.",
                         className="text-muted mb-2", style={"fontSize": "0.75rem"}),
                html.Div("③ Isovolumic Relaxation",
                         style={"fontSize": "0.78rem", "fontWeight": 600, "color": "#e2e8f0"}),
                html.Div("Aortic valve closes. Pressure drops at constant volume.",
                         className="text-muted mb-2", style={"fontSize": "0.75rem"}),
                html.Div("④ Filling",
                         style={"fontSize": "0.78rem", "fontWeight": 600, "color": "#e2e8f0"}),
                html.Div("Mitral valve opens. Volume increases along EDPVR.",
                         className="text-muted mb-3", style={"fontSize": "0.75rem"}),
            ]),
            html.Hr(style={"borderColor": "rgba(148,163,184,0.15)"}),
            html.Div([
                html.Div("ESPVR  —  end-systolic pressure–volume relationship (dashed)",
                         style={"fontSize": "0.75rem", "color": "#64748b", "marginBottom": "0.3rem"}),
                html.Div("EDPVR  —  diastolic filling curve (dotted)",
                         style={"fontSize": "0.75rem", "color": "#64748b", "marginBottom": "0.3rem"}),
                html.Div("Loop area  =  stroke work (external cardiac work per beat)",
                         style={"fontSize": "0.75rem", "color": "#64748b"}),
            ]),
            (html.Div([
                html.Hr(style={"borderColor": "rgba(148,163,184,0.15)"}),
                html.Div("Comparison mode: ESPVR/EDPVR shown for primary condition only.",
                         style={"fontSize": "0.75rem", "color": "#64748b"}),
            ]) if r2 else html.Div()),
        ], style={"padding": "0.5rem 1rem"})

        return dbc.Row([
            dbc.Col(pv_graph, md=7),
            dbc.Col(education, md=5,
                    style={"borderLeft": "1px solid rgba(148,163,184,0.12)",
                           "overflowY": "auto", "maxHeight": "520px"}),
        ])

    elif active_tab == "all-vars":
        default_vars = [0, 4, 6, 11]
        var_options  = [
            {"label": f"X{i+1}: {STATE_LABELS[i][0]}", "value": i}
            for i in range(12)
        ]
        return html.Div([
            html.Div([
                html.Label("Select state variables:", className="text-muted me-2",
                           style={"fontSize": "0.82rem"}),
                dcc.Dropdown(
                    id="var-select",
                    options=var_options,
                    value=default_vars,
                    multi=True,
                    clearable=False,
                    style={"fontSize": "0.82rem", "minWidth": "400px"},
                ),
            ], className="d-flex align-items-center mb-3"),
            dcc.Loading(
                html.Div(id="all-vars-container"),
                color="#0ea5e9", type="circle",
            ),
        ])

    elif active_tab == "export":
        def export_section(label, prefix, r, suffix=""):
            return dbc.Card([
                dbc.CardHeader(label),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col(dbc.Button(
                            [html.I(className="bi bi-file-earmark-spreadsheet me-2"),
                             "Waveform Data"],
                            id=f"btn-wave{suffix}", n_clicks=0,
                            outline=True, color="secondary",
                            className="w-100 export-btn",
                        ), md=4, className="mb-2"),
                        dbc.Col(dbc.Button(
                            [html.I(className="bi bi-activity me-2"), "PV Loop Data"],
                            id=f"btn-pv{suffix}", n_clicks=0,
                            outline=True, color="secondary",
                            className="w-100 export-btn",
                        ), md=4, className="mb-2"),
                        dbc.Col(dbc.Button(
                            [html.I(className="bi bi-table me-2"), "Full Simulation"],
                            id=f"btn-full{suffix}", n_clicks=0,
                            outline=True, color="secondary",
                            className="w-100 export-btn",
                        ), md=4, className="mb-2"),
                    ]),
                ]),
            ], className="mb-3")

        children = [export_section(f"Primary: {r1['preset']}", "1", r1, "1")]
        if r2:
            children.append(export_section(f"Comparison: {r2['preset']}", "2", r2, "2"))
        else:
            children.append(dbc.Card([
                dbc.CardBody(
                    html.P("Enable Compare Two Conditions to export a second dataset.",
                           className="text-muted mb-0", style={"fontSize": "0.85rem"}),
                )
            ], className="mb-3"))

        children.append(html.Div([
            html.Small([
                html.I(className="bi bi-info-circle me-1"),
                "Waveform data covers the current plot window. "
                "Full simulation exports all time points.",
            ], className="text-muted"),
        ]))
        return html.Div(children)

    return html.Div()


# 8. All Variables graph update
@app.callback(
    Output("all-vars-container", "children"),
    Input("var-select",           "value"),
    State("sim-result-1",         "data"),
    State("sim-result-2",         "data"),
    State("plot-window-slider",   "value"),
    State("compare-mode-store",   "data"),
    prevent_initial_call=False,
)
def update_all_vars(var_select, data1, data2, plot_window, compare_on):
    if data1 is None or not var_select:
        return html.Div()
    r1 = deserialize_result(data1)
    r2 = deserialize_result(data2) if compare_on and data2 else None
    t_end   = r1["t"][-1]
    t_start = max(0.0, t_end - plot_window)
    fig = make_all_variables(r1, [t_start, t_end], sorted(var_select), r2)
    h   = max(200 * len(var_select), 300)
    return dcc.Graph(figure=fig, config={"displayModeBar": False},
                     style={"height": f"{h}px"})


# ─────────────────────────────────────────────────────────────
# Export callbacks
# ─────────────────────────────────────────────────────────────
def _make_waveform_df(r, t_start, t_end):
    t = r["t"]; X = r["X"]; m = r["metrics"]
    idx = np.where((t >= t_start) & (t <= t_end))[0]
    d = {"Time (s)": t[idx]}
    for i, (name, unit) in enumerate(STATE_LABELS):
        d[f"X{i+1}: {name} ({unit})"] = X[idx, i]
    d["ECG (mV)"]          = r["ecg"][idx]
    d["LV Pressure (mmHg)"] = m["lvp_full"][idx]
    d["LV Outflow (cm³/s)"] = m["lvof"][idx]
    return pd.DataFrame(d)


def _make_pv_df(r):
    return pd.DataFrame({
        "LV Volume (cm³)":   r["metrics"]["lv_vol"],
        "LV Pressure (mmHg)": r["metrics"]["lvp"],
    })


def _make_full_df(r):
    t = r["t"]; X = r["X"]
    d = {"Time (s)": t}
    for i, (name, unit) in enumerate(STATE_LABELS):
        d[f"X{i+1}: {name} ({unit})"] = X[:, i]
    return pd.DataFrame(d)


def _slug(preset):
    return preset.lower().replace(" ", "_").replace("(", "").replace(")", "")


@app.callback(
    Output("dl-wave1", "data"),
    Input("btn-wave1", "n_clicks"),
    State("sim-result-1",       "data"),
    State("plot-window-slider", "value"),
    prevent_initial_call=True,
)
def dl_wave1(n, data1, pw):
    if not data1: return no_update
    r = deserialize_result(data1)
    t_end = r["t"][-1]; t_start = max(0, t_end - pw)
    return dcc.send_data_frame(_make_waveform_df(r, t_start, t_end).to_csv,
                               f"cardiosim_{_slug(r['preset'])}_waveforms.csv", index=False)


@app.callback(
    Output("dl-pv1", "data"),
    Input("btn-pv1", "n_clicks"),
    State("sim-result-1", "data"),
    prevent_initial_call=True,
)
def dl_pv1(n, data1):
    if not data1: return no_update
    r = deserialize_result(data1)
    return dcc.send_data_frame(_make_pv_df(r).to_csv,
                               f"cardiosim_{_slug(r['preset'])}_pvloop.csv", index=False)


@app.callback(
    Output("dl-full1", "data"),
    Input("btn-full1", "n_clicks"),
    State("sim-result-1", "data"),
    prevent_initial_call=True,
)
def dl_full1(n, data1):
    if not data1: return no_update
    r = deserialize_result(data1)
    return dcc.send_data_frame(_make_full_df(r).to_csv,
                               f"cardiosim_{_slug(r['preset'])}_full.csv", index=False)


@app.callback(
    Output("dl-wave2", "data"),
    Input("btn-wave2", "n_clicks"),
    State("sim-result-2",       "data"),
    State("plot-window-slider", "value"),
    prevent_initial_call=True,
)
def dl_wave2(n, data2, pw):
    if not data2: return no_update
    r = deserialize_result(data2)
    t_end = r["t"][-1]; t_start = max(0, t_end - pw)
    return dcc.send_data_frame(_make_waveform_df(r, t_start, t_end).to_csv,
                               f"cardiosim_{_slug(r['preset'])}_waveforms.csv", index=False)


@app.callback(
    Output("dl-pv2", "data"),
    Input("btn-pv2", "n_clicks"),
    State("sim-result-2", "data"),
    prevent_initial_call=True,
)
def dl_pv2(n, data2):
    if not data2: return no_update
    r = deserialize_result(data2)
    return dcc.send_data_frame(_make_pv_df(r).to_csv,
                               f"cardiosim_{_slug(r['preset'])}_pvloop.csv", index=False)


@app.callback(
    Output("dl-full2", "data"),
    Input("btn-full2", "n_clicks"),
    State("sim-result-2", "data"),
    prevent_initial_call=True,
)
def dl_full2(n, data2):
    if not data2: return no_update
    r = deserialize_result(data2)
    return dcc.send_data_frame(_make_full_df(r).to_csv,
                               f"cardiosim_{_slug(r['preset'])}_full.csv", index=False)


# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=8050)
