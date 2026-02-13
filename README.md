# Cardiac Arrhythmia Simulator

Interactive cardiovascular hemodynamic simulator built on the Avanzolini et al. (1988) lumped-parameter model, featuring synthetic ECG generation, interactive Plotly visualizations, and support for 10 clinical conditions including arrhythmias, heart failure, and hemorrhagic shock.

Developed as part of a research project on cardiac arrhythmia modeling at Washington State University.

Copyright (c) 2025 Artemii Remizov

## Features

- **12-ODE Hemodynamic Model** — Full closed-loop cardiovascular system with time-varying ventricular elastance, four heart valves, and systemic/pulmonary circulation
- **Synthetic ECG Generation** — PQRST waveform synthesis with condition-specific morphology (wide QRS for VTach, absent P-waves for AFib, chaotic baseline for VFib)
- **Stochastic R-R Intervals** — Gamma-distributed beat timing for atrial fibrillation, chaotic intervals for ventricular fibrillation
- **10 Clinical Presets** — Healthy Adult, Ventricular Fibrillation, Ventricular Tachycardia, Atrial Fibrillation, Sinus Tachycardia, Sinus Bradycardia, Systolic Heart Failure, Hypertension, Aortic Stenosis, Hemorrhagic Shock
- **Comparison Mode** — Overlay two conditions side-by-side with delta metrics
- **Interactive PV Loops** — Left ventricular pressure-volume diagrams with educational annotations
- **CSV Export** — Download waveform data, PV loop data, and full simulation results
- **Real-Time Parameter Control** — Adjust heart rate, contractility, peripheral resistance, and arterial compliance with live results

## Quick Start

```bash
git clone https://github.com/artremizov/Cardiac-Arrhythmia-Simulator.git
cd Cardiac-Arrhythmia-Simulator
pip install -r requirements.txt
streamlit run cardiac_sim.py
```

The simulator will open in your browser at `http://localhost:8501`.

### Environment Setup (Optional)

Using conda:
```bash
conda create -n cardiac_sim python=3.9
conda activate cardiac_sim
pip install -r requirements.txt
```

Or using venv:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Using the Simulator

1. **Select a Preset** — Choose a predefined clinical condition from the sidebar. This automatically sets the sliders to typical values for that state.
2. **Customize Parameters** — Fine-tune heart rate, contractility, peripheral resistance, and arterial compliance with the sliders. Tooltips explain each parameter.
3. **Run Simulation** — Click "Run Simulation" to solve the ODEs. Longer durations generally produce more stable results.
4. **Analyze Results** — View KPIs, hemodynamic waveforms with synthetic ECG, pressure-volume loops, and individual state variables across the tabbed interface. Download CSV data for offline analysis.
5. **Compare Conditions** — Switch to comparison mode to overlay two clinical states and see percentage deltas across all metrics.

## Model Description

The simulator implements the 12-state lumped-parameter model from Avanzolini et al. (1988). The cardiovascular system is represented as an electrical analog circuit where:

- **Resistance (R)** represents viscous blood flow resistance
- **Compliance (C)** represents elastic vessel wall properties
- **Inertance (L)** represents blood inertia

Cardiac contraction is driven by a time-varying activation function that modulates ventricular elastance between diastolic and systolic values across each cardiac cycle.

### State Variables

| Variable | Description | Unit |
|----------|-------------|------|
| X1 | Aortic Pressure | mmHg |
| X2 | Aortic Flow | cm³/s |
| X3 | Systemic Arterial Pressure | mmHg |
| X4 | Systemic Peripheral Flow | cm³/s |
| X5 | Systemic Venous Pressure | mmHg |
| X6 | Right Ventricle Volume | cm³ |
| X7 | Pulmonary Artery Pressure | mmHg |
| X8 | Pulmonary Arterial Flow | cm³/s |
| X9 | Pulmonary Arteriole Pressure | mmHg |
| X10 | Pulmonary Venous Flow | cm³/s |
| X11 | Pulmonary Venous / LA Pressure | mmHg |
| X12 | Left Ventricle Volume | cm³ |

### Validation

The baseline healthy adult simulation produces:
- Cardiac Output: ~5.88 L/min (literature: 4.0-8.0 L/min)
- Systolic Pressure: ~115 mmHg (literature: 90-140 mmHg)
- Diastolic Pressure: ~70 mmHg (literature: 60-90 mmHg)

These values are consistent with the original Avanzolini paper and standard physiological references.

## File Structure

```
├── cardiac_sim.py        # Main Streamlit application (v2.0)
├── run_simulation.py     # Standalone baseline validation script
├── requirements.txt      # Python dependencies
├── LICENSE               # CC BY-NC 4.0
└── README.md
```

## Citation

If you use this simulator or code in your research or educational work, please cite the associated arXiv paper:

> Remizov, A., & Lapin, S. (2025). Quantifying the Hemodynamic Effects of Ventricular Fibrillation using a Verified Computational Model. *arXiv preprint arXiv:2511.00358*.

Alternatively, you can cite the GitHub repository directly:

> Remizov, A. (2025). Cardiac-Arrhythmia-Simulator (Version 2.0) [Software]. Available from https://github.com/artremizov/Cardiac-Arrhythmia-Simulator

## Model Reference

Avanzolini, G., Barbini, P., Cappello, A., & Cevenini, G. (1988). CADCS simulation of the closed-loop cardiovascular system. *International Journal of Bio-Medical Computing*, 22(1), 39-49.

## License

Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0). See the LICENSE file for details. This software may not be used for commercial purposes.