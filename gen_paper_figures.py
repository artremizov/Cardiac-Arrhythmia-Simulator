import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt

# ═══════════════════════════════════════════════════
# MODEL (Avanzolini et al. 1988)
# ═══════════════════════════════════════════════════
def cardiovascular_model(t, X, Tc=0.8, ULO=50.0, URO=24.0):
    """12-ODE closed-loop cardiovascular system."""
    ELD = 0.1;     ELS = 1.375
    ERD = 3.0e-02; ERS = 0.3288
    RL  = 8.0e-02; RR  = 1.75e-02

    R1 = 3.751e-03; R2 = 6.75e-02; R3 = 1.0;    R4 = 3.751e-03
    R5 = 3.751e-03; R6 = 3.376e-02; R7 = 0.1013; R8 = 3.751e-03
    L1 = 8.25e-04;  L2 = 3.6e-03;   L3 = 7.5e-04; L4 = 3.08e-03
    C1 = 0.22; C2 = 1.46; C3 = 20.0; C4 = 9.0e-02; C5 = 2.67; C6 = 46.7

    X1, X2, X3, X4, X5, X6, X7, X8, X9, X10, X11, X12 = X

    Ts = 0.16 + 0.3 * Tc
    Tm = t % Tc
    A = (1 - np.cos(2 * np.pi * Tm / Ts)) / 2 if Tm < Ts else 0

    UL = ULO * A;  UR = URO * A
    EL = ELD + ELS * A; ER = ERD + ERS * A

    Z1 = UL + X12 * EL - X1
    Z2 = X5 - UR - X6 * ER
    Z3 = UR + X6 * ER - X7
    Z4 = X11 - UL - X12 * EL

    S1 = float(Z1 > 0); S2 = float(Z2 > 0)
    S3 = float(Z3 > 0); S4 = float(Z4 > 0)

    dX = np.zeros(12)
    dX[0]  = (S1 * Z1 / (RL + R1) - X2) / C1
    dX[1]  = (X1 - R2 * X2 - X3) / L1
    dX[2]  = (X2 - X4) / C2
    dX[3]  = (X3 - R3 * X4 - X5) / L2
    dX[4]  = (X4 - S2 * Z2 / R4) / C3
    dX[5]  = S2 * Z2 / R4 - S3 * Z3 / (RR + R5)
    dX[6]  = (S3 * Z3 / (RR + R5) - X8) / C4
    dX[7]  = (X7 - R6 * X8 - X9) / L3
    dX[8]  = (X8 - X10) / C5
    dX[9]  = (X9 - R7 * X10 - X11) / L4
    dX[10] = (X10 - S4 * Z4 / R8) / C6
    dX[11] = S4 * Z4 / R8 - S1 * Z1 / (RL + R1)
    return dX


# ═══════════════════════════════════════════════════
# PLOT STYLE
# ═══════════════════════════════════════════════════
plt.rcParams.update({
    'font.family': 'serif',
    'font.size': 11,
    'axes.labelsize': 12,
    'axes.titlesize': 13,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'axes.grid': True,
    'grid.alpha': 0.3,
    'grid.linewidth': 0.5,
})

# Baseline steady-state initial conditions
X0 = [71.132, 8.890, 70.537, 67.359, 3.3268, 105.46,
      13.416, 0.78612, 13.392, 23.830, 11.295, 112.76]

t_span = [0, 1.6]
t_eval = np.linspace(0, 1.6, 1000)


# ═══════════════════════════════════════════════════
# FIGURE 1: HEALTHY BASELINE (steady state, 0-1.6s)
# ═══════════════════════════════════════════════════
print("Running healthy baseline...")
sol_h = solve_ivp(
    lambda t, X: cardiovascular_model(t, X, Tc=0.8, ULO=50.0, URO=24.0),
    t_span, X0, t_eval=t_eval,
    method='RK45', rtol=1e-6, atol=1e-9, max_step=0.005
)
t_h, X_h = sol_h.t, sol_h.y.T

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
fig.suptitle('Baseline Cardiovascular Simulation', fontsize=14, fontweight='bold')

ax1.plot(t_h, X_h[:, 0], 'b-', linewidth=1.5)
ax1.set_title('Aortic Pressure')
ax1.set_ylabel('mmHg')
ax1.set_xlim(t_span)
ax1.set_ylim([70, 125])

ax2.plot(t_h, X_h[:, 4], 'r-', linewidth=1.5)
ax2.set_title('Right Venous-Atrial Pressure')
ax2.set_ylabel('mmHg')
ax2.set_xlabel('Time (sec)')
ax2.set_xlim(t_span)
ax2.set_ylim([3.0, 5.25])

plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig('Figure_1.png')
plt.close()
print(f"  Figure_1.png  |  BP: {np.max(X_h[:,0]):.1f}/{np.min(X_h[:,0]):.1f} mmHg")


# ═══════════════════════════════════════════════════
# FIGURE 2: VF TRANSIENT (0-1.6s from baseline ICs)
# Shows the real-time collapse as VF takes hold.
# ═══════════════════════════════════════════════════
print("Running VF transient...")
sol_vf = solve_ivp(
    lambda t, X: cardiovascular_model(t, X, Tc=60.0/350.0, ULO=25.0, URO=12.0),
    t_span, X0, t_eval=t_eval,
    method='RK45', rtol=1e-6, atol=1e-9, max_step=0.005
)
t_vf, X_vf = sol_vf.t, sol_vf.y.T

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
fig.suptitle('Ventricular Fibrillation Simulation', fontsize=14, fontweight='bold')

ax1.plot(t_vf, X_vf[:, 0], 'b-', linewidth=1.5)
ax1.set_title('Aortic Pressure')
ax1.set_ylabel('mmHg')
ax1.set_xlim(t_span)
ax1.set_ylim([70, 125])

ax2.plot(t_vf, X_vf[:, 4], 'r-', linewidth=1.5)
ax2.set_title('Right Venous-Atrial Pressure')
ax2.set_ylabel('mmHg')
ax2.set_xlabel('Time (sec)')
ax2.set_xlim(t_span)
ax2.set_ylim([3.0, 5.25])

plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig('Figure_2.png')
plt.close()
print(f"  Figure_2.png  |  BP range: {np.max(X_vf[:,0]):.1f}/{np.min(X_vf[:,0]):.1f} mmHg")


# ═══════════════════════════════════════════════════
# FIGURE 3: CO BAR CHART (paper's Table 1 values)
# ═══════════════════════════════════════════════════
print("Generating CO bar chart...")
co_healthy = 5.88
co_vf = 2.21
pct_drop = (co_healthy - co_vf) / co_healthy * 100

fig, ax = plt.subplots(figsize=(6, 5))
bars = ax.bar(
    ['Healthy Baseline', 'Ventricular Fibrillation'],
    [co_healthy, co_vf],
    color=['#2563eb', '#b91c1c'],
    width=0.5,
    edgecolor='#334155',
    linewidth=0.8,
)
ax.set_ylabel('Cardiac Output (L/min)', fontsize=12)
ax.set_title('Impact of Ventricular Fibrillation on Cardiac Output',
             fontsize=13, fontweight='bold')
ax.set_ylim([0, 7])

for bar, val in zip(bars, [co_healthy, co_vf]):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.15,
            f'{val:.2f}', ha='center', va='bottom', fontsize=12, fontweight='bold')

ax.grid(True, axis='y', alpha=0.3)
ax.set_axisbelow(True)
plt.tight_layout()
plt.savefig('Figure_3.png')
plt.close()
print(f"  Figure_3.png  |  {co_healthy} -> {co_vf} ({pct_drop:.1f}% drop)")

print("\nDone. All figures saved to current directory.")