"""
reproduce_paper.py
Regenerates every number and figure in the paper
"Quantifying the hemodynamic effects of a prescribed ventricular-fibrillation-like
state using a lumped-parameter cardiovascular model".

Usage:  python reproduce_paper.py                      (full run, about 15 minutes)
        python reproduce_paper.py --use-cached-sweep   (reuse an existing results_sweep.csv)

Self-contained: the model equations (Avanzolini et al. 1988) are defined below,
so no other file from the simulator repository is needed.
Systolic duration uses Ts = min(0.16 + 0.3*Tc, BETA*Tc). The first term is the
original Avanzolini formula; the cap only acts above 225 bpm (BETA = 0.9), where
the original formula would make systole longer than the whole cycle.

Outputs:
  results_scenarios.csv   steady-state metrics for the five named scenarios
  results_sweep.csv       cardiac output over the heart-rate x contractility grid
  results_beta.csv        sensitivity of the 350 bpm results to the systole cap BETA
  results_contractility_definition.csv   main scenarios with only E_LS and E_RS scaled
  Fig1.png / Fig1.tif     steady-state waveforms, baseline vs VF-like
  Fig2.png / Fig2.tif     transition after the VF-like parameters are switched on
  Fig3.png / Fig3.tif     left-ventricular pressure-volume loops
  Fig4.png / Fig4.tif     cardiac output over heart rate and contractility
Figure numbers match the manuscript. TIFFs are RGB, LZW-compressed, 300 dpi.
"""
import csv
import os
import sys
from PIL import Image
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp

# ------------------------------------------------------------------ settings
BETA = 0.9           # systole may occupy at most this fraction of the cycle
T_SETTLE = 40.0      # s of simulated time before metrics are taken
N_BEATS = 5          # metrics are averaged over the last N_BEATS beats
SOLVER = dict(method="RK45", rtol=1e-6, atol=1e-8, max_step=0.005)
SAMPLES_PER_S = 2000

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Liberation Serif", "Times New Roman", "Times"], "mathtext.fontset": "stix", "font.size": 10, "axes.labelsize": 10,
    "axes.titlesize": 11, "savefig.dpi": 300, "savefig.bbox": "tight",
    "axes.grid": True, "grid.alpha": 0.3, "grid.linewidth": 0.5,
})

# ------------------------------------------------------------------ model
BASE = {"Tc": 0.8, "ULO": 50.0, "URO": 24.0, "ELD": 0.1, "ELS": 1.375, "ERD": 0.03, "ERS": 0.3288,
        "RL": 0.08, "RR": 0.0175,
        "R1": 0.003751, "R2": 0.0675, "R3": 1.0, "R4": 0.003751,
        "R5": 0.003751, "R6": 0.03376, "R7": 0.1013, "R8": 0.003751,
        "L1": 0.000825, "L2": 0.0036, "L3": 0.00075, "L4": 0.00308,
        "C1": 0.22, "C2": 1.46, "C3": 20.0, "C4": 0.09, "C5": 2.67, "C6": 46.7}
X0 = [71.13, 8.89, 70.54, 67.36, 3.33, 105.46, 13.42, 0.79, 13.39, 23.83, 11.30, 112.76]


def systole(Tc, beta):
    ts = 0.16 + 0.3 * Tc
    return ts if beta is None else min(ts, beta * Tc)


def make_params(hr=75.0, kappa=1.0, beta=BETA):
    """Baseline parameters with heart rate hr and contractility scale kappa
    applied to all four active terms (ULO, URO, ELS, ERS)."""
    p = dict(BASE)
    p["Tc"] = 60.0 / hr
    p["beta"] = beta
    for k in ("ULO", "URO", "ELS", "ERS"):
        p[k] = BASE[k] * kappa
    return p


def activation(t, p):
    Tc = p["Tc"]
    Ts = systole(Tc, p["beta"])
    Tm = np.mod(t, Tc)
    return np.where(Tm < Ts, (1.0 - np.cos(2.0 * np.pi * Tm / Ts)) / 2.0, 0.0)


def rhs(t, X, p):
    X1, X2, X3, X4, X5, X6, X7, X8, X9, X10, X11, X12 = X
    A = float(activation(t, p))
    UL, UR = p["ULO"] * A, p["URO"] * A
    EL, ER = p["ELD"] + p["ELS"] * A, p["ERD"] + p["ERS"] * A
    Z1 = UL + X12 * EL - X1          # aortic valve
    Z2 = X5 - (UR + X6 * ER)         # tricuspid valve
    Z3 = UR + X6 * ER - X7           # pulmonary valve
    Z4 = X11 - (UL + X12 * EL)       # mitral valve
    S1, S2, S3, S4 = Z1 > 0, Z2 > 0, Z3 > 0, Z4 > 0
    d = np.empty(12)
    d[0] = (S1 * Z1 / (p["RL"] + p["R1"]) - X2) / p["C1"]
    d[1] = (X1 - p["R2"] * X2 - X3) / p["L1"]
    d[2] = (X2 - X4) / p["C2"]
    d[3] = (X3 - p["R3"] * X4 - X5) / p["L2"]
    d[4] = (X4 - S2 * Z2 / p["R4"]) / p["C3"]
    d[5] = S2 * Z2 / p["R4"] - S3 * Z3 / (p["RR"] + p["R5"])
    d[6] = (S3 * Z3 / (p["RR"] + p["R5"]) - X8) / p["C4"]
    d[7] = (X7 - p["R6"] * X8 - X9) / p["L3"]
    d[8] = (X8 - X10) / p["C5"]
    d[9] = (X9 - p["R7"] * X10 - X11) / p["L4"]
    d[10] = (X10 - S4 * Z4 / p["R8"]) / p["C6"]
    d[11] = S4 * Z4 / p["R8"] - S1 * Z1 / (p["RL"] + p["R1"])
    return d


def simulate(p, x0, T):
    t_eval = np.linspace(0.0, T, int(T * SAMPLES_PER_S) + 1)
    sol = solve_ivp(lambda t, X: rhs(t, X, p), [0.0, T], x0, t_eval=t_eval, **SOLVER)
    if sol.status != 0:
        raise RuntimeError(sol.message)
    return sol.t, sol.y.T


def lv_signals(t, X, p):
    """Aortic-valve outflow and left-ventricular pressure."""
    A = activation(t, p)
    UL = p["ULO"] * A
    EL = p["ELD"] + p["ELS"] * A
    Z1 = UL + X[:, 11] * EL - X[:, 0]
    q = np.where(Z1 > 0, Z1 / (p["RL"] + p["R1"]), 0.0)
    plv = UL + EL * X[:, 11] - p["RL"] * q
    return q, plv


def last_beats(t, p, n=N_BEATS):
    Tc = p["Tc"]
    nc = int(np.floor(t[-1] / Tc + 1e-9))
    start, end = (nc - n) * Tc, nc * Tc
    return (t >= start - 1e-12) & (t <= end + 1e-12)


def metrics(t, X, p):
    idx = last_beats(t, p)
    q, _ = lv_signals(t, X, p)
    tt = t[idx]
    sv = np.trapezoid(q[idx], tt) / N_BEATS
    hr = 60.0 / p["Tc"]
    aop = X[idx, 0]
    vlv = X[idx, 11]
    return dict(
        HR=hr, CO=sv * hr / 1000.0, SV=sv,
        SBP=aop.max(), DBP=aop.min(),
        MAP=np.trapezoid(aop, tt) / (tt[-1] - tt[0]),
        EDV=vlv.max(), ESV=vlv.min(),
        EF=100.0 * (vlv.max() - vlv.min()) / vlv.max(),
        PSV=X[idx, 4].mean(),          # mean systemic venous pressure
    )


def save_fig(name):
    """Save the current figure as PNG and as a PLOS-style TIFF (RGB, LZW, 300 dpi)."""
    plt.savefig(f"{name}.png")
    plt.close()
    im = Image.open(f"{name}.png").convert("RGBA")
    bg = Image.new("RGB", im.size, (255, 255, 255))
    bg.paste(im, mask=im.split()[3])
    bg.save(f"{name}.tif", compression="tiff_lzw", dpi=(300, 300))


# ------------------------------------------------------------------ baseline
p_base = make_params(75, 1.0)
t_b, X_b = simulate(p_base, X0, T_SETTLE)
x_ss = X_b[-1].copy()              # baseline steady state, used as the start for every other run
m_base = metrics(t_b, X_b, p_base)

SCENARIOS = [
    ("Baseline",            75, 1.00),
    ("Rate only",          350, 1.00),
    ("Contractility only",  75, 0.50),
    ("VF-like",            350, 0.50),
    ("Severe VF-like",     350, 0.25),
]

runs = {}
for name, hr, kappa in SCENARIOS:
    p = make_params(hr, kappa)
    t, X = (t_b, X_b) if name == "Baseline" else simulate(p, x_ss, T_SETTLE)
    runs[name] = (p, t, X, metrics(t, X, p))

with open("results_scenarios.csv", "w", newline="") as f:
    keys = ["HR", "CO", "SV", "SBP", "DBP", "MAP", "EDV", "ESV", "EF", "PSV"]
    w = csv.writer(f)
    w.writerow(["scenario", "kappa"] + keys + ["CO_pct_change"])
    for name, hr, kappa in SCENARIOS:
        m = runs[name][3]
        w.writerow([name, kappa] + [f"{m[k]:.2f}" for k in keys]
                   + [f"{100 * (m['CO'] / m_base['CO'] - 1):.1f}"])
        print(f"{name:20s} " + " ".join(f"{k}={m[k]:.2f}" for k in keys)
              + f"  dCO={100 * (m['CO'] / m_base['CO'] - 1):.1f}%")

# ------------------------------------------------------------------ figure 1
WIN = 1.6
fig, axes = plt.subplots(3, 2, figsize=(7.2, 5.8), sharex=True, sharey="row")
for col, name in enumerate(["Baseline", "VF-like"]):
    p, t, X, m = runs[name]
    sel = t >= t[-1] - WIN
    ts = t[sel] - t[sel][0]
    _, plv = lv_signals(t, X, p)
    ax = axes[0, col]
    ax.plot(ts, plv[sel], color="#b91c1c", lw=1.2, label="Left ventricle")
    ax.plot(ts, X[sel, 0], color="#1d4ed8", lw=1.2, label="Aorta")
    ax.set_title(f"{name} ({m['HR']:.0f} bpm, contractility {100 * (p['ELS'] / BASE['ELS']):.0f}%)")
    axes[1, col].plot(ts, X[sel, 11], color="#047857", lw=1.2)
    axes[2, col].plot(ts, X[sel, 4], color="#7c3aed", lw=1.2)
    axes[2, col].set_xlabel("Time (s)")
axes[0, 0].set_ylabel("Pressure (mmHg)")
axes[1, 0].set_ylabel("LV volume (mL)")
axes[2, 0].set_ylabel("Systemic venous\npressure (mmHg)")
axes[0, 0].legend(loc="center", bbox_to_anchor=(0.40, 0.33), fontsize=8, framealpha=1.0)
for ax in axes.flat:
    ax.set_xlim(0, WIN)
plt.tight_layout()
save_fig("Fig1")

# ------------------------------------------------------------------ figure 3
colors = {"Baseline": "#111827", "Rate only": "#d97706", "Contractility only": "#2563eb",
          "VF-like": "#b91c1c", "Severe VF-like": "#6d28d9"}
styles = {"Baseline": "-", "Rate only": "--", "Contractility only": "-.",
          "VF-like": "-", "Severe VF-like": ":"}
panels = [("(a) Each change applied separately", ["Baseline", "Rate only", "Contractility only"]),
          ("(b) Combined VF-like states", ["Baseline", "VF-like", "Severe VF-like"])]
fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.6), sharex=True, sharey=True)
for ax, (title, names) in zip(axes, panels):
    for name in names:
        p, t, X, m = runs[name]
        Tc = p["Tc"]
        nc = int(np.floor(t[-1] / Tc + 1e-9))
        sel = (t >= (nc - 1) * Tc - 1e-12) & (t <= nc * Tc + 1e-12)
        _, plv = lv_signals(t, X, p)
        ax.plot(X[sel, 11], plv[sel], styles[name], color=colors[name], lw=1.5,
                label=f"{name} (SV {m['SV']:.1f} mL)")
    ax.set_title(title)
    ax.set_xlabel("Left-ventricular volume (mL)")
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=1, frameon=False)
axes[0].set_ylabel("Left-ventricular pressure (mmHg)")
plt.tight_layout()
save_fig("Fig3")

# ------------------------------------------------------------------ sweep + figure 4
HRS = [60, 80, 100, 125, 150, 175, 200, 225, 250, 275, 300, 325, 350]
KAPPAS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
co_grid = np.zeros((len(KAPPAS), len(HRS)))
import os
cached = None
if "--use-cached-sweep" in sys.argv and os.path.exists("results_sweep.csv"):
    rows = list(csv.DictReader(open("results_sweep.csv")))
    if len(rows) == len(HRS) * len(KAPPAS):
        cached = {(int(r["HR"]), float(r["kappa"])): float(r["CO"]) for r in rows}
if cached is not None:
    print("using cached results_sweep.csv (run without --use-cached-sweep to recompute)")
    for i, kappa in enumerate(KAPPAS):
        for j, hr in enumerate(HRS):
            co_grid[i, j] = cached[(hr, kappa)]
else:
  with open("results_sweep.csv", "w", newline="") as f:
      w = csv.writer(f)
      w.writerow(["HR", "kappa", "CO", "MAP", "SV", "CO_pct_of_baseline"])
      for i, kappa in enumerate(KAPPAS):
          for j, hr in enumerate(HRS):
              p = make_params(hr, kappa)
              t, X = simulate(p, x_ss, T_SETTLE)
              m = metrics(t, X, p)
              co_grid[i, j] = m["CO"]
              w.writerow([hr, kappa, f"{m['CO']:.4f}", f"{m['MAP']:.2f}", f"{m['SV']:.2f}",
                          f"{100 * m['CO'] / m_base['CO']:.1f}"])
          print(f"sweep kappa={kappa:.1f} done")

pct = 100.0 * co_grid / m_base["CO"]
fig, ax = plt.subplots(figsize=(6.6, 4.5))
mesh = ax.pcolormesh(HRS, [100 * k for k in KAPPAS], pct, shading="gouraud", cmap="RdYlBu")
cs = ax.contour(HRS, [100 * k for k in KAPPAS], pct, levels=[25, 50, 75, 100], colors="k", linewidths=0.8)
ax.clabel(cs, fmt="%d%%", fontsize=8)
cb = fig.colorbar(mesh, ax=ax)
cb.set_label("Cardiac output (% of baseline)")
hr_crit = 60.0 / (0.16 / (BETA - 0.3))
ax.axvline(hr_crit, color="k", ls="--", lw=1)
ax.text(hr_crit + 4, 94, "systole capped", fontsize=8,
        bbox=dict(facecolor="white", edgecolor="none", alpha=0.8, pad=1.5))
labels = {"Baseline": ("Baseline", (6, -12)), "Rate only": ("Rate only", (-50, -12)),
          "Contractility only": ("Contractility only", (6, 4)),
          "VF-like": ("VF-like", (-40, 4)), "Severe VF-like": ("Severe VF-like", (-66, 4))}
for name, hr, kappa in SCENARIOS:
    ax.plot(hr, 100 * kappa, "o", mfc="white", mec="k", ms=6, clip_on=False, zorder=5)
    txt, off = labels[name]
    ax.annotate(txt, (hr, 100 * kappa), xytext=off, textcoords="offset points", fontsize=8,
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.8, pad=1.0), zorder=6)
ax.set_xlabel("Heart rate (bpm)")
ax.set_ylabel("Contractility (% of baseline)")
plt.tight_layout()
save_fig("Fig4")

# ------------------------------------------------------------------ figure 2 (transient)
def per_beat(t, X, Tc, t0=0.0):
    """Mean, max and min aortic pressure for each complete cycle.
    Returns cycle edges (len n+1) and per-cycle values (len n)."""
    n = int(np.floor((t[-1] - t[0]) / Tc + 1e-9))
    mean, hi, lo = [], [], []
    for k in range(n):
        sel = (t >= t[0] + k * Tc - 1e-12) & (t <= t[0] + (k + 1) * Tc + 1e-12)
        a, tt = X[sel, 0], t[sel]
        mean.append(np.trapezoid(a, tt) / (tt[-1] - tt[0]))
        hi.append(a.max())
        lo.append(a.min())
    edges = t0 + t[0] + Tc * np.arange(n + 1)
    return edges, np.array(mean), np.array(hi), np.array(lo)


T_PRE, T_POST = 3.2, 8.0
t_pre, X_pre = simulate(p_base, x_ss, T_PRE)
fig, ax = plt.subplots(figsize=(7.2, 3.3))
traces = [("Baseline", "#111827", t_pre, X_pre, p_base["Tc"], 0.0)]
settle = {}
for name, color in [("VF-like", colors["VF-like"]), ("Severe VF-like", colors["Severe VF-like"])]:
    p = runs[name][0]
    t_post, X_post = simulate(p, X_pre[-1], T_POST)
    traces.append((name, color, t_post, X_post, p["Tc"], T_PRE))
for name, color, t, X, Tc, t0 in traces:
    edges, mean, hi, lo = per_beat(t, X, Tc, t0)
    ax.stairs(hi, edges, baseline=lo, fill=True, color=color, alpha=0.18, lw=0)
    ax.stairs(mean, edges, baseline=None, color=color, lw=1.8, label=name)
    if t0 > 0:
        final = mean[-1]
        k = next(i for i in range(len(mean)) if np.all(np.abs(mean[i:] - final) < 1.0))
        settle[name] = edges[k + 1] - T_PRE
ax.axvline(T_PRE, color="k", ls=":", lw=1)
ax.set_xlabel("Time (s)")
ax.set_ylabel("Aortic pressure (mmHg)")
ax.set_xlim(0, T_PRE + T_POST)
ax.set_ylim(30, 120)
ax.legend(fontsize=8, loc="upper right")
plt.tight_layout()
save_fig("Fig2")
for k, v in settle.items():
    print(f"{k}: beat-mean aortic pressure within 1 mmHg of final value after {v:.2f} s")

print("systole cap active above", round(hr_crit, 1), "bpm")

# ------------------------------------------------------------------ sensitivity to BETA
with open("results_beta.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["beta", "scenario", "CO", "CO_pct_change", "MAP", "EDV"])
    for beta in [None, 0.8, 0.85, 0.9, 0.95]:
        for name, hr, kappa in SCENARIOS[1:]:
            if hr < 300:
                continue
            p = make_params(hr, kappa, beta)
            t, X = simulate(p, x_ss, T_SETTLE)
            m = metrics(t, X, p)
            w.writerow(["original" if beta is None else beta, name, f"{m['CO']:.2f}",
                        f"{100 * (m['CO'] / m_base['CO'] - 1):.1f}", f"{m['MAP']:.1f}", f"{m['EDV']:.1f}"])
            print("beta", beta, name, f"{100 * (m['CO'] / m_base['CO'] - 1):+.1f}%", f"MAP {m['MAP']:.1f}")

# ------------------------------------------------------------------ contractility definition
# Repeat the main scenarios scaling only the active elastances (E_LS, E_RS);
# the active pressure terms U_L0 and U_R0 stay at baseline.
with open("results_contractility_definition.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["scenario", "HR", "kappa_elastance_only", "CO", "CO_pct_change", "MAP"])
    for name, hr, kappa in SCENARIOS[1:]:
        p = make_params(hr, 1.0)
        p["ELS"] = BASE["ELS"] * kappa
        p["ERS"] = BASE["ERS"] * kappa
        t, X = simulate(p, x_ss, T_SETTLE)
        m = metrics(t, X, p)
        w.writerow([name, hr, kappa, f"{m['CO']:.2f}", f"{100 * (m['CO'] / m_base['CO'] - 1):.1f}", f"{m['MAP']:.1f}"])
        print(f"elastance-only {name:20s} CO {m['CO']:.2f} ({100 * (m['CO'] / m_base['CO'] - 1):+.1f}%)")
print("done")
