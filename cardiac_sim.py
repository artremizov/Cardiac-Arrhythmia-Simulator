# Copyright (c) 2025 Artemii Remizov
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)
# You may obtain a copy of the License at
# https://creativecommons.org/licenses/by-nc/4.0/
# See the LICENSE file for the full text.
#
# This software may not be used for commercial purposes.
import streamlit as st
import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt
import pandas as pd
import io

# =======================================================
# MODEL PARAMETERS (Centralized Definition)
# =======================================================
# Define baseline parameters in a dictionary for clarity
# Based on Avanzolini et al. 1988, Table III and typical values
PARAMS = {
    # Timing
    "Tc": 0.8,         # Cardiac period (s) -> Corresponds to 75 bpm baseline

    # Ventricular Properties (Baseline Peak Pressures & Elastances)
    "ULO": 50.0,     # Peak isovolumic pressure LV (mmHg)
    "URO": 24.0,     # Peak isovolumic pressure RV (mmHg)
    "ELD": 0.1,      # Diastolic elastance LV (mmHg/cm^3)
    "ELS": 1.375,    # Systolic elastance LV (mmHg/cm^3) - Tuned baseline
    "ERD": 0.03,     # Diastolic elastance RV (mmHg/cm^3)
    "ERS": 0.3288,   # Systolic elastance RV (mmHg/cm^3) - Tuned baseline

    # Myocardium Viscosity (Ventricular Resistance during flow)
    "RL": 0.08,      # Myocardium viscosity LV (mmHg*s/cm^3)
    "RR": 0.0175,    # Myocardium viscosity RV (mmHg*s/cm^3)

    # Resistances (mmHg*s/cm^3) - R_valve or R_vascular
    "R1": 0.003751,  # Aortic valve resistance
    "R2": 0.0675,    # Systemic arteries resistance (proximal)
    "R3": 1.0,       # Systemic peripheral resistance (main adjustable)
    "R4": 0.003751,  # Vena cava resistance (entering RA) - Simplified representation
    "R5": 0.003751,  # Tricuspid valve resistance
    "R6": 0.03376,   # Pulmonary arteries resistance
    "R7": 0.1013,    # Pulmonary peripheral resistance
    "R8": 0.003751,  # Mitral valve resistance

    # Inertances (mmHg*s^2/cm^3) - L_blood_inertia
    "L1": 0.000825,  # Aorta inertance
    "L2": 0.0036,    # Systemic arteries inertance
    "L3": 0.00075,   # Pulmonary artery inertance
    "L4": 0.00308,   # Pulmonary veins inertance

    # Compliances (cm^3/mmHg) - C_vascular_elasticity
    "C1": 0.22,      # Aortic compliance
    "C2": 1.46,      # Systemic arterial compliance (main adjustable)
    "C3": 20.0,      # Systemic venous compliance
    "C4": 0.09,      # Pulmonary arterial compliance
    "C5": 2.67,      # Pulmonary capillary/venous compliance
    "C6": 46.7,      # Left atrial / pulmonary venous compliance (lumped)

    # Initial Conditions (mmHg or cm^3) - from a stable baseline run
    "X0": [71.13, 8.89, 70.54, 67.36, 3.33, 105.46,
           13.42, 0.79, 13.39, 23.83, 11.30, 112.76]
           # X1=P_sa, X2=Q_aortic, X3=P_sart, X4=Q_sp, X5=P_sv, X6=V_rv
           # X7=P_pa, X8=Q_pulm_art, X9=P_part, X10=Q_pv, X11=P_pv/la, X12=V_lv
}

# Dictionary to map state variables to readable names and units
STATE_VAR_MAP = {
    0: ("Systemic Aortic Pressure (P_sa)", "mmHg"),
    1: ("Aortic Flow (Q_aortic)", "cm³/s"),
    2: ("Systemic Arterial Pressure (P_sart)", "mmHg"),
    3: ("Systemic Peripheral Flow (Q_sp)", "cm³/s"),
    4: ("Systemic Venous Pressure (P_sv)", "mmHg"),
    5: ("Right Ventricle Volume (V_rv)", "cm³"),
    6: ("Pulmonary Artery Pressure (P_pa)", "mmHg"),
    7: ("Pulmonary Arterial Flow (Q_pulm_art)", "cm³/s"),
    8: ("Pulmonary Arteriole Pressure (P_part)", "mmHg"),
    9: ("Pulmonary Venous Flow (Q_pv)", "cm³/s"),
    10: ("Pulmonary Venous / LA Pressure (P_pv/la)", "mmHg"),
    11: ("Left Ventricle Volume (V_lv)", "cm³"),
}


# =======================================================
# THE MODEL FUNCTION (Takes params dict)
# =======================================================
def cardiovascular_model(t, X, p):
    """
    Defines the 12 ODEs for the cardiovascular system.
    Args:
        t (float): Time.
        X (np.ndarray): Array of 12 state variables.
        p (dict): Dictionary containing model parameters.
    Returns:
        np.ndarray: Array of 12 derivatives dX/dt.
    """
    X1, X2, X3, X4, X5, X6, X7, X8, X9, X10, X11, X12 = X

    # Calculate time-varying elastance parameters
    Ts = 0.16 + 0.3 * p["Tc"] # Systole duration based on cardiac period
    Tm = t % p["Tc"]          # Time within the current cardiac cycle
    A = (1 - np.cos(2 * np.pi * Tm / Ts)) / 2 if Tm < Ts else 0 # Activation func

    # Time-varying variables
    UL = p["ULO"] * A
    UR = p["URO"] * A
    EL = p["ELD"] + p["ELS"] * A
    ER = p["ERD"] + p["ERS"] * A

    # Pressure drops across valves (potential gradients)
    # Z1: LV -> Aorta potential (Aortic Valve)
    # Z2: Systemic Veins -> RV potential (Tricuspid Valve equivalent - simplified)
    # Z3: RV -> Pulm Artery potential (Pulmonary Valve)
    # Z4: Pulm Veins/LA -> LV potential (Mitral Valve)
    Z1 = UL + X12 * EL - X1
    Z2 = X5 - (UR + X6 * ER) # Simplified Tricuspid opening pressure
    Z3 = UR + X6 * ER - X7
    Z4 = X11 - (UL + X12 * EL) # Simplified Mitral opening pressure

    # Valve states (1 for open, 0 for closed - using boolean directly)
    S1 = (Z1 > 0) # Aortic valve open if LV pressure > Aortic pressure
    S2 = (Z2 > 0) # Tricuspid valve open if Venous pressure > RV diastolic pressure
    S3 = (Z3 > 0) # Pulmonary valve open if RV pressure > Pulm Artery pressure
    S4 = (Z4 > 0) # Mitral valve open if LA/PV pressure > LV diastolic pressure

    # Calculate derivatives dX/dt based on Table I of Avanzolini et al.
    dX = np.zeros(12)
    # dP_sa/dt = (Q_aortic - Q_sart) / C1 -> Using X2 and calculating Q_sart implicitly
    dX[0]  = (S1 * Z1 / (p["RL"] + p["R1"]) - X2) / p["C1"] # dP_ao/dt (X1=P_ao)
    # dQ_aortic/dt = (P_ao - P_sart - R2*Q_aortic) / L1 -> Using X1, X3, R2, X2, L1
    dX[1]  = (X1 - p["R2"] * X2 - X3) / p["L1"] # dQ_ao/dt (X2=Q_ao)
    # dP_sart/dt = (Q_aortic - Q_sp) / C2 -> Using X2, X4, C2
    dX[2]  = (X2 - X4) / p["C2"] # dP_sart/dt (X3=P_sart)
    # dQ_sp/dt = (P_sart - P_sv - R3*Q_sp) / L2 -> Using X3, X5, R3, X4, L2
    dX[3]  = (X3 - p["R3"] * X4 - X5) / p["L2"] # dQ_sp/dt (X4=Q_sp)
    # dP_sv/dt = (Q_sp - Q_tricuspid) / C3 -> Using X4, S2*Z2/R4, C3
    dX[4]  = (X4 - S2 * Z2 / p["R4"]) / p["C3"] # dP_sv/dt (X5=P_sv)
    # dV_rv/dt = Q_tricuspid - Q_pulm_valve -> Using S2*Z2/R4, S3*Z3/(RR+R5)
    dX[5]  = S2 * Z2 / p["R4"] - S3 * Z3 / (p["RR"] + p["R5"]) # dV_rv/dt (X6=V_rv)
    # dP_pa/dt = (Q_pulm_valve - Q_part) / C4 -> Using S3*Z3/(RR+R5), X8, C4
    dX[6]  = (S3 * Z3 / (p["RR"] + p["R5"]) - X8) / p["C4"] # dP_pa/dt (X7=P_pa)
    # dQ_part/dt = (P_pa - P_part - R6*Q_part) / L3 -> Using X7, X9, R6, X8, L3
    dX[7]  = (X7 - p["R6"] * X8 - X9) / p["L3"] # dQ_pa/dt (X8=Q_pa)
    # dP_part/dt = (Q_part - Q_pv) / C5 -> Using X8, X10, C5
    dX[8]  = (X8 - X10) / p["C5"] # dP_pcap/dt (X9=P_pcap)
    # dQ_pv/dt = (P_part - P_pv/la - R7*Q_pv) / L4 -> Using X9, X11, R7, X10, L4
    dX[9]  = (X9 - p["R7"] * X10 - X11) / p["L4"] # dQ_pv/dt (X10=Q_pv)
    # dP_pv/la/dt = (Q_pv - Q_mitral) / C6 -> Using X10, S4*Z4/R8, C6
    dX[10] = (X10 - S4 * Z4 / p["R8"]) / p["C6"] # dP_la/dt (X11=P_la)
    # dV_lv/dt = Q_mitral - Q_aortic -> Using S4*Z4/R8, S1*Z1/(RL+R1)
    dX[11] = S4 * Z4 / p["R8"] - S1 * Z1 / (p["RL"] + p["R1"]) # dV_lv/dt (X12=V_lv)

    return dX

# =======================================================
# HELPER FUNCTIONS
# =======================================================
def calculate_derived_metrics(t, X, p):
    """Calculates Cardiac Output, Stroke Volume, Pressures, etc. from simulation results."""
    # Recalculate flows and pressures needed for CO/SV/PV loop
    LVOF = np.zeros(len(t)) # Left Ventricular Outflow (Aortic Flow)
    LVP = np.zeros(len(t))  # Left Ventricular Pressure
    Ts = 0.16 + 0.3 * p["Tc"]
    for i in range(len(t)):
        Tm = t[i] % p["Tc"]
        A = (1-np.cos(2*np.pi*Tm/Ts))/2 if Tm < Ts else 0
        UL = p["ULO"] * A
        EL = p["ELD"] + p["ELS"] * A
        Z1 = UL + X[i, 11] * EL - X[i, 0] # LV Pressure - Aortic Pressure
        S1 = (Z1 > 0) # Aortic valve open state
        LVOF[i] = Z1 * S1 / (p["RL"] + p["R1"]) # Flow through aortic valve if open

        # Calculate instantaneous LVP: P_lv = E_lv(t) * (V_lv(t) - V0)
        # Avanzolini uses P_lv = U(t) + E(t)*V(t) - R_myo * Q_out
        # V0 is implicit in U(t) and E(t) definition origin
        LVP[i] = UL + EL * X[i, 11] - p["RL"] * LVOF[i]

    # --- Find the last STABLE cardiac cycle ---
    # Analyze the last two cycles to ensure stability, calculate metrics over the second to last
    end_time = t[-1]
    if end_time < 2 * p["Tc"]: # Ensure enough time has passed
         st.warning("Simulation duration too short for stable cycle analysis. Increase duration.")
         return 0, 0, 0, 0, np.array([]), np.array([]), np.array([]) # Return zeros/empty

    stable_beat_start_time = max(t[0], end_time - 2 * p["Tc"])
    stable_beat_end_time = end_time - p["Tc"]

    stable_beat_indices = np.where((t >= stable_beat_start_time) & (t < stable_beat_end_time))[0]

    if len(stable_beat_indices) <= 1:
        st.warning("Could not isolate a stable beat. Check simulation parameters or duration.")
        return 0, 0, 0, 0, np.array([]), np.array([]), np.array([])

    t_beat = t[stable_beat_indices]
    LVOF_beat = LVOF[stable_beat_indices]
    LV_Volume_beat = X[stable_beat_indices, 11]
    LVP_beat = LVP[stable_beat_indices]
    AorticPressure_beat = X[stable_beat_indices, 0]

    # Calculate metrics over this stable beat
    StrokeVolume = np.trapz(LVOF_beat, t_beat)
    CardiacOutput = StrokeVolume * (60.0 / p["Tc"]) / 1000 # L/min
    SystolicPressure = np.max(AorticPressure_beat)
    DiastolicPressure = np.min(AorticPressure_beat)

    return CardiacOutput, StrokeVolume, SystolicPressure, DiastolicPressure, LV_Volume_beat, LVP_beat, AorticPressure_beat

def plot_waveforms(t, X, p, t_range_display):
    """Generates Matplotlib figure for hemodynamic waveforms."""
    fig, axes = plt.subplots(3, 1, sharex=True, figsize=(10, 8))
    fig.suptitle('Hemodynamic Waveforms', fontsize=16)

    # Plot Aortic Pressure (P_sa = X1)
    axes[0].plot(t, X[:, 0], 'b-', linewidth=1.5, label='Aortic Pressure')
    axes[0].set_ylabel('Pressure (mmHg)')
    axes[0].grid(True)
    axes[0].set_title('Systemic Pressures')
    axes[0].legend(loc='upper right')
    # Maybe add LVP here too? Recalculate LVP as in calculate_derived_metrics
    LVP = np.zeros(len(t))
    Ts = 0.16 + 0.3 * p["Tc"]
    for i in range(len(t)):
        Tm = t[i] % p["Tc"]
        A = (1-np.cos(2*np.pi*Tm/Ts))/2 if Tm < Ts else 0
        UL = p["ULO"] * A
        EL = p["ELD"] + p["ELS"] * A
        # Need LVOF again, simplified here - requires full calc if needed accurately
        LVOF_i = max(0, (UL + X[i, 11] * EL - X[i, 0]) / (p["RL"] + p["R1"]))
        LVP[i] = UL + EL * X[i, 11] - p["RL"] * LVOF_i
    axes[0].plot(t, LVP, 'g--', linewidth=1.0, label='LV Pressure')
    axes[0].legend(loc='upper right')


    # Plot Pulmonary Artery Pressure (P_pa = X7)
    axes[1].plot(t, X[:, 6], 'r-', linewidth=1.5, label='Pulmonary Art. Pressure')
    # Plot Right Venous/Atrial Pressure (P_sv = X5)
    axes[1].plot(t, X[:, 4], color='purple', linestyle='-', linewidth=1.5, label='Systemic Venous Pressure')
    axes[1].set_ylabel('Pressure (mmHg)')
    axes[1].grid(True)
    axes[1].set_title('Pulmonary & Venous Pressures')
    axes[1].legend(loc='upper right')

    # Plot LV Volume (V_lv = X12)
    axes[2].plot(t, X[:, 11], 'm-', linewidth=1.5, label='LV Volume')
    axes[2].set_ylabel('Volume (cm³)')
    axes[2].set_xlabel('Time (sec)')
    axes[2].grid(True)
    axes[2].set_title('Left Ventricular Volume')
    axes[2].legend(loc='upper right')

    axes[2].set_xlim(t_range_display) # Show only the requested time range

    plt.tight_layout(rect=[0, 0.03, 1, 0.95]) # Adjust layout to prevent title overlap
    return fig

def plot_pv_loop(lv_volume, lv_pressure):
    """Generates Matplotlib figure for the PV loop."""
    fig, ax = plt.subplots(1, 1, figsize=(6, 5))
    if len(lv_volume) > 0 and len(lv_pressure) > 0:
        ax.plot(lv_volume, lv_pressure, 'g-', linewidth=2)
    else:
        ax.text(0.5, 0.5, 'PV Loop data not available\n(Check simulation stability)',
                horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)
    ax.set_title('Left Ventricle Pressure-Volume (PV) Loop')
    ax.set_xlabel('LV Volume (cm³)')
    ax.set_ylabel('LV Pressure (mmHg)')
    ax.grid(True)
    plt.tight_layout()
    return fig

# =======================================================
# STREAMLIT UI LAYOUT
# =======================================================
st.set_page_config(layout="wide", page_title="Cardiovascular Simulator")

st.title('Interactive Cardiovascular Simulator')
st.write("""
This application simulates the human cardiovascular system based on the verified 1988 Avanzolini et al. model.
Select a preset clinical condition or manually adjust physiological parameters in the sidebar to observe the impact.
""")

# --- Initialize Session State ---
if 'simulation_results' not in st.session_state:
    st.session_state.simulation_results = None
if 'current_params' not in st.session_state:
    st.session_state.current_params = PARAMS.copy() # Store the adjustable parameters


# --- Sidebar for User Inputs ---
with st.sidebar:
    st.header('Simulation Controls')
    st.markdown('**1. Select Preset Condition**')

    preset_options = {
        'Healthy Adult':          {"hr": 75, "contract": 100, "resist": 1.0, "compl": 1.46},
        'Ventricular Fibrillation': {"hr": 350, "contract": 50, "resist": 1.0, "compl": 1.46},
        'Tachycardia':            {"hr": 120, "contract": 100, "resist": 1.0, "compl": 1.46},
        'Heart Failure (Systolic)':{"hr": 90, "contract": 60, "resist": 1.2, "compl": 1.46},
        'Hypertension':           {"hr": 80, "contract": 110, "resist": 1.5, "compl": 1.2},
    }
    preset = st.radio(
        "Choose a condition:",
        options=list(preset_options.keys()),
        index=0,
        key='preset_choice'
    )

    # Update defaults based on preset IF radio button changed
    defaults = preset_options[preset]

    st.markdown('**2. Customize Parameters**')
    # Use defaults from selected preset for sliders
    heart_rate = st.slider('Heart Rate (bpm)', 40, 400, defaults["hr"], key='hr_slider',
                           help="Adjusts the frequency of heartbeats.")
    contractility = st.slider('Ventricular Contractility (%)', 10, 150, defaults["contract"], key='contract_slider',
                              help="Relative strength of heart muscle contraction (100% = baseline). Affects peak pressures ULO and URO.")
    resistance = st.slider('Systemic Peripheral Resistance (R3, mmHg·s/cm³)', 0.5, 2.5, defaults["resist"], step=0.1, key='resist_slider',
                           help="Resistance blood encounters in the body's smaller arteries and arterioles. Higher values increase afterload.")
    compliance = st.slider('Arterial Compliance (C2, cm³/mmHg)', 0.8, 2.0, defaults["compl"], step=0.01, key='compl_slider',
                           help="Elasticity ('stretchiness') of the major systemic arteries. Lower values mean stiffer arteries (e.g., aging, hypertension).")

    st.markdown('**3. Simulation Settings**')
    sim_duration = st.number_input("Simulation Duration (s)", min_value=1.0, max_value=30.0, value=5.0, step=0.5,
                                   help="Total time to simulate. Longer durations allow the system to reach a more stable state.")
    plot_duration = st.number_input("Plot Last N Seconds", min_value=0.5, max_value=sim_duration, value=min(2.0, sim_duration), step=0.1,
                                   help="How many seconds from the *end* of the simulation to display in the plots.")


    # --- Run Button ---
    run_button = st.button('Run Simulation', type="primary", use_container_width=True)

# --- Main Simulation Logic & Display ---
if run_button:
    with st.spinner('Running simulation... This may take a moment.'):
        # Update PARAMS dictionary with values from sliders
        current_params = PARAMS.copy() # Start fresh from defaults
        current_params["Tc"] = 60.0 / heart_rate
        # Adjust baseline ULO/URO based on percentage slider
        baseline_ULO = PARAMS["ULO"] # Get the original baseline
        baseline_URO = PARAMS["URO"]
        current_params["ULO"] = baseline_ULO * (contractility / 100.0)
        current_params["URO"] = baseline_URO * (contractility / 100.0)
        current_params["R3"] = resistance
        current_params["C2"] = compliance

        # Store the parameters used for this run
        st.session_state.current_params = current_params

        # Set time span and evaluation points
        t_span = [0, sim_duration]
        num_points = int(sim_duration * 500) # Increase points for better resolution
        t_eval = np.linspace(t_span[0], t_span[1], num_points)

        try:
            # Solve the ODEs
            solution = solve_ivp(
                lambda t, X: cardiovascular_model(t, X, current_params),
                t_span, current_params["X0"], t_eval=t_eval, method='RK45', # Use default RK45
                rtol=1e-4, atol=1e-7 # Slightly tighter tolerances
            )

            if solution.status != 0:
                 st.error(f"ODE solver failed to converge. Status: {solution.status}, Message: {solution.message}")
                 st.session_state.simulation_results = None
            else:
                st.success("Simulation complete!")
                st.session_state.simulation_results = solution # Store the full solution
                st.session_state.plot_range = [max(0, sim_duration - plot_duration), sim_duration]


        except Exception as e:
            st.error(f"An error occurred during simulation: {e}")
            st.session_state.simulation_results = None

# --- Display Results if Available ---
if st.session_state.simulation_results is not None:
    solution = st.session_state.simulation_results
    params_used = st.session_state.current_params
    t = solution.t
    X = solution.y.T

    st.header('Simulation Results')
    st.markdown("---")

    # Perform analysis
    (CardiacOutput, StrokeVolume, SystolicPressure, DiastolicPressure,
     LV_Volume_beat, LVP_beat, AorticPressure_beat) = calculate_derived_metrics(t, X, params_used)

    st.subheader('Key Performance Indicators (Last Stable Cycle)')
    if CardiacOutput > 0: # Check if calculation was successful
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Cardiac Output", f"{CardiacOutput:.2f} L/min")
        col2.metric("Stroke Volume", f"{StrokeVolume:.2f} cm³")
        col3.metric("Systolic Pressure", f"{SystolicPressure:.1f} mmHg")
        col4.metric("Diastolic Pressure", f"{DiastolicPressure:.1f} mmHg")
    else:
        st.warning("Could not calculate stable cycle metrics. Please check parameters or increase simulation duration.")

    st.markdown("---")

    st.subheader('Graphical Analysis')

    # Define time range for plots based on user input
    plot_start_time = st.session_state.plot_range[0]
    plot_end_time = st.session_state.plot_range[1]
    plot_indices = np.where((t >= plot_start_time) & (t <= plot_end_time))[0]

    tab1, tab2, tab3 = st.tabs(["Hemodynamic Waveforms", "PV Loop", "All State Variables"])

    with tab1:
        st.markdown(f"Displaying last {plot_end_time - plot_start_time:.1f} seconds of simulation.")
        fig_wave = plot_waveforms(t, X, params_used, [plot_start_time, plot_end_time])
        st.pyplot(fig_wave, use_container_width=True)

        # Prepare waveform data for download
        waveform_df = pd.DataFrame(X[plot_indices], columns=[STATE_VAR_MAP[i][0] for i in range(12)])
        waveform_df.insert(0, "Time (s)", t[plot_indices])
        csv_wave = waveform_df.to_csv(index=False).encode('utf-8')
        st.download_button(
           label="Download Waveform Data (CSV)",
           data=csv_wave,
           file_name=f'waveforms_{preset.replace(" ", "_").lower()}.csv',
           mime='text/csv',
        )

    with tab2:
        st.markdown("Calculated from the last stable cardiac cycle.")
        fig_pv = plot_pv_loop(LV_Volume_beat, LVP_beat)
        st.pyplot(fig_pv, use_container_width=True)

         # Prepare PV loop data for download
        if len(LV_Volume_beat) > 0:
            pv_df = pd.DataFrame({'LV Volume (cm³)': LV_Volume_beat, 'LV Pressure (mmHg)': LVP_beat})
            csv_pv = pv_df.to_csv(index=False).encode('utf-8')
            st.download_button(
               label="Download PV Loop Data (CSV)",
               data=csv_pv,
               file_name=f'pv_loop_{preset.replace(" ", "_").lower()}.csv',
               mime='text/csv',
            )


    with tab3:
        st.markdown("Showing all 12 state variables over the selected plot duration.")
        fig_all, axes_all = plt.subplots(6, 2, figsize=(12, 15), sharex=True)
        axes_all_flat = axes_all.flatten()
        for i in range(12):
            var_name, unit = STATE_VAR_MAP[i]
            axes_all_flat[i].plot(t, X[:, i], linewidth=1)
            axes_all_flat[i].set_title(f"X{i+1}: {var_name}")
            axes_all_flat[i].set_ylabel(unit)
            axes_all_flat[i].grid(True)
            if i >= 10: # Only add xlabel to bottom plots
                 axes_all_flat[i].set_xlabel("Time (s)")
            axes_all_flat[i].tick_params(axis='y', labelsize=8)


        axes_all_flat[0].set_xlim([plot_start_time, plot_end_time]) # Apply time range
        plt.tight_layout()
        st.pyplot(fig_all, use_container_width=True)

        # Option to download full raw data
        full_df = pd.DataFrame(X, columns=[STATE_VAR_MAP[i][0] for i in range(12)])
        full_df.insert(0, "Time (s)", t)
        csv_full = full_df.to_csv(index=False).encode('utf-8')
        st.download_button(
           label="Download Full Simulation Data (CSV)",
           data=csv_full,
           file_name=f'full_sim_data_{preset.replace(" ", "_").lower()}.csv',
           mime='text/csv',
        )

else:
    # Show instructions or a placeholder if no simulation has been run yet
    st.info("Adjust parameters in the sidebar and click 'Run Simulation' to start.")

# --- Add Expander for Model Details ---
with st.expander("Model Parameters and Details"):
    st.write("This simulator implements the 12-state ODE model from Avanzolini et al. (1988).")
    st.write("**Baseline Parameters Used (can be modified via sliders):**")
    param_df = pd.DataFrame.from_dict(PARAMS, orient='index', columns=['Value'])
    st.dataframe(param_df[~param_df.index.isin(['X0'])], use_container_width=True) # Exclude initial conditions from display
    st.write("**State Variables:**")
    state_df = pd.DataFrame.from_dict(STATE_VAR_MAP, orient='index', columns=['Name', 'Unit'])
    st.dataframe(state_df, use_container_width=True)
    st.write("Reference: Avanzolini, G., Barbini, P., Cappello, A., & Cevenini, G. (1988). CADCS simulation of the closed-loop cardiovascular system. *International Journal of Bio-Medical Computing*, 22(1), 39-49.")