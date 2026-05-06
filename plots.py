# Copyright (c) 2025 Artemii Remizov
# Licensed under CC BY-NC 4.0 — https://creativecommons.org/licenses/by-nc/4.0/
#
# Plotly figure factories — all visualization logic, no UI imports.

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from model import STATE_LABELS

COLORS = {
    "aortic":    "#ef4444",
    "lvp":       "#f59e0b",
    "venous":    "#3b82f6",
    "pulm":      "#a78bfa",
    "ecg":       "#10b981",
    "volume":    "#818cf8",
    "comp1":     "#38bdf8",
    "comp2":     "#fb7185",
    "comp1_dim": "rgba(56,189,248,0.35)",
    "comp2_dim": "rgba(251,113,133,0.35)",
    "pv":        "#38bdf8",
    "espvr":     "#64748b",
    "edpvr":     "#64748b",
    "grid":      "rgba(148,163,184,0.15)",
    "text":      "#94a3b8",
}

_LAYOUT_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(15,23,42,0.6)",
    font=dict(color="#94a3b8", family="Inter, system-ui, sans-serif", size=12),
    margin=dict(l=58, r=20, t=38, b=42),
    hovermode="x unified",
    legend=dict(
        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
        bgcolor="rgba(0,0,0,0)", bordercolor="rgba(148,163,184,0.2)", borderwidth=1,
        font=dict(size=11),
    ),
)

_AXIS_STYLE = dict(showgrid=True, gridcolor=COLORS["grid"], gridwidth=1,
                   zeroline=False, linecolor="rgba(148,163,184,0.2)")


def make_monitor_plot(result, t_range, result2=None):
    """4-panel hemodynamic monitor: ECG, arterial, venous/pulmonary, LV volume."""
    has_comp = result2 is not None

    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True,
        vertical_spacing=0.055,
        row_heights=[0.22, 0.30, 0.22, 0.26],
        subplot_titles=["ECG  (Lead II)", "Arterial Pressures",
                        "Venous & Pulmonary", "Left Ventricular Volume"],
    )

    def _add_traces(res, is_primary):
        t = res["t"]; X = res["X"]; ecg = res["ecg"]; m = res["metrics"]
        idx = np.where((t >= t_range[0]) & (t <= t_range[1]))[0]
        ti = t[idx]
        label = res["preset"]

        if has_comp:
            c  = COLORS["comp1"] if is_primary else COLORS["comp2"]
            cd = COLORS["comp1_dim"] if is_primary else COLORS["comp2_dim"]
            fig.add_trace(go.Scatter(x=ti, y=ecg[idx], mode='lines',
                name=label, legendgroup=label, showlegend=True,
                line=dict(color=c, width=1.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=ti, y=X[idx, 0], mode='lines',
                name=f'Aortic ({label})', legendgroup=label, showlegend=False,
                line=dict(color=c, width=2)), row=2, col=1)
            fig.add_trace(go.Scatter(x=ti, y=m["lvp_full"][idx], mode='lines',
                name=f'LV Pres ({label})', legendgroup=label, showlegend=False,
                line=dict(color=cd, width=1.2)), row=2, col=1)
            fig.add_trace(go.Scatter(x=ti, y=X[idx, 4], mode='lines',
                name=f'Venous ({label})', legendgroup=label, showlegend=False,
                line=dict(color=c, width=1.5)), row=3, col=1)
            fig.add_trace(go.Scatter(x=ti, y=X[idx, 6], mode='lines',
                name=f'Pulm ({label})', legendgroup=label, showlegend=False,
                line=dict(color=cd, width=1.3)), row=3, col=1)
            fill_c = "rgba(56,189,248,0.06)" if is_primary else None
            fig.add_trace(go.Scatter(x=ti, y=X[idx, 11], mode='lines',
                name=f'LV Vol ({label})', legendgroup=label, showlegend=False,
                line=dict(color=c, width=1.5),
                fill='tozeroy' if is_primary else None,
                fillcolor=fill_c), row=4, col=1)
        else:
            fig.add_trace(go.Scatter(x=ti, y=ecg[idx], mode='lines', name='ECG',
                line=dict(color=COLORS["ecg"], width=1.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=ti, y=X[idx, 0], mode='lines', name='Aortic Pressure',
                line=dict(color=COLORS["aortic"], width=2)), row=2, col=1)
            fig.add_trace(go.Scatter(x=ti, y=m["lvp_full"][idx], mode='lines', name='LV Pressure',
                line=dict(color=COLORS["lvp"], width=1.2, dash='dot')), row=2, col=1)
            fig.add_trace(go.Scatter(x=ti, y=X[idx, 4], mode='lines', name='Systemic Venous',
                line=dict(color=COLORS["venous"], width=1.5)), row=3, col=1)
            fig.add_trace(go.Scatter(x=ti, y=X[idx, 6], mode='lines', name='Pulmonary Artery',
                line=dict(color=COLORS["pulm"], width=1.5)), row=3, col=1)
            fig.add_trace(go.Scatter(x=ti, y=X[idx, 11], mode='lines', name='LV Volume',
                line=dict(color=COLORS["volume"], width=1.8),
                fill='tozeroy', fillcolor='rgba(129,140,248,0.08)'), row=4, col=1)

    _add_traces(result, is_primary=True)
    if has_comp:
        _add_traces(result2, is_primary=False)

    fig.update_layout(**_LAYOUT_BASE, height=700, showlegend=True)
    fig.update_xaxes(**_AXIS_STYLE, title_text="Time (s)", row=4, col=1,
                     range=[t_range[0], t_range[1]])
    for row in range(1, 5):
        fig.update_xaxes(**_AXIS_STYLE, row=row, col=1)
        fig.update_yaxes(**_AXIS_STYLE, row=row, col=1)
    fig.update_yaxes(title_text="mV",   row=1, col=1)
    fig.update_yaxes(title_text="mmHg", row=2, col=1)
    fig.update_yaxes(title_text="mmHg", row=3, col=1)
    fig.update_yaxes(title_text="cm³",  row=4, col=1)
    for ann in fig['layout']['annotations']:
        ann['font'] = dict(size=12, color=COLORS["text"])
    return fig


def make_pv_loop(result, result2=None):
    """PV loop with ESPVR/EDPVR reference lines, ESV/EDV markers, filled stroke work."""
    fig = go.Figure()
    has_comp = result2 is not None

    def _add_loop(res, is_primary):
        m = res["metrics"]
        if len(m["lv_vol"]) < 3:
            return
        vol = m["lv_vol"]
        pres = m["lvp"]
        name = res["preset"]
        esv = np.min(vol)
        edv = np.max(vol)

        near_esv = np.where(vol < esv + 0.02 * (edv - esv))[0]
        esp_idx  = near_esv[np.argmax(pres[near_esv])]
        esp      = pres[esp_idx]

        near_edv = np.where(vol > edv - 0.02 * (edv - esv))[0]
        edp_idx  = near_edv[np.argmax(pres[near_edv])]
        edp      = pres[edp_idx]

        vol_c  = np.append(vol, vol[0])
        pres_c = np.append(pres, pres[0])

        if has_comp:
            color      = COLORS["comp1"] if is_primary else COLORS["comp2"]
            fill_color = "rgba(56,189,248,0.10)" if is_primary else "rgba(251,113,133,0.10)"
        else:
            color      = COLORS["pv"]
            fill_color = "rgba(56,189,248,0.08)"

        fig.add_trace(go.Scatter(
            x=vol_c, y=pres_c, mode='lines', name=name,
            line=dict(color=color, width=2.5),
            fill='toself', fillcolor=fill_color,
        ))
        fig.add_trace(go.Scatter(
            x=[esv], y=[esp], mode='markers+text',
            marker=dict(size=8, color=color, symbol='circle'),
            text=['ESV'], textposition='top left',
            textfont=dict(size=10, color=color),
            showlegend=False, hoverinfo='skip',
        ))
        fig.add_trace(go.Scatter(
            x=[edv], y=[edp], mode='markers+text',
            marker=dict(size=8, color=color, symbol='circle'),
            text=['EDV'], textposition='bottom right',
            textfont=dict(size=10, color=color),
            showlegend=False, hoverinfo='skip',
        ))

        if is_primary:
            v0 = 10
            ees = esp / (esv - v0) if esv > v0 else 1.0
            p_max_line = np.max(pres) * 1.3
            v_max_line = v0 + p_max_line / ees
            espvr_v = np.array([v0, min(v_max_line, edv + 5)])
            espvr_p = ees * (espvr_v - v0)
            fig.add_trace(go.Scatter(
                x=espvr_v, y=espvr_p, mode='lines', name='ESPVR',
                line=dict(color=COLORS["espvr"], width=1.2, dash='dash'),
                showlegend=not has_comp,
            ))
            eld     = res["params"]["ELD"]
            edpvr_v = np.linspace(max(v0, esv - 5), edv + 5, 50)
            edpvr_p = eld * edpvr_v
            fig.add_trace(go.Scatter(
                x=edpvr_v, y=edpvr_p, mode='lines', name='EDPVR',
                line=dict(color=COLORS["edpvr"], width=1.2, dash='dot'),
                showlegend=not has_comp,
            ))

    _add_loop(result, is_primary=True)
    if has_comp:
        _add_loop(result2, is_primary=False)

    all_pres = result["metrics"]["lvp"]
    y_max = np.max(all_pres) * 1.15 if len(all_pres) > 0 else 200
    if has_comp and len(result2["metrics"]["lvp"]) > 0:
        y_max = max(y_max, np.max(result2["metrics"]["lvp"]) * 1.15)

    fig.update_layout(
        **_LAYOUT_BASE,
        height=480,
        xaxis_title="LV Volume (cm³)",
        yaxis_title="LV Pressure (mmHg)",
        yaxis=dict(**_AXIS_STYLE, range=[0, y_max]),
        xaxis=dict(**_AXIS_STYLE),
    )
    return fig


def make_all_variables(result, t_range, var_select, result2=None):
    """Plot selected state variables in stacked subplots."""
    if not var_select:
        return go.Figure()

    palette = ["#ef4444", "#f59e0b", "#10b981", "#3b82f6", "#a78bfa",
               "#ec4899", "#6366f1", "#06b6d4", "#f97316", "#eab308",
               "#64748b", "#0ea5e9"]

    fig = make_subplots(
        rows=len(var_select), cols=1, shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=[f"X{i+1}: {STATE_LABELS[i][0]}" for i in var_select],
    )
    has_comp = result2 is not None

    def _add(res, is_primary):
        t = res["t"]; X = res["X"]
        idx = np.where((t >= t_range[0]) & (t <= t_range[1]))[0]
        label = res["preset"]
        for row, vi in enumerate(var_select):
            c = (COLORS["comp1"] if is_primary else COLORS["comp2"]) if has_comp else palette[vi]
            fig.add_trace(go.Scatter(
                x=t[idx], y=X[idx, vi], mode='lines',
                name=label if has_comp else STATE_LABELS[vi][0],
                line=dict(color=c, width=1.5),
                showlegend=(row == 0) if has_comp else False,
                legendgroup=label if has_comp else None,
            ), row=row + 1, col=1)

    _add(result, is_primary=True)
    if has_comp:
        _add(result2, is_primary=False)

    for row, vi in enumerate(var_select):
        fig.update_yaxes(title_text=STATE_LABELS[vi][1], **_AXIS_STYLE, row=row + 1, col=1)
        fig.update_xaxes(**_AXIS_STYLE, row=row + 1, col=1)

    fig.update_layout(
        **_LAYOUT_BASE,
        height=max(200 * len(var_select), 300),
        showlegend=has_comp,
    )
    fig.update_xaxes(title_text="Time (s)", row=len(var_select), col=1)
    for ann in fig['layout']['annotations']:
        ann['font'] = dict(size=11, color=COLORS["text"])
    return fig
