# Copyright (c) 2025 Artemii Remizov
# Licensed under CC BY-NC 4.0 — https://creativecommons.org/licenses/by-nc/4.0/
#
# Hemodynamic analysis: metrics extraction, clinical classification, simulation runner.

import numpy as np
from scipy.integrate import solve_ivp

from model import cardiovascular_model, build_params
from ecg import generate_rr_intervals, generate_synthetic_ecg


def calculate_metrics(t, X, p, rr_intervals=None):
    """Extract hemodynamic metrics from the last stable cardiac cycle.

    Regular rhythms: snap to exact cycle boundaries for a clean PV loop.
    Stochastic rhythms (AF, VF): average over last ~8 beats, pick representative loop.
    Ejection fraction is SV / EDV (in %); hr is the effective rate over the same beats.
    """
    n = len(t)
    LVOF = np.zeros(n)
    LVP = np.zeros(n)
    Tc = p["Tc"]

    beat_boundaries = []
    if rr_intervals is not None and len(rr_intervals) > 0:
        cum = 0.0
        beat_boundaries.append(0.0)
        for rr in rr_intervals:
            cum += rr
            beat_boundaries.append(cum)
            if cum > t[-1] + 1.0:
                break
        beat_boundaries = np.array(beat_boundaries)

    for i in range(n):
        if rr_intervals is not None and len(rr_intervals) > 0:
            bi = np.searchsorted(beat_boundaries, t[i], side='right') - 1
            bi = max(0, min(bi, len(rr_intervals) - 1))
            Tc_local = rr_intervals[bi]
            Tm = t[i] - beat_boundaries[bi]
        else:
            Tc_local = Tc
            Tm = t[i] % Tc_local

        Ts = min(0.16 + 0.3 * Tc_local, 0.9 * Tc_local)  # cap so systole fits in the cycle above 225 bpm
        A = (1 - np.cos(2 * np.pi * Tm / Ts)) / 2 if Tm < Ts else 0
        UL = p["ULO"] * A
        EL = p["ELD"] + p["ELS"] * A
        Z1 = UL + X[i, 11] * EL - X[i, 0]
        S1 = float(Z1 > 0)
        LVOF[i] = Z1 * S1 / (p["RL"] + p["R1"])
        LVP[i] = UL + EL * X[i, 11] - p["RL"] * LVOF[i]

    end_t = t[-1]
    _trapz = np.trapezoid if hasattr(np, 'trapezoid') else np.trapz
    empty = dict(co=0, sv=0, sys=0, dia=0, map_val=0, pp=0, ef=0, hr=0,
                 lv_vol=np.array([]), lvp=np.array([]),
                 lvof=LVOF, lvp_full=LVP)

    if rr_intervals is not None and len(rr_intervals) > 0:
        valid = beat_boundaries[beat_boundaries <= end_t]
        if len(valid) < 4:
            return empty

        n_avg_beats = min(8, len(valid) - 2)
        avg_start_idx = len(valid) - 1 - n_avg_beats
        beat_svs, beat_sys, beat_dia, beat_edv, beat_ranges = [], [], [], [], []
        for b in range(avg_start_idx, len(valid) - 1):
            bs = valid[b]
            be = valid[b + 1]
            b_idx = np.where((t >= bs) & (t < be))[0]
            if len(b_idx) < 2:
                continue
            beat_svs.append(_trapz(LVOF[b_idx], t[b_idx]))
            beat_sys.append(np.max(X[b_idx, 0]))
            beat_dia.append(np.min(X[b_idx, 0]))
            beat_edv.append(np.max(X[b_idx, 11]))
            beat_ranges.append(b_idx)

        if len(beat_svs) == 0:
            return empty

        avg_sv  = np.mean(beat_svs)
        avg_sys = np.mean(beat_sys)
        avg_dia = np.mean(beat_dia)
        avg_rr  = np.mean(np.diff(valid[avg_start_idx:]))
        avg_co  = avg_sv * (60.0 / avg_rr) / 1000.0

        median_sv  = np.median(beat_svs)
        best_beat  = np.argmin(np.abs(np.array(beat_svs) - median_sv))
        pv_idx     = beat_ranges[best_beat]

        return dict(
            co=avg_co, sv=avg_sv, sys=avg_sys, dia=avg_dia,
            map_val=avg_dia + (avg_sys - avg_dia) / 3.0,
            ef=np.mean(np.array(beat_svs) / np.array(beat_edv)) * 100.0,
            hr=60.0 / avg_rr,
            pp=avg_sys - avg_dia,
            lv_vol=X[pv_idx, 11], lvp=LVP[pv_idx],
            lvof=LVOF, lvp_full=LVP,
        )
    else:
        n_cycles = int(end_t / Tc)
        if n_cycles < 3:
            return empty
        beat_start   = (n_cycles - 1) * Tc
        beat_end     = n_cycles * Tc
        effective_tc = Tc

    idx = np.where((t >= beat_start) & (t < beat_end))[0]
    if len(idx) <= 1:
        return empty

    t_beat = t[idx]
    sv     = _trapz(LVOF[idx], t_beat)
    hr     = 60.0 / effective_tc
    co     = sv * hr / 1000.0

    aop_beat = X[idx, 0]
    sys_p    = np.max(aop_beat)
    dia_p    = np.min(aop_beat)
    map_val  = dia_p + (sys_p - dia_p) / 3.0
    pp       = sys_p - dia_p

    return dict(
        co=co, sv=sv, sys=sys_p, dia=dia_p, map_val=map_val, pp=pp,
        ef=sv / np.max(X[idx, 11]) * 100.0, hr=hr,
        lv_vol=X[idx, 11], lvp=LVP[idx],
        lvof=LVOF, lvp_full=LVP,
    )


def classify_metric(name, value):
    """Return 'normal', 'warning', or 'danger' for a given metric value."""
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
        if value > 90  or value < 60: return "warning"
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


def run_sim(params, duration, preset_name):
    """Run a single simulation and return all results, or None on solver failure."""
    rr = generate_rr_intervals(preset_name, 60.0 / params["Tc"], duration)
    t_eval = np.linspace(0, duration, int(duration * 600))

    sol = solve_ivp(
        lambda t, X: cardiovascular_model(t, X, params, rr),
        [0, duration], params["X0"], t_eval=t_eval,
        method='RK45', rtol=1e-5, atol=1e-8, max_step=0.005,
    )

    if sol.status != 0:
        return None

    t = sol.t
    X = sol.y.T
    met = calculate_metrics(t, X, params, rr)
    ecg = generate_synthetic_ecg(t, params, rr, preset_name)

    return dict(t=t, X=X, metrics=met, ecg=ecg, params=params,
                preset=preset_name, rr=rr)
