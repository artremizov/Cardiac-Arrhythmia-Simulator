"""Independent checks on the numbers in the paper.

Run after reproduce_paper.py, in the same folder:  python verify.py
Checks, for each of the five scenarios: conservation of total blood volume, periodic
steady state, stroke volume computed two ways, flow balance through all four vascular
segments, agreement with a different solver (DOP853) at a much tighter tolerance,
insensitivity to doubling the run length (40 s vs 80 s), and agreement with
results_scenarios.csv. Also compares the equations with the simulator's model.py, found
next to this file or in the folder above it (the repository root).
"""
import os, sys, csv, re, importlib.util, contextlib, io
import numpy as np
from scipy.integrate import solve_ivp

# load the paper's script as a module without re-running the figures
src = open("reproduce_paper.py").read()
src = src[:src.index("# ------------------------------------------------------------------ baseline")]
R = {}; exec(src, R)

try:
    import model as repo  # original model.py from the GitHub repo, placed next to this file
except ImportError:
    # otherwise the repository root, one folder above paper/
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    try:
        import model as repo
    except ImportError:
        repo = None

ok = lambda c: "PASS" if c else "FAIL"

# 1. same equations as the original repo code
if repo is None:
    print("[1] skipped: model.py not found next to this file or in the folder above")
rng = np.random.default_rng(0)
worst = 0.0
for hr in ([60, 75, 150, 225] if repo else []):
    for kappa in [0.25, 0.5, 1.0]:
        p_mine = R["make_params"](hr, kappa)
        p_repo = repo.build_params("Healthy Adult", hr, kappa * 100, 1.0, 1.46)
        for _ in range(200):
            X = np.array(R["X0"]) * rng.uniform(0.5, 1.5, 12)
            t = rng.uniform(0, 5)
            a, b = R["rhs"](t, X, p_mine), repo.cardiovascular_model(t, X, p_repo)
            worst = max(worst, np.max(np.abs(a - b) / (np.abs(b) + 1e-9)))
if repo: print(f"[1] equations match repo model.py at <=225 bpm, max rel diff {worst:.1e}: {ok(worst < 1e-12)}")

# helper: tight independent solver
def tight(p, x0, T):
    te = np.linspace(0, T, int(T * 4000) + 1)
    s = solve_ivp(lambda t, X: R["rhs"](t, X, p), [0, T], x0, t_eval=te,
                  method="DOP853", rtol=1e-10, atol=1e-10, max_step=0.001)
    return s.t, s.y.T

def total_volume(X, p):
    C = [p["C1"], p["C2"], p["C3"], p["C4"], p["C5"], p["C6"]]
    P = X[:, [0, 2, 4, 6, 8, 10]]
    return (P * C).sum(1) + X[:, 5] + X[:, 11]

pb = R["make_params"](75, 1.0)
t, X = R["simulate"](pb, R["X0"], 40)
xss = X[-1]
paper = {r["scenario"]: r for r in csv.DictReader(open("results_scenarios.csv"))}
scen = [("Baseline", 75, 1.0), ("Rate only", 350, 1.0), ("Contractility only", 75, 0.5),
        ("VF-like", 350, 0.5), ("Severe VF-like", 350, 0.25)]
for name, hr, k in scen:
    p = R["make_params"](hr, k)
    x0 = R["X0"] if name == "Baseline" else xss
    t, X = R["simulate"](p, x0, 40)
    m = R["metrics"](t, X, p)
    # 2. blood volume conserved
    vol = total_volume(X, p)
    drift = np.ptp(vol) / vol.mean()
    # 3. steady state: state at the exact end of the last cycle equals one cycle earlier
    Tc = p["Tc"]; nc = int(40 / Tc)
    sd = solve_ivp(lambda tt, XX: R["rhs"](tt, XX, p), [0, 40], x0, dense_output=True, **R["SOLVER"])
    a_, b_ = sd.sol(nc * Tc - 1e-9), sd.sol((nc - 1) * Tc - 1e-9)
    per = np.max(np.abs(a_ - b_) / (np.abs(a_) + 1e-6))
    # 4. two independent SV definitions
    sv_vol = m["EDV"] - m["ESV"]
    # 5. mass balance: mean flow through every segment equals CO
    idx = R["last_beats"](t, p); tt = t[idx]; dur = tt[-1] - tt[0]
    flows = [np.trapezoid(X[idx, j], tt) / dur * 60 / 1000 for j in (1, 3, 7, 9)]
    # 6. much tighter, different solver
    t2, X2 = tight(p, x0, 40); m2 = R["metrics"](t2, X2, p)
    sdiff = max(abs(m2[q] - m[q]) / abs(m[q]) for q in ("CO", "SV", "MAP", "EDV", "ESV"))
    # 8. doubling the run length does not change the result
    t3, X3 = R["simulate"](p, x0, 80); m3 = R["metrics"](t3, X3, p)
    ddiff = abs(m3["CO"] - m["CO"]) / m["CO"]
    # 7. matches the CSV the paper was written from
    csvdiff = max(abs(float(paper[name][q]) - m[q]) for q in ("CO", "SV", "MAP", "EDV", "ESV"))
    print(f"\n{name}")
    print(f"  [2] blood volume drift {drift:.1e}: {ok(drift < 1e-4)}")
    print(f"  [3] periodic steady state, max change over last cycle {per:.1e}: {ok(per < 1e-3)}")
    print(f"  [4] SV from valve flow {m['SV']:.2f} vs EDV-ESV {sv_vol:.2f}: {ok(abs(m['SV'] - sv_vol) < 0.05)}")
    print(f"  [5] CO {m['CO']:.3f}; mean flow in 4 vessels {', '.join(f'{f:.3f}' for f in flows)}: {ok(max(abs(f - m['CO']) for f in flows) < 0.01)}")
    print(f"  [6] DOP853 rtol 1e-10 vs paper solver, max rel diff {sdiff:.1e}: {ok(sdiff < 1e-3)}")
    print(f"  [7] matches results_scenarios.csv, max abs diff {csvdiff:.3f}: {ok(csvdiff < 0.01)}")
    print(f"  [8] 80 s vs 40 s run, CO rel diff {ddiff:.1e}: {ok(ddiff < 2e-3)}")
