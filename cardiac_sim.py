import streamlit as st
import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt

# =======================================================
# THE MODEL FUNCTION (Slightly modified to accept parameters)
# =======================================================
def cardiovascular_model(t, X, ULO, URO, Tc):
    """
    This function defines the 12 differential equations for the cardiovascular system.
    It now accepts key parameters as arguments to allow for interactive changes.
    """
    # --- Model Parameters ---
    ELD = 0.1; ELS = 1.375; ERD = 3.000E-02; ERS = 0.3288;
    RL  = 8.000E-02; RR  = 1.750E-02; R1 = 3.751E-03; R2 = 6.750E-02;
    R3 = 1.0; R4 = 3.751E-03; R5 = 3.751E-03; R6 = 3.376E-02;
    R7 = 0.1013; R8 = 3.751E-03; L1 = 8.250E-04; L2 = 3.600E-03;
    L3 = 7.500E-04; L4 = 3.080E-03; C1 = 0.22; C2 = 1.46;
    C3 = 20.0; C4 = 9.000E-02; C5 = 2.67; C6 = 46.7;

    X1, X2, X3, X4, X5, X6, X7, X8, X9, X10, X11, X12 = X

    Ts = 0.16 + 0.3 * Tc
    Tm = t % Tc
    A = (1 - np.cos(2 * np.pi * Tm / Ts)) / 2 if Tm < Ts else 0

    UL = ULO * A; UR = URO * A; EL = ELD + ELS * A; ER = ERD + ERS * A;

    Z1 = UL + X12 * EL - X1; Z2 = X5 - UR - X6 * ER;
    Z3 = UR + X6 * ER - X7; Z4 = X11 - UL - X12 * EL;

    S1 = (Z1 > 0); S2 = (Z2 > 0); S3 = (Z3 > 0); S4 = (Z4 > 0);

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
# STREAMLIT USER INTERFACE
# =======================================================
st.title('Interactive Cardiovascular Simulator')
st.write("""
This application simulates the human cardiovascular system based on the 1988 Avanzolini et al. model. 
Use the sliders to change physiological parameters and observe the impact on hemodynamic waveforms and cardiac output.
""")

# --- Sidebar for User Inputs ---
st.sidebar.header('Simulation Parameters')
st.sidebar.markdown('### Select a Preset')

preset = st.sidebar.radio(
    "Choose a patient condition:",
    ('Healthy Adult', 'Ventricular Fibrillation (Adult)')
)

if preset == 'Healthy Adult':
    hr_default, contract_default = 75, 100
else:
    hr_default, contract_default = 350, 50

st.sidebar.markdown('### Or Customize Manually')
heart_rate = st.sidebar.slider('Heart Rate (beats per minute)', 40, 400, hr_default)
contractility = st.sidebar.slider('Ventricular Contractility (%)', 10, 120, contract_default)

# --- Main Simulation Logic ---
if st.sidebar.button('Run Simulation'):
    # Convert user inputs to model parameters
    Tc = 60.0 / heart_rate
    ULO = 50.0 * (contractility / 100.0)
    URO = 24.0 * (contractility / 100.0)
    
    # Set initial conditions and time span
    t_span = [0, 1.6]
    t_eval = np.linspace(t_span[0], t_span[1], 1000)
    X0 = [71.132, 8.8900, 70.537, 67.359, 3.3268, 105.46,
          13.416, 0.78612, 13.392, 23.830, 11.295, 112.76]

    # Solve the ODEs
    solution = solve_ivp(cardiovascular_model, t_span, X0, args=(ULO, URO, Tc), t_eval=t_eval)
    t = solution.t
    X = solution.y.T

    # --- Post-Simulation Analysis ---
    # (Simplified for display - full analysis from your paper script)
    LVOF = np.zeros(len(t))
    RL=8.000E-02; R1=3.751E-03; ELD=0.1; ELS=1.375;
    for i in range(len(t)):
        Tm = t[i] % Tc
        A = (1-np.cos(2*np.pi*Tm/(0.16+0.3*Tc)))/2 if Tm<(0.16+0.3*Tc) else 0
        UL = ULO * A
        EL = ELD + ELS * A
        Z1 = UL + X[i, 11] * EL - X[i, 0]
        S1 = (Z1 > 0)
        LVOF[i] = Z1 * S1 / (RL + R1)
    
    last_beat_indices = np.where(t >= (t[-1] - Tc))
    StrokeVolume = np.trapz(LVOF[last_beat_indices], t[last_beat_indices])
    CardiacOutput = StrokeVolume * heart_rate / 1000

    # --- Display Results ---
    st.header('Simulation Results')
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Heart Rate", f"{heart_rate} BPM")
    col2.metric("Stroke Volume", f"{StrokeVolume:.2f} cm³")
    col3.metric("Cardiac Output", f"{CardiacOutput:.2f} L/min")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    fig.suptitle('Hemodynamic Waveforms', fontsize=16)

    ax1.plot(t, X[:, 0], 'b-', linewidth=1.5)
    ax1.set_title('Aortic Pressure')
    ax1.set_ylabel('mmHg')
    ax1.grid(True)
    ax1.set_xlim(t_span)

    ax2.plot(t, X[:, 4], 'r-', linewidth=1.5)
    ax2.set_title('Right Venous-Atrial Pressure')
    ax2.set_ylabel('mmHg')
    ax2.set_xlabel('Time (sec)')
    ax2.grid(True)

    st.pyplot(fig)