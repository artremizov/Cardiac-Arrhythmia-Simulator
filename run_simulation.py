import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt

# =======================================================
# THE MODEL FUNCTION (from cardiovascular_model.m)
# =======================================================
def cardiovascular_model(t, X):
    """
    This function defines the 12 differential equations for the closed-loop
    cardiovascular system based on the Avanzolini et al. 1988 paper.
    """

    # --- Model Parameters from Table III ---
    # Timing
    # STANDARD
    Tc = 0.8         # Cardiac period (s)
    # VENTRICULAR FIBRILLATION
    # Tc = 60/350         # Cardiac period (s)

    # Ventricular Properties
    # STANDARD
    ULO = 50      # Peak isovolumic pressure LV (mmHg)
    # VENTRICULAR FIBRILLATION
    # ULO = 25.0      # Peak isovolumic pressure LV (mmHg)
    # STANDARD
    URO = 24      # Peak isovolumic pressure RV (mmHg)
    # VENTRICULAR FIBRILLATION
    # URO = 12.0       # Peak isovolumic pressure RV (mmHg)
    ELD = 0.1        # Diastolic elastance LV (mmHg/cm^3)
    # STANDARD
    ELS = 1.375      # Systolic elastance LV (mmHg/cm^3)
    # VENTRICULAR FIBRILLATION
    # ELS = 0.6875     # Systolic elastance LV (mmHg/cm^3)
    ERD = 3.000E-02  # Diastolic elastance RV (mmHg/cm^3)
    # STANDARD
    ERS = 0.3288     # Systolic elastance RV (mmHg/cm^3)
    # VENTRICULAR FIBRILLATION
    # ERS = 0.1644     # Systolic elastance RV (mmHg/cm^3)
    RL  = 8.000E-02  # Myocardium viscosity LV (mmHg*s/cm^3)
    RR  = 1.750E-02  # Myocardium viscosity RV (mmHg*s/cm^3)

    # Resistances (mmHg*s/cm^3)
    R1 = 3.751E-03; R2 = 6.750E-02; R3 = 1.0; R4 = 3.751E-03;
    R5 = 3.751E-03; R6 = 3.376E-02; R7 = 0.1013; R8 = 3.751E-03;
    
    # Inertances (mmHg*s^2/cm^3)
    L1 = 8.250E-04; L2 = 3.600E-03; L3 = 7.500E-04; L4 = 3.080E-03;

    # Compliances (cm^3/mmHg)
    C1 = 0.22; C2 = 1.46; C3 = 20.0; C4 = 9.000E-02;
    C5 = 2.67; C6 = 46.7;

    # --- Unpack State Variables for Readability ---
    X1, X2, X3, X4, X5, X6, X7, X8, X9, X10, X11, X12 = X

    # --- Auxiliary Variables from Table I ---
    Ts = min(0.16 + 0.3 * Tc, 0.9 * Tc)  # cap so systole fits in the cycle above 225 bpm
    Tm = t % Tc # The modulo operator in Python is %
    
    if Tm < Ts:
        A = (1 - np.cos(2 * np.pi * Tm / Ts)) / 2
    else:
        A = 0

    UL = ULO * A
    UR = URO * A
    EL = ELD + ELS * A
    ER = ERD + ERS * A

    # Pressure drops across valves
    Z1 = UL + X12 * EL - X1
    Z2 = X5 - UR - X6 * ER
    Z3 = UR + X6 * ER - X7
    Z4 = X11 - UL - X12 * EL

    # Valve states (True for open, False for closed)
    S1 = (Z1 > 0); S2 = (Z2 > 0)
    S3 = (Z3 > 0); S4 = (Z4 > 0)

    # --- Derivatives from Table I ---
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
    dX[9] = (X9 - R7 * X10 - X11) / L4
    dX[10] = (X10 - S4 * Z4 / R8) / C6
    dX[11] = S4 * Z4 / R8 - S1 * Z1 / (RL + R1)
    
    return dX

# =======================================================
# THE MAIN SCRIPT (from run_simulation.m)
# =======================================================

# 1. Set the time span for the simulation
t_span = [0, 1.6]
t_eval = np.linspace(t_span[0], t_span[1], 1000) # Points where to store the solution

# 2. Set initial conditions for the 12 state variables
X0 = [71.132, 8.8900, 70.537, 67.359, 3.3268, 105.46,
      13.416, 0.78612, 13.392, 23.830, 11.295, 112.76]

# 3. Solve the system of differential equations
solution = solve_ivp(cardiovascular_model, t_span, X0, t_eval=t_eval)

# 4. Extract the results
t = solution.t
X = solution.y.T # Transpose the solution to match Octave's output shape

# 5. Plot the results
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
fig.suptitle('Baseline Cardiovascular Simulation', fontsize=16)

# Plot Aortic Pressure (X1)
ax1.plot(t, X[:, 0], 'b-', linewidth=1.5)
ax1.set_title('Aortic Pressure')
ax1.set_ylabel('mmHg')
ax1.grid(True)
ax1.set_xlim(t_span)
ax1.set_ylim([70, 120])

# Plot Right Venous-Atrial Pressure (X5)
ax2.plot(t, X[:, 4], 'r-', linewidth=1.5)
ax2.set_title('Right Venous-Atrial Pressure')
ax2.set_ylabel('mmHg')
ax2.set_xlabel('Time (sec)')
ax2.grid(True)
ax2.set_xlim(t_span)
ax2.set_ylim([3, 5])

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.show()