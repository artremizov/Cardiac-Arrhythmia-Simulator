# Copyright (c) 2025 Artemii Remizov
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)
# https://creativecommons.org/licenses/by-nc/4.0/
#
# Cardiovascular Simulator v2.0
# Based on Avanzolini et al. (1988) lumped-parameter model
# With synthetic ECG generation (McSharry et al. 2003)

import streamlit as st
import numpy as np
from scipy.integrate import solve_ivp
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

# ═══════════════════════════════════════════════════════════
# PAGE CONFIG & CUSTOM STYLING
# ═══════════════════════════════════════════════════════════
st.set_page_config(
    layout="wide",
    page_title="CardioSim — Cardiovascular Simulator",
)

CUSTOM_CSS = """
<style>
    /* ── Global ── */
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }

    /* ── Metric cards ── */
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #0f3460;
        border-radius: 12px;
        padding: 1.1rem 1.2rem;
        text-align: center;
        transition: transform 0.2s ease;
    }
    .metric-card:hover { transform: translateY(-2px); }
    .metric-label {
        color: #8892b0;
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.25rem;
    }
    .metric-value {
        font-size: 1.75rem;
        font-weight: 700;
        margin-bottom: 0.1rem;
        font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
    }
    .metric-unit {
        color: #8892b0;
        font-size: 0.72rem;
    }
    .metric-normal { color: #64ffda; }
    .metric-warning { color: #ffd93d; }
    .metric-danger { color: #ff6b6b; }

    /* ── Preset cards ── */
    .preset-info {
        background: #1a1a2e;
        border-left: 3px solid #0f3460;
        border-radius: 0 8px 8px 0;
        padding: 0.8rem 1rem;
        margin: 0.5rem 0;
        font-size: 0.82rem;
        line-height: 1.5;
    }

    /* ── Section headers ── */
    .section-header {
        font-size: 0.85rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #64ffda;
        padding-bottom: 0.4rem;
        border-bottom: 1px solid #233554;
        margin-bottom: 0.8rem;
    }

    /* ── Comparison badge ── */
    .comparison-badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 20px;
        font-size: 0.7rem;
        font-weight: 600;
    }
    .badge-up { background: rgba(255, 107, 107, 0.15); color: #ff6b6b; }
    .badge-down { background: rgba(100, 255, 218, 0.15); color: #64ffda; }

    /* ── Hide Streamlit branding ── */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* ── Sidebar polish ── */
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 1rem;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# MODEL PARAMETERS
# ═══════════════════════════════════════════════════════════
BASELINE_PARAMS = {
    "Tc": 0.8, "ULO": 50.0, "URO": 24.0,
    "ELD": 0.1, "ELS": 1.375, "ERD": 0.03, "ERS": 0.3288,
    "RL": 0.08, "RR": 0.0175,
    "R1": 0.003751, "R2": 0.0675, "R3": 1.0, "R4": 0.003751,
    "R5": 0.003751, "R6": 0.03376, "R7": 0.1013, "R8": 0.003751,
    "L1": 0.000825, "L2": 0.0036, "L3": 0.00075, "L4": 0.00308,
    "C1": 0.22, "C2": 1.46, "C3": 20.0, "C4": 0.09, "C5": 2.67, "C6": 46.7,
    "X0": [71.13, 8.89, 70.54, 67.36, 3.33, 105.46,
           13.42, 0.79, 13.39, 23.83, 11.30, 112.76],
}

STATE_LABELS = [
    ("Aortic Pressure", "mmHg"),
    ("Aortic Flow", "cm³/s"),
    ("Systemic Arterial Pressure", "mmHg"),
    ("Systemic Peripheral Flow", "cm³/s"),
    ("Systemic Venous Pressure", "mmHg"),
    ("Right Ventricle Volume", "cm³"),
    ("Pulmonary Artery Pressure", "mmHg"),
    ("Pulmonary Arterial Flow", "cm³/s"),
    ("Pulmonary Arteriole Pressure", "mmHg"),
    ("Pulmonary Venous Flow", "cm³/s"),
    ("Pulmonary Venous / LA Pressure", "mmHg"),
    ("Left Ventricle Volume", "cm³"),
]

CLINICAL_PRESETS = {
    "Healthy Adult": {
        "hr": 75, "contract": 100, "resist": 1.0, "compl": 1.46,
        "icon": "",
        "desc": "Normal resting cardiovascular function. HR ~75 bpm, cardiac output ~5–6 L/min, systolic pressure ~120 mmHg.",
        "category": "normal",
    },
    "Ventricular Fibrillation": {
        "hr": 350, "contract": 25, "resist": 1.0, "compl": 1.46,
        "icon": "",
        "desc": "Chaotic ventricular depolarization at 300–400 bpm with severely reduced contractility. Immediately life-threatening — cardiac output drops >60%.",
        "category": "critical",
    },
    "Ventricular Tachycardia": {
        "hr": 180, "contract": 60, "resist": 1.0, "compl": 1.46,
        "icon": "",
        "desc": "Rapid ventricular rhythm at 150–250 bpm originating below the AV node. Reduced filling time compromises cardiac output.",
        "category": "arrhythmia",
    },
    "Atrial Fibrillation": {
        "hr": 130, "contract": 85, "resist": 1.0, "compl": 1.46,
        "icon": "",
        "desc": "Irregularly irregular rhythm with loss of atrial contraction. Simulated with variable R-R intervals and reduced ventricular filling.",
        "category": "arrhythmia",
    },
    "Sinus Tachycardia": {
        "hr": 120, "contract": 100, "resist": 1.0, "compl": 1.46,
        "icon": "",
        "desc": "Elevated heart rate from physiological causes (exercise, stress, fever). Normal conduction pathway, rate >100 bpm.",
        "category": "arrhythmia",
    },
    "Sinus Bradycardia": {
        "hr": 50, "contract": 100, "resist": 1.0, "compl": 1.46,
        "icon": "",
        "desc": "Slower-than-normal sinus rhythm (<60 bpm). Common in athletes. Stroke volume compensates via longer filling time.",
        "category": "arrhythmia",
    },
    "Heart Failure (Systolic)": {
        "hr": 90, "contract": 55, "resist": 1.2, "compl": 1.46,
        "icon": "",
        "desc": "Reduced ejection fraction (HFrEF). Weakened myocardial contractility with compensatory increase in heart rate and peripheral resistance.",
        "category": "structural",
    },
    "Hypertension": {
        "hr": 80, "contract": 110, "resist": 1.5, "compl": 1.1,
        "icon": "",
        "desc": "Chronically elevated systemic vascular resistance with reduced arterial compliance (stiffened vessels). LV hypertrophy increases contractility.",
        "category": "structural",
    },
    "Aortic Stenosis": {
        "hr": 80, "contract": 120, "resist": 1.0, "compl": 1.46,
        "icon": "",
        "desc": "Narrowed aortic valve increases outflow resistance. LV compensates with hypertrophy. Simulated via increased aortic valve resistance and contractility.",
        "category": "structural",
        "extra": {"R1": 0.05},
    },
    "Hemorrhagic Shock": {
        "hr": 130, "contract": 90, "resist": 1.6, "compl": 1.46,
        "icon": "",
        "desc": "Acute blood loss triggers compensatory tachycardia and vasoconstriction. Reduced preload causes low stroke volume despite elevated heart rate.",
        "category": "critical",
        "x0_overrides": {4: 2.0, 5: 75.0, 10: 7.0, 11: 80.0},
    },
}


# ═══════════════════════════════════════════════════════════
# CORE HEMODYNAMIC MODEL (Avanzolini 1988)
# ═══════════════════════════════════════════════════════════
def cardiovascular_model(t, X, p, rr_intervals=None):
    """
    12-ODE lumped-parameter cardiovascular model.
    Supports optional stochastic R-R intervals for arrhythmia simulation.
    """
    X1, X2, X3, X4, X5, X6, X7, X8, X9, X10, X11, X12 = X

    # Determine current cardiac phase with optional irregular R-R
    Tc = p["Tc"]
    if rr_intervals is not None and len(rr_intervals) > 0:
        # Walk through accumulated beat times to find current beat
        cum_t = 0.0
        beat_idx = 0
        while beat_idx < len(rr_intervals) and cum_t + rr_intervals[beat_idx] <= t:
            cum_t += rr_intervals[beat_idx]
            beat_idx += 1
        if beat_idx < len(rr_intervals):
            Tc = rr_intervals[beat_idx]
        Tm = t - cum_t
    else:
        Tm = t % Tc

    Ts = 0.16 + 0.3 * Tc
    A = (1 - np.cos(2 * np.pi * Tm / Ts)) / 2 if Tm < Ts else 0

    UL = p["ULO"] * A
    UR = p["URO"] * A
    EL = p["ELD"] + p["ELS"] * A
    ER = p["ERD"] + p["ERS"] * A

    Z1 = UL + X12 * EL - X1
    Z2 = X5 - (UR + X6 * ER)
    Z3 = UR + X6 * ER - X7
    Z4 = X11 - (UL + X12 * EL)

    S1 = float(Z1 > 0)
    S2 = float(Z2 > 0)
    S3 = float(Z3 > 0)
    S4 = float(Z4 > 0)

    dX = np.zeros(12)
    dX[0]  = (S1 * Z1 / (p["RL"] + p["R1"]) - X2) / p["C1"]
    dX[1]  = (X1 - p["R2"] * X2 - X3) / p["L1"]
    dX[2]  = (X2 - X4) / p["C2"]
    dX[3]  = (X3 - p["R3"] * X4 - X5) / p["L2"]
    dX[4]  = (X4 - S2 * Z2 / p["R4"]) / p["C3"]
    dX[5]  = S2 * Z2 / p["R4"] - S3 * Z3 / (p["RR"] + p["R5"])
    dX[6]  = (S3 * Z3 / (p["RR"] + p["R5"]) - X8) / p["C4"]
    dX[7]  = (X7 - p["R6"] * X8 - X9) / p["L3"]
    dX[8]  = (X8 - X10) / p["C5"]
    dX[9]  = (X9 - p["R7"] * X10 - X11) / p["L4"]
    dX[10] = (X10 - S4 * Z4 / p["R8"]) / p["C6"]
    dX[11] = S4 * Z4 / p["R8"] - S1 * Z1 / (p["RL"] + p["R1"])

    return dX


def generate_rr_intervals(preset_name, mean_hr, duration):
    """
    Generate R-R intervals for arrhythmia presets.
    Returns None for regular rhythms, array of intervals for irregular ones.
    """
    mean_rr = 60.0 / mean_hr

    if preset_name == "Atrial Fibrillation":
        # AF: irregularly irregular — use gamma distribution
        n_beats = int(duration / mean_rr * 1.5) + 20
        shape = 4.0  # controls irregularity (lower = more irregular)
        scale = mean_rr / shape
        intervals = np.random.gamma(shape, scale, n_beats)
        intervals = np.clip(intervals, 0.3, 1.5)
        return intervals

    elif preset_name == "Ventricular Fibrillation":
        # VF: chaotic, very rapid, variable
        n_beats = int(duration / mean_rr * 1.5) + 20
        intervals = np.random.uniform(0.12, 0.25, n_beats)
        return intervals

    return None  # Regular rhythm


# ═══════════════════════════════════════════════════════════
# SYNTHETIC ECG GENERATION (McSharry et al. 2003 inspired)
# ═══════════════════════════════════════════════════════════
def generate_synthetic_ecg(t, p, rr_intervals=None, preset_name="Healthy Adult"):
    """
    Generate a synthetic ECG trace synchronized to the hemodynamic model timing.
    Uses sum-of-Gaussians approach for PQRST morphology.
    """
    ecg = np.zeros(len(t))
    Tc = p["Tc"]

    # PQRST Gaussian parameters: (amplitude, center_frac_of_Tc, width_frac_of_Tc)
    # These define the shape of each ECG wave within a single beat
    if preset_name == "Ventricular Fibrillation":
        # VF: chaotic low-amplitude oscillations, no discernible PQRST
        ecg = 0.15 * np.sin(2 * np.pi * 5.5 * t) * np.sin(2 * np.pi * 0.3 * t)
        ecg += 0.08 * np.sin(2 * np.pi * 7.2 * t + 1.2)
        ecg += np.random.normal(0, 0.03, len(t))
        return ecg

    # Normal PQRST morphology parameters
    waves = [
        (0.10,  0.10, 0.035),  # P wave
        (-0.08, 0.17, 0.012),  # Q wave
        (1.00,  0.20, 0.018),  # R wave
        (-0.20, 0.23, 0.015),  # S wave
        (0.25,  0.38, 0.055),  # T wave
    ]

    # Adjust morphology based on condition
    if preset_name == "Ventricular Tachycardia":
        waves = [
            (0.02,  0.08, 0.02),   # Tiny/absent P
            (-0.15, 0.15, 0.025),  # Wide Q
            (0.80,  0.22, 0.04),   # Wide bizarre QRS
            (-0.35, 0.32, 0.035),  # Deep S
            (0.30,  0.55, 0.07),   # Discordant T
        ]
    elif preset_name == "Atrial Fibrillation":
        waves = [
            (0.0,   0.10, 0.03),   # No P wave
            (-0.08, 0.17, 0.012),  # Normal Q
            (1.00,  0.20, 0.018),  # Normal R
            (-0.18, 0.23, 0.015),  # Normal S
            (0.22,  0.38, 0.055),  # Normal T
        ]
    elif "Heart Failure" in preset_name:
        waves = [
            (0.08,  0.10, 0.04),   # Widened P
            (-0.06, 0.17, 0.012),  # Q
            (0.70,  0.20, 0.022),  # Reduced R
            (-0.15, 0.23, 0.015),  # S
            (0.15,  0.40, 0.065),  # Flattened T
        ]
    elif preset_name == "Hypertension":
        waves = [
            (0.12,  0.10, 0.04),   # Tall P (LAE)
            (-0.10, 0.17, 0.012),  # Deep Q
            (1.20,  0.20, 0.020),  # Tall R (LVH)
            (-0.30, 0.24, 0.018),  # Deep S
            (-0.15, 0.40, 0.060),  # Inverted T (strain)
        ]

    # Build ECG beat by beat
    if rr_intervals is not None and len(rr_intervals) > 0:
        cum_t = 0.0
        beat_idx = 0
        for i, ti in enumerate(t):
            while beat_idx < len(rr_intervals) - 1 and cum_t + rr_intervals[beat_idx] <= ti:
                cum_t += rr_intervals[beat_idx]
                beat_idx += 1
            current_rr = rr_intervals[min(beat_idx, len(rr_intervals) - 1)]
            phase = (ti - cum_t) / current_rr
            if phase < 0: phase = 0
            if phase > 1: phase = 1
            for amp, center, width in waves:
                ecg[i] += amp * np.exp(-0.5 * ((phase - center) / width) ** 2)
    else:
        for i, ti in enumerate(t):
            phase = (ti % Tc) / Tc
            for amp, center, width in waves:
                ecg[i] += amp * np.exp(-0.5 * ((phase - center) / width) ** 2)

    # Add fibrillatory baseline for AF
    if preset_name == "Atrial Fibrillation":
        ecg += 0.04 * np.sin(2 * np.pi * 6.5 * t + np.random.uniform(0, 2 * np.pi))
        ecg += 0.03 * np.sin(2 * np.pi * 8.1 * t + np.random.uniform(0, 2 * np.pi))

    # Add realistic noise
    ecg += np.random.normal(0, 0.012, len(t))

    return ecg


# ═══════════════════════════════════════════════════════════
# ANALYSIS FUNCTIONS
# ═══════════════════════════════════════════════════════════
def calculate_metrics(t, X, p, rr_intervals=None):
    """Calculate hemodynamic metrics from the last stable cardiac cycle."""
    n = len(t)
    LVOF = np.zeros(n)
    LVP = np.zeros(n)
    Tc = p["Tc"]

    for i in range(n):
        if rr_intervals is not None and len(rr_intervals) > 0:
            cum = 0.0
            bi = 0
            while bi < len(rr_intervals) and cum + rr_intervals[bi] <= t[i]:
                cum += rr_intervals[bi]
                bi += 1
            if bi < len(rr_intervals):
                Tc_local = rr_intervals[bi]
            else:
                Tc_local = Tc
            Tm = t[i] - cum
        else:
            Tc_local = Tc
            Tm = t[i] % Tc_local

        Ts = 0.16 + 0.3 * Tc_local
        A = (1 - np.cos(2 * np.pi * Tm / Ts)) / 2 if Tm < Ts else 0
        UL = p["ULO"] * A
        EL = p["ELD"] + p["ELS"] * A
        Z1 = UL + X[i, 11] * EL - X[i, 0]
        S1 = float(Z1 > 0)
        LVOF[i] = Z1 * S1 / (p["RL"] + p["R1"])
        LVP[i] = UL + EL * X[i, 11] - p["RL"] * LVOF[i]

    # Extract last stable beat
    end_t = t[-1]
    effective_tc = np.mean(rr_intervals[-10:]) if rr_intervals is not None else Tc
    if end_t < 2 * effective_tc:
        return dict(co=0, sv=0, sys=0, dia=0, map_val=0, pp=0,
                    lv_vol=np.array([]), lvp=np.array([]),
                    lvof=LVOF, lvp_full=LVP)

    beat_start = max(t[0], end_t - 2 * effective_tc)
    beat_end = end_t - effective_tc
    idx = np.where((t >= beat_start) & (t < beat_end))[0]
    if len(idx) <= 1:
        return dict(co=0, sv=0, sys=0, dia=0, map_val=0, pp=0,
                    lv_vol=np.array([]), lvp=np.array([]),
                    lvof=LVOF, lvp_full=LVP)

    t_beat = t[idx]
    _trapz = np.trapezoid if hasattr(np, 'trapezoid') else np.trapz
    sv = _trapz(LVOF[idx], t_beat)
    hr = 60.0 / effective_tc
    co = sv * hr / 1000.0

    aop_beat = X[idx, 0]
    sys_p = np.max(aop_beat)
    dia_p = np.min(aop_beat)
    map_val = dia_p + (sys_p - dia_p) / 3.0
    pp = sys_p - dia_p

    return dict(
        co=co, sv=sv, sys=sys_p, dia=dia_p, map_val=map_val, pp=pp,
        lv_vol=X[idx, 11], lvp=LVP[idx],
        lvof=LVOF, lvp_full=LVP,
    )


def run_sim(params, duration, preset_name):
    """Run a single simulation and return all results."""
    rr = generate_rr_intervals(preset_name, 60.0 / params["Tc"], duration)
    t_span = [0, duration]
    t_eval = np.linspace(0, duration, int(duration * 600))

    sol = solve_ivp(
        lambda t, X: cardiovascular_model(t, X, params, rr),
        t_span, params["X0"], t_eval=t_eval,
        method='RK45', rtol=1e-5, atol=1e-8, max_step=0.005,
    )

    if sol.status != 0:
        return None

    t = sol.t
    X = sol.y.T
    metrics = calculate_metrics(t, X, params, rr)
    ecg = generate_synthetic_ecg(t, params, rr, preset_name)

    return dict(t=t, X=X, metrics=metrics, ecg=ecg, params=params,
                preset=preset_name, rr=rr)


# ═══════════════════════════════════════════════════════════
# PLOTLY VISUALIZATION
# ═══════════════════════════════════════════════════════════
COLORS = {
    "aortic": "#ff6b6b",
    "lvp": "#ffd93d",
    "venous": "#48bfe3",
    "pulm": "#64dfdf",
    "ecg": "#64ffda",
    "ecg2": "#ff9f43",
    "volume": "#a29bfe",
    "pv": "#6c5ce7",
    "grid": "rgba(255,255,255,0.06)",
    "bg": "rgba(0,0,0,0)",
    "text": "#ccd6f6",
    "muted": "#8892b0",
}

PLOT_LAYOUT = dict(
    paper_bgcolor=COLORS["bg"],
    plot_bgcolor="#0a192f",
    font=dict(color=COLORS["text"], family="Inter, system-ui, sans-serif", size=12),
    margin=dict(l=55, r=20, t=35, b=40),
    hovermode="x unified",
    legend=dict(
        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
        bgcolor="rgba(10,25,47,0.7)", borderwidth=0, font=dict(size=11),
    ),
)


def make_monitor_plot(result, t_range):
    """Create the main patient-monitor-style multi-panel plot."""
    t = result["t"]
    X = result["X"]
    ecg = result["ecg"]
    metrics = result["metrics"]
    idx = np.where((t >= t_range[0]) & (t <= t_range[1]))[0]
    ti = t[idx]

    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True,
        vertical_spacing=0.06,
        row_heights=[0.22, 0.30, 0.22, 0.26],
        subplot_titles=["ECG  (Lead II)", "Arterial Pressures", "Venous & Pulmonary", "Left Ventricular Volume"],
    )

    # Row 1 — ECG
    fig.add_trace(go.Scatter(
        x=ti, y=ecg[idx], mode='lines', name='ECG',
        line=dict(color=COLORS["ecg"], width=1.5),
        hovertemplate='%{y:.2f} mV<extra>ECG</extra>',
    ), row=1, col=1)

    # Row 2 — Aortic + LV Pressure
    fig.add_trace(go.Scatter(
        x=ti, y=X[idx, 0], mode='lines', name='Aortic Pressure',
        line=dict(color=COLORS["aortic"], width=2),
        hovertemplate='%{y:.1f} mmHg<extra>Aortic</extra>',
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=ti, y=metrics["lvp_full"][idx], mode='lines', name='LV Pressure',
        line=dict(color=COLORS["lvp"], width=1.5, dash='dot'),
        hovertemplate='%{y:.1f} mmHg<extra>LV</extra>',
    ), row=2, col=1)

    # Row 3 — Venous + Pulmonary
    fig.add_trace(go.Scatter(
        x=ti, y=X[idx, 4], mode='lines', name='Systemic Venous',
        line=dict(color=COLORS["venous"], width=1.5),
        hovertemplate='%{y:.1f} mmHg<extra>Venous</extra>',
    ), row=3, col=1)
    fig.add_trace(go.Scatter(
        x=ti, y=X[idx, 6], mode='lines', name='Pulmonary Artery',
        line=dict(color=COLORS["pulm"], width=1.5),
        hovertemplate='%{y:.1f} mmHg<extra>Pulmonary</extra>',
    ), row=3, col=1)

    # Row 4 — LV Volume
    fig.add_trace(go.Scatter(
        x=ti, y=X[idx, 11], mode='lines', name='LV Volume',
        line=dict(color=COLORS["volume"], width=2),
        fill='tozeroy', fillcolor='rgba(162,155,254,0.12)',
        hovertemplate='%{y:.1f} cm³<extra>LV Vol</extra>',
    ), row=4, col=1)

    fig.update_layout(
        **PLOT_LAYOUT,
        height=680,
        showlegend=True,
    )
    fig.update_xaxes(
        showgrid=True, gridcolor=COLORS["grid"], gridwidth=1,
        title_text="Time (s)", row=4, col=1,
        range=[t_range[0], t_range[1]],
    )
    for row in range(1, 5):
        fig.update_yaxes(showgrid=True, gridcolor=COLORS["grid"], gridwidth=1, row=row, col=1)
    fig.update_yaxes(title_text="mV", row=1, col=1)
    fig.update_yaxes(title_text="mmHg", row=2, col=1)
    fig.update_yaxes(title_text="mmHg", row=3, col=1)
    fig.update_yaxes(title_text="cm³", row=4, col=1)

    # Style subtitle annotations
    for ann in fig['layout']['annotations']:
        ann['font'] = dict(size=12, color=COLORS["muted"])

    return fig


def make_pv_loop(result, result2=None):
    """Create PV loop plot, optionally overlaid with a second condition."""
    m = result["metrics"]
    fig = go.Figure()

    if len(m["lv_vol"]) > 0:
        fig.add_trace(go.Scatter(
            x=m["lv_vol"], y=m["lvp"], mode='lines', name=result["preset"],
            line=dict(color=COLORS["pv"], width=2.5),
            fill='toself', fillcolor='rgba(108,92,231,0.08)',
        ))

    if result2 is not None:
        m2 = result2["metrics"]
        if len(m2["lv_vol"]) > 0:
            fig.add_trace(go.Scatter(
                x=m2["lv_vol"], y=m2["lvp"], mode='lines', name=result2["preset"],
                line=dict(color=COLORS["ecg2"], width=2.5, dash='dash'),
                fill='toself', fillcolor='rgba(255,159,67,0.06)',
            ))

    fig.update_layout(
        **PLOT_LAYOUT,
        height=420,
        xaxis_title="LV Volume (cm³)",
        yaxis_title="LV Pressure (mmHg)",
    )
    fig.update_xaxes(showgrid=True, gridcolor=COLORS["grid"])
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["grid"])

    return fig


def make_comparison_waveform(r1, r2, t_range):
    """Overlay two simulations on the same axes for comparison."""
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.35, 0.35, 0.30],
        subplot_titles=["ECG  (Lead II)", "Aortic Pressure", "Left Ventricular Volume"],
    )

    for result, color_set, dash in [
        (r1, (COLORS["ecg"], COLORS["aortic"], COLORS["volume"]), None),
        (r2, (COLORS["ecg2"], "#ff9f43", "#fdcb6e"), "dash"),
    ]:
        t = result["t"]
        X = result["X"]
        ecg = result["ecg"]
        idx = np.where((t >= t_range[0]) & (t <= t_range[1]))[0]
        ti = t[idx]
        label = result["preset"]
        ls = dict(width=1.8) if dash is None else dict(width=1.8, dash=dash)

        fig.add_trace(go.Scatter(
            x=ti, y=ecg[idx], mode='lines', name=f'{label}',
            line={**ls, "color": color_set[0]}, legendgroup=label,
            showlegend=True,
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=ti, y=X[idx, 0], mode='lines', name=f'{label}',
            line={**ls, "color": color_set[1]}, legendgroup=label,
            showlegend=False,
        ), row=2, col=1)
        fig.add_trace(go.Scatter(
            x=ti, y=X[idx, 11], mode='lines', name=f'{label}',
            line={**ls, "color": color_set[2]}, legendgroup=label,
            showlegend=False,
        ), row=3, col=1)

    fig.update_layout(**PLOT_LAYOUT, height=580)
    fig.update_xaxes(
        showgrid=True, gridcolor=COLORS["grid"],
        title_text="Time (s)", row=3, col=1,
        range=[t_range[0], t_range[1]],
    )
    for row in range(1, 4):
        fig.update_yaxes(showgrid=True, gridcolor=COLORS["grid"], row=row, col=1)
    fig.update_yaxes(title_text="mV", row=1, col=1)
    fig.update_yaxes(title_text="mmHg", row=2, col=1)
    fig.update_yaxes(title_text="cm³", row=3, col=1)
    for ann in fig['layout']['annotations']:
        ann['font'] = dict(size=12, color=COLORS["muted"])

    return fig


# ═══════════════════════════════════════════════════════════
# UI HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════
def metric_card(label, value, unit, status="normal"):
    """Render a styled metric card."""
    css_class = f"metric-{status}"
    return f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value {css_class}">{value}</div>
        <div class="metric-unit">{unit}</div>
    </div>
    """


def classify_metric(name, value):
    """Return status color based on clinical ranges."""
    if name == "co":
        if value < 2.5: return "danger"
        if value < 4.0: return "warning"
        return "normal"
    elif name == "sys":
        if value > 160 or value < 80: return "danger"
        if value > 140 or value < 90: return "warning"
        return "normal"
    elif name == "dia":
        if value > 100 or value < 50: return "danger"
        if value > 90 or value < 60: return "warning"
        return "normal"
    elif name == "sv":
        if value < 30: return "danger"
        if value < 50: return "warning"
        return "normal"
    elif name == "map":
        if value < 60 or value > 120: return "danger"
        if value < 70 or value > 105: return "warning"
        return "normal"
    elif name == "pp":
        if value > 80 or value < 20: return "danger"
        if value > 60 or value < 25: return "warning"
        return "normal"
    return "normal"


def build_params(preset_name, hr, contract, resist, compl):
    """Build a complete parameter dictionary from UI inputs."""
    p = BASELINE_PARAMS.copy()
    p["X0"] = list(BASELINE_PARAMS["X0"])  # Deep copy so overrides don't mutate baseline
    p["Tc"] = 60.0 / hr
    # Contractility affects BOTH isovolumic pressure AND systolic elastance
    # P_LV = U(t) + E(t)*V(t), where U and E both depend on contractile strength
    scale = contract / 100.0
    p["ULO"] = BASELINE_PARAMS["ULO"] * scale
    p["URO"] = BASELINE_PARAMS["URO"] * scale
    p["ELS"] = BASELINE_PARAMS["ELS"] * scale
    p["ERS"] = BASELINE_PARAMS["ERS"] * scale
    p["R3"] = resist
    p["C2"] = compl
    # Apply any preset-specific extra parameters
    preset = CLINICAL_PRESETS.get(preset_name, {})
    if "extra" in preset:
        for k, v in preset["extra"].items():
            p[k] = v
    # Apply initial condition overrides (e.g. reduced blood volume for hemorrhage)
    if "x0_overrides" in preset:
        for idx, val in preset["x0_overrides"].items():
            p["X0"][idx] = val
    return p


# ═══════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════
if 'sim_result' not in st.session_state:
    st.session_state.sim_result = None
if 'sim_result_2' not in st.session_state:
    st.session_state.sim_result_2 = None

with st.sidebar:
    st.markdown("## CardioSim")
    st.caption("Avanzolini et al. (1988) Model  ·  v2.0")
    st.markdown("---")

    # ── Mode selector ──
    mode = st.radio("Mode", ["Single Simulation", "Compare Two Conditions"],
                    horizontal=True, label_visibility="collapsed")

    st.markdown('<div class="section-header">Clinical Preset</div>', unsafe_allow_html=True)
    preset = st.selectbox(
        "Condition",
        list(CLINICAL_PRESETS.keys()),
        label_visibility="collapsed",
    )
    info = CLINICAL_PRESETS[preset]
    st.markdown(f'<div class="preset-info">{info["desc"]}</div>', unsafe_allow_html=True)

    defaults = info

    if mode == "Compare Two Conditions":
        st.markdown('<div class="section-header">Comparison Condition</div>', unsafe_allow_html=True)
        preset2 = st.selectbox(
            "Compare with",
            [k for k in CLINICAL_PRESETS if k != preset],
            label_visibility="collapsed",
        )
        info2 = CLINICAL_PRESETS[preset2]
        st.markdown(f'<div class="preset-info">{info2["desc"]}</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-header">Parameters</div>', unsafe_allow_html=True)
    heart_rate = st.slider('Heart Rate (bpm)', 30, 400, defaults["hr"],
                           help="Frequency of heartbeats. Normal resting: 60–100 bpm.")
    contractility = st.slider('Contractility (%)', 10, 160, defaults["contract"],
                              help="Relative strength of ventricular contraction. 100% = healthy baseline.")
    resistance = st.slider('Peripheral Resistance', 0.4, 2.5, defaults["resist"], step=0.05,
                           help="Systemic vascular resistance (R3). Higher = more afterload.")
    compliance = st.slider('Arterial Compliance', 0.6, 2.2, defaults["compl"], step=0.02,
                           help="Arterial wall elasticity (C2). Lower = stiffer vessels.")

    st.markdown('<div class="section-header">Simulation</div>', unsafe_allow_html=True)
    sim_duration = st.slider('Duration (s)', 2.0, 20.0, 6.0, step=0.5)
    plot_duration = st.slider('Plot last N seconds', 0.5, sim_duration,
                              min(2.5, sim_duration), step=0.25)

    run = st.button('Run Simulation', type="primary", use_container_width=True)

# ═══════════════════════════════════════════════════════════
# MAIN CONTENT
# ═══════════════════════════════════════════════════════════
st.markdown("# CardioSim")
st.caption("Interactive hemodynamic simulator with synthetic ECG  ·  Avanzolini et al. 1988")

if run:
    params = build_params(preset, heart_rate, contractility, resistance, compliance)
    with st.spinner(f'Simulating {preset}...'):
        result = run_sim(params, sim_duration, preset)
    if result is None:
        st.error("Solver failed to converge. Try adjusting parameters or increasing duration.")
    else:
        st.session_state.sim_result = result

    if mode == "Compare Two Conditions":
        d2 = CLINICAL_PRESETS[preset2]
        params2 = build_params(preset2, d2["hr"], d2["contract"], d2["resist"], d2["compl"])
        with st.spinner(f'Simulating {preset2}...'):
            result2 = run_sim(params2, sim_duration, preset2)
        st.session_state.sim_result_2 = result2
    else:
        st.session_state.sim_result_2 = None


result = st.session_state.sim_result
result2 = st.session_state.sim_result_2

if result is not None:
    m = result["metrics"]
    t_end = result["t"][-1]
    t_range = [max(0, t_end - plot_duration), t_end]

    # ── Metric Cards ──
    cols = st.columns(6)
    metric_data = [
        ("Cardiac Output", f"{m['co']:.2f}", "L/min", classify_metric("co", m["co"])),
        ("Stroke Volume",  f"{m['sv']:.1f}", "cm³",   classify_metric("sv", m["sv"])),
        ("Systolic BP",    f"{m['sys']:.0f}", "mmHg",  classify_metric("sys", m["sys"])),
        ("Diastolic BP",   f"{m['dia']:.0f}", "mmHg",  classify_metric("dia", m["dia"])),
        ("Mean Arterial",  f"{m['map_val']:.0f}", "mmHg", classify_metric("map", m["map_val"])),
        ("Pulse Pressure", f"{m['pp']:.0f}", "mmHg",  classify_metric("pp", m["pp"])),
    ]
    for col, (label, val, unit, status) in zip(cols, metric_data):
        col.markdown(metric_card(label, val, unit, status), unsafe_allow_html=True)

    # ── Comparison deltas ──
    if result2 is not None:
        m2 = result2["metrics"]
        st.markdown("---")
        delta_cols = st.columns(6)
        comp_metrics = [
            ("Cardiac Output", m["co"], m2["co"], "L/min"),
            ("Stroke Volume",  m["sv"], m2["sv"], "cm³"),
            ("Systolic BP",    m["sys"], m2["sys"], "mmHg"),
            ("Diastolic BP",   m["dia"], m2["dia"], "mmHg"),
            ("Mean Arterial",  m["map_val"], m2["map_val"], "mmHg"),
            ("Pulse Pressure", m["pp"], m2["pp"], "mmHg"),
        ]
        for col, (label, v1, v2, unit) in zip(delta_cols, comp_metrics):
            if v2 != 0:
                delta = ((v1 - v2) / abs(v2)) * 100
                arrow = "↑" if delta > 0 else "↓"
                badge = "badge-up" if delta > 0 else "badge-down"
                col.markdown(
                    f'<div style="text-align:center; font-size:0.78rem; color:{COLORS["muted"]}">'
                    f'{label}<br>'
                    f'<span class="comparison-badge {badge}">{arrow} {abs(delta):.1f}%</span> vs {result2["preset"]}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    st.markdown("---")

    # ── Tabs ──
    if result2 is not None:
        tab_labels = ["Monitor", "Comparison", "PV Loop", "All Variables", "Export"]
    else:
        tab_labels = ["Monitor", "PV Loop", "All Variables", "Export"]

    tabs = st.tabs(tab_labels)
    tab_idx = 0

    # ── Monitor Tab ──
    with tabs[tab_idx]:
        fig_monitor = make_monitor_plot(result, t_range)
        st.plotly_chart(fig_monitor, use_container_width=True, config={"displayModeBar": False})
    tab_idx += 1

    # ── Comparison Tab ──
    if result2 is not None:
        with tabs[tab_idx]:
            fig_comp = make_comparison_waveform(result, result2, t_range)
            st.plotly_chart(fig_comp, use_container_width=True, config={"displayModeBar": False})
        tab_idx += 1

    # ── PV Loop Tab ──
    with tabs[tab_idx]:
        col_pv1, col_pv2 = st.columns([3, 2])
        with col_pv1:
            fig_pv = make_pv_loop(result, result2)
            st.plotly_chart(fig_pv, use_container_width=True, config={"displayModeBar": False})
        with col_pv2:
            st.markdown("**Understanding the PV Loop**")
            st.markdown("""
            The pressure-volume loop traces one complete cardiac cycle:

            **Bottom-right → Bottom-left:** Isovolumic contraction. 
            The mitral valve closes, LV pressure rises rapidly at constant volume.

            **Bottom-left → Top-left:** Ejection phase.
            The aortic valve opens, blood is expelled, and volume decreases.

            **Top-left → Top-right:** Isovolumic relaxation.
            The aortic valve closes, LV pressure falls at constant volume.

            **Top-right → Bottom-right:** Filling phase.
            The mitral valve opens and the ventricle fills with blood.

            The **area enclosed** by the loop represents the stroke work — 
            the mechanical energy delivered by the ventricle per beat.
            """)
            if result2 is not None:
                st.markdown(f"""
                The dashed loop shows **{result2['preset']}** for comparison. 
                A smaller, shifted loop indicates reduced stroke work.
                """)
    tab_idx += 1

    # ── All Variables Tab ──
    with tabs[tab_idx]:
        var_select = st.multiselect(
            "Select variables to plot",
            options=list(range(12)),
            default=[0, 4, 6, 11],
            format_func=lambda i: f"X{i+1}: {STATE_LABELS[i][0]}",
        )
        if var_select:
            fig_all = make_subplots(
                rows=len(var_select), cols=1, shared_xaxes=True,
                vertical_spacing=0.05,
                subplot_titles=[f"X{i+1}: {STATE_LABELS[i][0]}" for i in var_select],
            )
            palette = ["#ff6b6b", "#ffd93d", "#64ffda", "#48bfe3", "#a29bfe",
                       "#fd79a8", "#6c5ce7", "#00cec9", "#e17055", "#fdcb6e",
                       "#636e72", "#74b9ff"]
            t = result["t"]
            X = result["X"]
            idx = np.where((t >= t_range[0]) & (t <= t_range[1]))[0]
            for row, vi in enumerate(var_select):
                fig_all.add_trace(go.Scatter(
                    x=t[idx], y=X[idx, vi], mode='lines',
                    name=STATE_LABELS[vi][0],
                    line=dict(color=palette[vi], width=1.5),
                ), row=row+1, col=1)
                fig_all.update_yaxes(title_text=STATE_LABELS[vi][1], row=row+1, col=1)

            fig_all.update_layout(
                **PLOT_LAYOUT,
                height=200 * len(var_select),
                showlegend=False,
            )
            for row in range(1, len(var_select) + 1):
                fig_all.update_xaxes(showgrid=True, gridcolor=COLORS["grid"], row=row, col=1)
                fig_all.update_yaxes(showgrid=True, gridcolor=COLORS["grid"], row=row, col=1)
            fig_all.update_xaxes(title_text="Time (s)", row=len(var_select), col=1)
            for ann in fig_all['layout']['annotations']:
                ann['font'] = dict(size=11, color=COLORS["muted"])
            st.plotly_chart(fig_all, use_container_width=True, config={"displayModeBar": False})
    tab_idx += 1

    # ── Export Tab ──
    with tabs[tab_idx]:
        st.markdown("Download simulation data for external analysis.")
        col_dl1, col_dl2, col_dl3 = st.columns(3)

        # Full waveform CSV
        t = result["t"]
        X = result["X"]
        idx_plot = np.where((t >= t_range[0]) & (t <= t_range[1]))[0]
        wave_df = pd.DataFrame(X[idx_plot], columns=[STATE_LABELS[i][0] for i in range(12)])
        wave_df.insert(0, "Time (s)", t[idx_plot])
        wave_df["ECG (mV)"] = result["ecg"][idx_plot]
        wave_df["LV Pressure (mmHg)"] = result["metrics"]["lvp_full"][idx_plot]
        wave_df["LV Outflow (cm³/s)"] = result["metrics"]["lvof"][idx_plot]

        col_dl1.download_button(
            "Waveform Data (CSV)",
            wave_df.to_csv(index=False).encode('utf-8'),
            f"cardiosim_{preset.replace(' ', '_').lower()}_waveforms.csv",
            mime='text/csv', use_container_width=True,
        )

        # PV loop CSV
        m = result["metrics"]
        if len(m["lv_vol"]) > 0:
            pv_df = pd.DataFrame({"LV Volume (cm³)": m["lv_vol"], "LV Pressure (mmHg)": m["lvp"]})
            col_dl2.download_button(
                "PV Loop Data (CSV)",
                pv_df.to_csv(index=False).encode('utf-8'),
                f"cardiosim_{preset.replace(' ', '_').lower()}_pvloop.csv",
                mime='text/csv', use_container_width=True,
            )

        # Full raw data CSV
        full_df = pd.DataFrame(X, columns=[STATE_LABELS[i][0] for i in range(12)])
        full_df.insert(0, "Time (s)", t)
        col_dl3.download_button(
            "Full Simulation (CSV)",
            full_df.to_csv(index=False).encode('utf-8'),
            f"cardiosim_{preset.replace(' ', '_').lower()}_full.csv",
            mime='text/csv', use_container_width=True,
        )

        # Summary metrics
        st.markdown("**Simulation Summary**")
        summary = {
            "Preset": preset,
            "Heart Rate (bpm)": heart_rate,
            "Contractility (%)": contractility,
            "Peripheral Resistance": resistance,
            "Arterial Compliance": compliance,
            "Cardiac Output (L/min)": f"{m['co']:.2f}",
            "Stroke Volume (cm³)": f"{m['sv']:.1f}",
            "Systolic BP (mmHg)": f"{m['sys']:.0f}",
            "Diastolic BP (mmHg)": f"{m['dia']:.0f}",
            "MAP (mmHg)": f"{m['map_val']:.0f}",
            "Pulse Pressure (mmHg)": f"{m['pp']:.0f}",
        }
        st.json(summary)

else:
    # ── Landing state ──
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; padding: 3rem 1rem;">
        <div style="font-size: 2rem; font-weight: 700; margin-bottom: 0.5rem; color: #64ffda;">CardioSim</div>
        <h3 style="color: #ccd6f6; margin-bottom: 0.5rem;">Select a condition and run a simulation</h3>
        <p style="color: #8892b0; max-width: 500px; margin: 0 auto; line-height: 1.6;">
            Choose a clinical preset from the sidebar, adjust physiological parameters,
            and click <b>Run Simulation</b> to visualize hemodynamic waveforms, synthetic ECG,
            and pressure-volume loops.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Show preset overview
    st.markdown("### Available Clinical Presets")
    cols = st.columns(2)
    for i, (name, info) in enumerate(CLINICAL_PRESETS.items()):
        with cols[i % 2]:
            cat_colors = {"normal": "#64ffda", "arrhythmia": "#ffd93d",
                          "structural": "#ff9f43", "critical": "#ff6b6b"}
            border_color = cat_colors.get(info["category"], "#0f3460")
            st.markdown(f"""
            <div style="background: #1a1a2e; border-left: 3px solid {border_color};
                        border-radius: 0 8px 8px 0; padding: 0.8rem 1rem; margin-bottom: 0.5rem;">
                <b>{name}</b><br>
                <span style="font-size: 0.82rem; color: #8892b0;">{info['desc']}</span>
            </div>
            """, unsafe_allow_html=True)


# ── Footer ──
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #4a5568; font-size: 0.75rem; padding: 0.5rem;">
    CardioSim v2.0 · Based on Avanzolini et al. (1988) with McSharry ECG synthesis ·
    Built by Artemii Remizov under supervision of Prof. Sergey Lapin, WSU ·
    <a href="https://creativecommons.org/licenses/by-nc/4.0/" style="color: #64ffda;">CC BY-NC 4.0</a>
</div>
""", unsafe_allow_html=True)