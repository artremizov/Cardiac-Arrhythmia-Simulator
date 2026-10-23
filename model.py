# Copyright (c) 2025 Artemii Remizov
# Licensed under CC BY-NC 4.0 — https://creativecommons.org/licenses/by-nc/4.0/
#
# Cardiovascular model — Avanzolini et al. (1988)
# Pure physics layer: no UI or plotting imports.

import numpy as np

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
        "desc": "Resting baseline: heart rate 75 bpm, contractility 100%. Cardiac output 4.64 L/min, blood pressure 113/68 mmHg.",
        "category": "normal",
    },
    "Ventricular Fibrillation": {
        "hr": 350, "contract": 25, "resist": 1.0, "compl": 1.46,
        "desc": "Irregular VF-like rhythm: R-R intervals drawn uniformly from 0.12–0.25 s (240–500 bpm) and contractility reduced to 25%. Cardiac output falls 57% from Healthy Adult (mean of 5 runs of 30 s).",
        "category": "critical",
    },
    "Ventricular Tachycardia": {
        "hr": 180, "contract": 60, "resist": 1.0, "compl": 1.46,
        "desc": "Regular rhythm at 180 bpm with contractility reduced to 60%. Stroke volume 23 mL; cardiac output 4.18 L/min, 10% below Healthy Adult.",
        "category": "arrhythmia",
    },
    "Atrial Fibrillation": {
        "hr": 130, "contract": 85, "resist": 1.0, "compl": 1.46,
        "desc": "Irregular R-R intervals drawn from a gamma distribution (mean 60/HR s, limited to 0.3–1.5 s), contractility 85%. Results vary between runs; the model has no atrial chambers, so loss of atrial contraction is not represented.",
        "category": "arrhythmia",
    },
    "Sinus Tachycardia": {
        "hr": 120, "contract": 100, "resist": 1.0, "compl": 1.46,
        "desc": "Regular rhythm at 120 bpm, contractility 100%. Stroke volume falls to 46 mL; cardiac output 5.55 L/min, 20% above Healthy Adult.",
        "category": "arrhythmia",
    },
    "Sinus Bradycardia": {
        "hr": 50, "contract": 100, "resist": 1.0, "compl": 1.46,
        "desc": "Regular rhythm at 50 bpm, contractility 100%. Longer filling raises stroke volume to 76 mL, but cardiac output falls to 3.81 L/min, 18% below Healthy Adult.",
        "category": "arrhythmia",
    },
    "Heart Failure (Systolic)": {
        "hr": 90, "contract": 55, "resist": 1.2, "compl": 1.46,
        "desc": "Contractility reduced to 55%, heart rate 90 bpm, peripheral resistance 1.2 mmHg·s/mL. Ejection fraction 29%; cardiac output 2.97 L/min, 36% below Healthy Adult.",
        "category": "structural",
    },
    "Hypertension": {
        "hr": 80, "contract": 110, "resist": 1.5, "compl": 1.1,
        "desc": "Peripheral resistance 1.5 mmHg·s/mL, arterial compliance 1.10 mL/mmHg, contractility 110%, heart rate 80 bpm. Blood pressure 140/95 mmHg.",
        "category": "structural",
    },
    "Aortic Stenosis": {
        "hr": 80, "contract": 120, "resist": 1.0, "compl": 1.46,
        "desc": "Aortic valve resistance raised from 0.0038 to 0.05 mmHg·s/mL, contractility 120%, heart rate 80 bpm. Peak LV pressure 146 mmHg against an aortic systolic pressure of 121 mmHg.",
        "category": "structural",
        "extra": {"R1": 0.05},
    },
    "Hemorrhagic Shock": {
        "hr": 130, "contract": 90, "resist": 1.6, "compl": 1.46,
        "desc": "Initial circulating volume reduced by about 290 mL, heart rate 130 bpm, contractility 90%, peripheral resistance 1.6 mmHg·s/mL. Stroke volume 24 mL; cardiac output 3.17 L/min, 32% below Healthy Adult.",
        "category": "critical",
        "x0_overrides": {4: 2.0, 5: 75.0, 10: 7.0, 11: 80.0},
    },
}

CATEGORY_COLORS = {
    "normal":    "#10b981",  # emerald
    "arrhythmia": "#f59e0b", # amber
    "structural": "#3b82f6", # blue
    "critical":  "#ef4444",  # red
}


def cardiovascular_model(t, X, p, rr_intervals=None):
    """12-ODE lumped-parameter cardiovascular model (Avanzolini 1988).
    Supports optional stochastic R-R intervals for arrhythmia simulation."""
    X1, X2, X3, X4, X5, X6, X7, X8, X9, X10, X11, X12 = X

    Tc = p["Tc"]
    if rr_intervals is not None and len(rr_intervals) > 0:
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

    Ts = min(0.16 + 0.3 * Tc, 0.9 * Tc)  # cap so systole fits in the cycle above 225 bpm
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


def build_params(preset_name, hr, contract, resist, compl):
    """Build a complete parameter dictionary from UI inputs."""
    p = BASELINE_PARAMS.copy()
    p["X0"] = list(BASELINE_PARAMS["X0"])  # copy so overrides don't mutate baseline
    p["Tc"] = 60.0 / hr
    scale = contract / 100.0
    p["ULO"] = BASELINE_PARAMS["ULO"] * scale
    p["URO"] = BASELINE_PARAMS["URO"] * scale
    p["ELS"] = BASELINE_PARAMS["ELS"] * scale
    p["ERS"] = BASELINE_PARAMS["ERS"] * scale
    p["R3"] = resist
    p["C2"] = compl
    preset = CLINICAL_PRESETS.get(preset_name, {})
    if "extra" in preset:
        for k, v in preset["extra"].items():
            p[k] = v
    if "x0_overrides" in preset:
        for idx, val in preset["x0_overrides"].items():
            p["X0"][idx] = val
    return p
