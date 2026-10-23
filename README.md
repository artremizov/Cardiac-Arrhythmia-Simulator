# CardioSim: Cardiovascular Hemodynamic Simulator

Interactive cardiovascular simulator built on the Avanzolini et al. (1988) lumped-parameter model, with a synthetic ECG after McSharry et al. (2003). It solves the closed-loop cardiovascular system as 12 coupled ODEs and includes 10 presets, from a healthy baseline to a prescribed ventricular-fibrillation-like state.

Developed as part of a research project on cardiac arrhythmia modeling at Washington State University.

Copyright (c) 2025 Artemii Remizov

## Quick Start

```bash
git clone https://github.com/artremizov/Cardiac-Arrhythmia-Simulator.git
cd Cardiac-Arrhythmia-Simulator

# Backend
pip install -r requirements.txt

# Run (serves the built web app + API on port 8000)
python api.py
```

Open your browser to **http://localhost:8000**.

The built web app is committed in `frontend/dist`. After changing anything in `frontend/src`, rebuild it:

```bash
cd frontend && npm install && npm run build && cd ..
```

### Development Mode (hot reload)

```bash
# Terminal 1: FastAPI backend
python api.py

# Terminal 2: Vite dev server with HMR (proxies /api to :8000)
cd frontend && npm run dev
```

Open **http://localhost:5173** for the dev server.

## Reproducing the paper

The `paper/` folder holds the code and results for:

> Artemii Remizov and Sergey Lapin. *Quantifying the hemodynamic effects of a prescribed ventricular-fibrillation-like state using a lumped-parameter cardiovascular model.*

From the repository root:

```bash
cd paper
python reproduce_paper.py                      # full run, about 15 minutes
python reproduce_paper.py --use-cached-sweep   # reuse results_sweep.csv instead of recomputing the sweep
```

The folder also holds the results the paper reports (`results_scenarios.csv`, `results_sweep.csv`, `results_beta.csv`, `results_contractility_definition.csv`).

Dependencies: `numpy` 2.0 or newer, `scipy`, `matplotlib`, `pillow` (all in `requirements.txt`). The script also writes Fig1 to Fig4 as PNG and TIFF into `paper/`; these are not committed.

## Features

- **12-ODE closed-loop model**: systemic and pulmonary circulation, four heart valves, time-varying ventricular elastance (Avanzolini 1988)
- **Synthetic ECG**: PQRST waveform synthesis with condition-specific morphology (wide QRS for VT, absent P waves for AF, irregular baseline for VF). The ECG is drawn for orientation and is not computed by the model
- **Irregular R-R intervals**: gamma-distributed beat timing for atrial fibrillation, uniformly random intervals of 0.12–0.25 s for ventricular fibrillation
- **10 presets** in four groups: Normal (Healthy Adult), Arrhythmia (Sinus Tachycardia, Sinus Bradycardia, Atrial Fibrillation, Ventricular Tachycardia), Structural (Systolic Heart Failure, Hypertension, Aortic Stenosis), Critical (Hemorrhagic Shock, Ventricular Fibrillation)
- **Results strip**: cardiac output, stroke volume, systolic/diastolic blood pressure, mean arterial pressure, ejection fraction and heart rate, each with its reference range; values outside the range are flagged
- **Comparison mode**: run a second preset alongside and see its values and percentage changes
- **Plots**: synchronized waveforms (ECG, aortic and LV pressure, venous and pulmonary artery pressure, LV volume), pressure–volume loop, and any of the 12 state variables
- **CSV export**: waveforms, PV loop data and the full time series for each run

## Using the Simulator

1. **Choose a preset** from the grouped list in the sidebar; the parameters load the preset's values
2. **Adjust parameters**: heart rate (30–400 bpm), contractility (10–160%), peripheral resistance and arterial compliance, by slider or by typing a value
3. **Run**: press **Run simulation**; the RK45 ODE solver runs server-side
4. **Read the results**: the strip at the top gives the hemodynamic metrics; the tabs give waveforms, the PV loop, state variables, CSV export and a description of the model
5. **Compare**: tick **Compare with a second preset** to run a second preset alongside; it is drawn dashed in every plot

## Model

The simulator implements the 12-state lumped-parameter model from Avanzolini et al. (1988), representing the cardiovascular system as an electrical analog circuit:

- **Resistance (R)**: viscous resistance to blood flow
- **Compliance (C)**: elasticity of vessel walls
- **Inertance (L)**: blood inertia

Ventricular contraction is driven by a time-varying activation function `A(t)` that modulates elastance between diastolic and systolic values each cycle. Systole lasts `Ts = min(0.16 + 0.3·Tc, 0.9·Tc)` seconds, where `Tc` is the R-R interval; the cap keeps systole inside the cycle above 225 bpm. Four diode-like valves (aortic, mitral, tricuspid, pulmonary) open and close based on pressure gradients.

Contractility scales `ULO`, `URO`, `ELS` and `ERS` together (100% is the published baseline).

**Solver:** `scipy.integrate.solve_ivp`, RK45, rtol=1e-5, atol=1e-8, max step 5 ms

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

### Healthy baseline

The Healthy Adult preset (30 s run):

| Metric | Simulated | Reference range |
|--------|-----------|-----------------|
| Cardiac Output | 4.64 L/min | 4.0–8.0 L/min |
| Systolic Pressure | 113 mmHg | 90–140 mmHg |
| Diastolic Pressure | 68 mmHg | 60–90 mmHg |

## File Structure

```
├── api.py                # FastAPI backend: REST API, serves the built web app
├── model.py              # ODE model, presets, parameter builder
├── ecg.py                # Synthetic ECG and R-R interval generation
├── metrics.py            # Hemodynamic metrics and simulation runner
├── paper/                # Paper reproduction scripts and results (see above)
├── frontend/
│   ├── src/
│   │   ├── components/   # Sidebar, results strip, plots, export, about
│   │   ├── lib/          # Design tokens, plot helpers, reference ranges
│   │   ├── App.tsx       # Layout and state
│   │   ├── api.ts        # Typed fetch wrappers
│   │   └── types.ts      # Shared TypeScript types
│   ├── dist/             # Built web app served by api.py
│   ├── vite.config.ts    # Vite build config with /api proxy
│   └── package.json
├── app.py, plots.py      # Older Plotly Dash interface (needs dash, dash-bootstrap-components, plotly, pandas)
├── cardiac_sim.py        # Older single-file Streamlit interface (needs streamlit, plotly, pandas)
├── run_simulation.py     # Minimal baseline script (matplotlib)
├── requirements.txt      # Python dependencies
├── LICENSE               # CC BY-NC 4.0
└── README.md
```

## Dependencies

**Python**
```
numpy>=2.0
scipy>=1.13.0
fastapi>=0.110.0
uvicorn>=0.29.0
matplotlib>=3.8.4
pillow>=10.0.0
```

**JavaScript (frontend)**
```
react 18, vite 5, typescript, tailwindcss (base reset only), uplot
```

## Citation

If you use this simulator in research or educational work, please cite:

- Remizov, A., & Lapin, S. Quantifying the hemodynamic effects of a prescribed ventricular-fibrillation-like state using a lumped-parameter cardiovascular model. Manuscript submitted to *PLOS ONE*.
- Avanzolini, G., Barbini, P., Cappello, A., & Cevese, A. (1988). CADCS simulation of the closed-loop cardiovascular system. *International Journal of Bio-Medical Computing*, 22(1), 39–49.
- McSharry, P. E., Clifford, G. D., Tarassenko, L., & Smith, L. A. (2003). A dynamical model for generating synthetic electrocardiogram signals. *IEEE Transactions on Biomedical Engineering*, 50(3), 289–294.

## License

Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0).
See [LICENSE](LICENSE) for details. This software may not be used for commercial purposes.
