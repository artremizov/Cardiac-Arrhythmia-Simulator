import streamlit as st
import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt

# =======================================================
# THE MODEL FUNCTION (Modified to accept more parameters)
# =======================================================
def cardiovascular_model(t, X, ULO, URO, Tc, R3, C2):
    """
    This function defines the 12 differential equations for the cardiovascular system.
    It now accepts key physiological parameters as arguments for interactive changes.
    """
    # --- Model Parameters (Constants) ---
    ELD = 0.1; ELS = 1.375; ERD = 3.000E-02; ERS = 0.3288;
    RL  = 8.000E-02; RR  = 1.750E-02; R1 = 3.751E-03; R2 = 6.750E-02;
    R4 = 3.751E-03; R5 = 3.751E-03; R6 = 3.376E-02;
    R7 = 0.1013; R8 = 3.751E-03; L1 = 8.250E-04; L2 = 3.600E-03;
    L3 = 7.500E-04; L4 = 3.080E-03; C1 = 0.22; C3 = 20.0; C4 = 9.000E-02; 
    C5 = 2.67; C6 = 46.7;

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
st.set_page_config(layout="wide")

st.title('Advanced Interactive Cardiovascular Simulator')
st.write("""
This application simulates the human cardiovascular system based on the 1988 Avanzolini et al. model. 
Select a preset clinical condition or manually adjust physiological parameters in the sidebar to observe the impact on hemodynamic waveforms, cardiac performance, and ventricular function.
""")

# --- Sidebar for User Inputs ---
st.sidebar.header('Simulation Control Panel')
st.sidebar.markdown('### 1. Select a Preset Condition')

preset = st.sidebar.radio(
    "Choose a patient condition:",
    ('Healthy Adult', 'Ventricular Fibrillation', 'Tachycardia', 'Heart Failure', 'Hypertension'),
    index=0
)

# Set default values based on preset
if preset == 'Healthy Adult':
    hr_default, contract_default, resistance_default, compliance_default = 75, 100, 1.0, 1.46
elif preset == 'Ventricular Fibrillation':
    hr_default, contract_default, resistance_default, compliance_default = 350, 50, 1.0, 1.46
elif preset == 'Tachycardia':
    hr_default, contract_default, resistance_default, compliance_default = 120, 100, 1.0, 1.46
elif preset == 'Heart Failure':
    hr_default, contract_default, resistance_default, compliance_default = 90, 60, 1.2, 1.46
else: # Hypertension
    hr_default, contract_default, resistance_default, compliance_default = 80, 110, 1.5, 1.2

st.sidebar.markdown('### 2. Customize Parameters Manually')
heart_rate = st.sidebar.slider('Heart Rate (beats per minute)', 40, 400, hr_default)
contractility = st.sidebar.slider('Ventricular Contractility (%)', 10, 120, contract_default)
resistance = st.sidebar.slider('Systemic Peripheral Resistance (R3)', 0.5, 2.5, resistance_default)
compliance = st.sidebar.slider('Arterial Compliance (C2)', 0.8, 2.0, compliance_default)

# --- Main Simulation Logic ---
if st.sidebar.button('Run Simulation', type="primary"):
    with st.spinner('Running simulation...'):
        # Convert user inputs to model parameters
        Tc = 60.0 / heart_rate
        ULO = 50.0 * (contractility / 100.0)
        URO = 24.0 * (contractility / 100.0)
        R3 = resistance
        C2 = compliance
        
        # Set initial conditions and time span
        t_span = [0, 5.0] # Extend time to see more cycles and stabilization
        t_eval = np.linspace(t_span[0], t_span[1], 2500)
        X0 = [71.132, 8.8900, 70.537, 67.359, 3.3268, 105.46,
              13.416, 0.78612, 13.392, 23.830, 11.295, 112.76]

        # Solve the ODEs
        solution = solve_ivp(
            lambda t, X: cardiovascular_model(t, X, ULO, URO, Tc, R3, C2), 
            t_span, X0, t_eval=t_eval, method='RK45'
        )
        t = solution.t
        X = solution.y.T

        # --- Post-Simulation Analysis (Advanced Version) ---
        LVOF = np.zeros(len(t))
        LVP = np.zeros(len(t))
        RL=8.000E-02; R1=3.751E-03; ELD=0.1; ELS=1.375;
        for i in range(len(t)):
            Tm = t[i] % Tc
            A = (1-np.cos(2*np.pi*Tm/(0.16+0.3*Tc)))/2 if Tm<(0.16+0.3*Tc) else 0
            UL = ULO * A
            EL = ELD + ELS * A
            Z1 = UL + X[i, 11] * EL - X[i, 0]
            S1 = (Z1 > 0)
            LVOF[i] = Z1 * S1 / (RL + R1)
            LVP[i] = UL + EL * X[i, 11] - RL * LVOF[i] # Left Ventricular Pressure

        # --- Find the last STABLE beat ---
        end_time = t[-1]
        stable_beat_start_time = end_time - 2 * Tc
        stable_beat_end_time = end_time - Tc

        if stable_beat_start_time < t[0]:
            stable_beat_start_time = t[0]
            stable_beat_end_time = t[0] + Tc

        stable_beat_indices = np.where((t >= stable_beat_start_time) & (t < stable_beat_end_time))

        t_beat = t[stable_beat_indices]
        LVOF_beat = LVOF[stable_beat_indices]
        
        # --- DEFINITIVE FIX for ValueError ---
        # Ensure both arrays are 1D vectors (flattened) before plotting
        LV_Volume_beat = X[stable_beat_indices, 11].flatten()
        LVP_beat = LVP[stable_beat_indices].flatten()
        # -------------------------------------

        if len(t_beat) > 1:
            StrokeVolume = np.trapz(LVOF_beat, t_beat)
        else:
            StrokeVolume = 0

        CardiacOutput = StrokeVolume * heart_rate / 1000
        SystolicPressure = np.max(X[stable_beat_indices, 0]) if len(stable_beat_indices[0]) > 0 else 0
        DiastolicPressure = np.min(X[stable_beat_indices, 0]) if len(stable_beat_indices[0]) > 0 else 0

    # --- Display Results ---
    st.header('Simulation Results')
    st.markdown("---")
    
    st.subheader('Key Performance Indicators')
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Cardiac Output", f"{CardiacOutput:.2f} L/min")
    col2.metric("Stroke Volume", f"{StrokeVolume:.2f} cm³")
    col3.metric("Systolic Pressure", f"{SystolicPressure:.1f} mmHg")
    col4.metric("Diastolic Pressure", f"{DiastolicPressure:.1f} mmHg")
    
    st.markdown("---")
    
    st.subheader('Graphical Analysis')
    tab1, tab2 = st.tabs(["Hemodynamic Waveforms", "Ventricular Function (PV Loop)"])

    with tab1:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
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

    with tab2:
        fig2, ax = plt.subplots(1, 1, figsize=(8, 6))
        if len(LV_Volume_beat) > 0 and len(LVP_beat) > 0:
            ax.plot(LV_Volume_beat, LVP_beat, 'g-', linewidth=2)
        ax.set_title('Left Ventricle Pressure-Volume (PV) Loop')
        ax.set_xlabel('LV Volume (cm³)')
        ax.set_ylabel('LV Pressure (mmHg)')
        ax.grid(True)
        st.pyplot(fig2)