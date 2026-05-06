# Copyright (c) 2025 Artemii Remizov
# Licensed under CC BY-NC 4.0 — https://creativecommons.org/licenses/by-nc/4.0/
#
# Synthetic ECG generation — inspired by McSharry et al. (2003)

import numpy as np


def generate_rr_intervals(preset_name, mean_hr, duration):
    """Return stochastic R-R interval array for arrhythmia presets, None otherwise."""
    mean_rr = 60.0 / mean_hr

    if preset_name == "Atrial Fibrillation":
        n_beats = int(duration / mean_rr * 1.5) + 20
        shape = 4.0
        scale = mean_rr / shape
        intervals = np.random.gamma(shape, scale, n_beats)
        intervals = np.clip(intervals, 0.3, 1.5)
        return intervals

    elif preset_name == "Ventricular Fibrillation":
        n_beats = int(duration / mean_rr * 1.5) + 20
        intervals = np.random.uniform(0.12, 0.25, n_beats)
        return intervals

    return None


def generate_synthetic_ecg(t, p, rr_intervals=None, preset_name="Healthy Adult"):
    """Generate a synthetic ECG trace using sum-of-Gaussians PQRST morphology."""
    ecg = np.zeros(len(t))
    Tc = p["Tc"]

    if preset_name == "Ventricular Fibrillation":
        ecg = 0.15 * np.sin(2 * np.pi * 5.5 * t) * np.sin(2 * np.pi * 0.3 * t)
        ecg += 0.08 * np.sin(2 * np.pi * 7.2 * t + 1.2)
        ecg += np.random.normal(0, 0.03, len(t))
        return ecg

    # (amplitude, center_frac, width_frac) for each PQRST wave
    waves = [
        (0.10,  0.10, 0.035),  # P
        (-0.08, 0.17, 0.012),  # Q
        (1.00,  0.20, 0.018),  # R
        (-0.20, 0.23, 0.015),  # S
        (0.25,  0.38, 0.055),  # T
    ]

    if preset_name == "Ventricular Tachycardia":
        waves = [
            (0.02,  0.08, 0.02),
            (-0.15, 0.15, 0.025),
            (0.80,  0.22, 0.04),
            (-0.35, 0.32, 0.035),
            (0.30,  0.55, 0.07),
        ]
    elif preset_name == "Atrial Fibrillation":
        waves = [
            (0.0,   0.10, 0.03),
            (-0.08, 0.17, 0.012),
            (1.00,  0.20, 0.018),
            (-0.18, 0.23, 0.015),
            (0.22,  0.38, 0.055),
        ]
    elif "Heart Failure" in preset_name:
        waves = [
            (0.08,  0.10, 0.04),
            (-0.06, 0.17, 0.012),
            (0.70,  0.20, 0.022),
            (-0.15, 0.23, 0.015),
            (0.15,  0.40, 0.065),
        ]
    elif preset_name == "Hypertension":
        waves = [
            (0.12,  0.10, 0.04),
            (-0.10, 0.17, 0.012),
            (1.20,  0.20, 0.020),
            (-0.30, 0.24, 0.018),
            (-0.15, 0.40, 0.060),
        ]

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

    if preset_name == "Atrial Fibrillation":
        ecg += 0.04 * np.sin(2 * np.pi * 6.5 * t + np.random.uniform(0, 2 * np.pi))
        ecg += 0.03 * np.sin(2 * np.pi * 8.1 * t + np.random.uniform(0, 2 * np.pi))

    ecg += np.random.normal(0, 0.012, len(t))
    return ecg
