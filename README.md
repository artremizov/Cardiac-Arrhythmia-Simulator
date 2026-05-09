# CardioSim — Cardiovascular Hemodynamic Simulator

Interactive cardiovascular simulator built on the verified Avanzolini et al. (1988) lumped-parameter model with McSharry-inspired synthetic ECG generation. Models the complete closed-loop cardiovascular system with 12 coupled ODEs and supports 10 clinical presets ranging from healthy baseline to ventricular fibrillation.

Developed as part of a research project on cardiac arrhythmia modeling at Washington State University.

Copyright (c) 2025 Artemii Remizov

## Quick Start

```bash
git clone https://github.com/artremizov/CardiacArrhythmia.git
cd CardiacArrhythmia

# Backend
pip install -r requirements.txt

# Frontend (build once)
cd frontend && npm install && npm run build && cd ..

# Run (serves the built React UI + API on port 8000)
python api.py
```

Open your browser to **http://localhost:8000**.

### Development Mode (hot reload)

```bash
# Terminal 1 — FastAPI backend
python api.py

# Terminal 2 — Vite dev server with HMR (proxies /api to :8000)
cd frontend && npm run dev
```

Open **http://localhost:5173** for the dev server.

## Features

- **12-ODE Closed-Loop Model** — Full cardiovascular system: systemic and pulmonary circulation, four heart valves, time-varying ventricular elastance (Avanzolini 1988)
- **Synthetic ECG** — PQRST waveform synthesis with condition-specific morphology: wide QRS for VTach, absent P-waves for AFib, chaotic baseline for VFib (McSharry 2003 inspired)
- **Stochastic R-R Intervals** — Gamma-distributed beat timing for atrial fibrillation, uniform-random for ventricular fibrillation
- **10 Clinical Presets** — Healthy Adult, Sinus Tachycardia, Sinus Bradycardia, Systolic Heart Failure, Hypertension, Aortic Stenosis, Hemorrhagic Shock, Ventricular Tachycardia, Atrial Fibrillation, Ventricular Fibrillation
- **6 Clinical Metrics** — Cardiac output, stroke volume, systolic/diastolic BP, mean arterial pressure, pulse pressure — each with normal/warning/danger severity indicators
- **Comparison Mode** — Run two conditions simultaneously and see percentage deltas on every metric
- **4 Visualization Panels** — Multi-panel hemodynamic monitor (ECG, arterial, venous, LV volume), PV loops with ESPVR/EDPVR reference lines, full state variable explorer, data export
- **CSV Export** — Waveform data, PV loop data, and full time-series for any condition

## Using the Simulator

1. **Select a Preset** — Pick a clinical condition from the left panel; sliders auto-load typical values
2. **Adjust Parameters** — Fine-tune heart rate (30–400 bpm), contractility (10–160%), peripheral resistance, and arterial compliance
3. **Run Simulation** — Click **Run Simulation**; the RK45 ODE solver runs server-side
4. **Analyze Results** — Metric cards show hemodynamic KPIs with severity color coding; tabs give waveforms, PV loop, all variables, and CSV export
5. **Compare Conditions** — Enable **Compare Two Conditions** to overlay two presets with delta badges on every metric

## Model

The simulator implements the 12-state lumped-parameter model from Avanzolini et al. (1988), representing the cardiovascular system as an electrical analog circuit:

- **Resistance (R)** — viscous blood flow resistance
- **Compliance (C)** — elastic vessel wall properties
- **Inertance (L)** — blood inertia

Ventricular contraction is driven by a time-varying activation function `A(t)` that modulates elastance between diastolic and systolic values each cycle. Four diode-like valves (aortic, mitral, tricuspid, pulmonary) open and close based on pressure gradients.

**Solver:** `scipy.integrate.solve_ivp`, RK45, rtol=1e-5, atol=1e-8

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

Healthy adult baseline:

| Metric | Simulated | Literature |
|--------|-----------|------------|
| Cardiac Output | ~4.6 L/min | 4.0–8.0 L/min |
| Systolic Pressure | ~113 mmHg | 90–140 mmHg |
| Diastolic Pressure | ~68 mmHg | 60–90 mmHg |

Consistent with the original Avanzolini paper and standard physiological references.

## File Structure

```
├── api.py                # FastAPI backend — REST API + serves built frontend
├── model.py              # ODE physics, clinical presets, parameter builder
├── ecg.py                # Synthetic ECG and R-R interval generation
├── metrics.py            # Hemodynamic analysis and simulation runner
├── frontend/
│   ├── src/
│   │   ├── components/   # React components (Charts, Sidebar, MetricsRow, …)
│   │   ├── lib/          # Plotly theme, classify utility
│   │   ├── App.tsx       # Root component and state management
│   │   ├── api.ts        # Typed fetch wrappers
│   │   └── types.ts      # Shared TypeScript types
│   ├── vite.config.ts    # Vite build config with /api proxy
│   └── package.json
├── gen_paper_figures.py  # Standalone publication figure generator
├── requirements.txt      # Python dependencies
├── LICENSE               # CC BY-NC 4.0
└── README.md
```

## Dependencies

**Python**
```
numpy>=1.24.0
scipy>=1.10.0
fastapi>=0.110.0
uvicorn>=0.29.0
```

**JavaScript (frontend)**
```
react 18, vite 5, typescript, tailwindcss, plotly.js-dist-min
```

## Citation

If you use this simulator in research or educational work, please cite:

- Remizov, A., & Lapin, S. (YYYY). Quantifying the Hemodynamic Effects of Ventricular Fibrillation using a Verified Computational Model. *arXiv preprint arXiv:XXXX.XXXXX*.
- Avanzolini, G., Barbini, P., Cappello, A., & Cevese, A. (1988). CADCS simulation of the closed-loop cardiovascular system. *International Journal of Bio-Medical Computing*, 22(1), 39–49.
- McSharry, P. E., Clifford, G. D., Tarassenko, L., & Smith, L. A. (2003). A dynamical model for generating synthetic electrocardiogram signals. *IEEE Transactions on Biomedical Engineering*, 50(3), 289–294.

## License

Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0).
See [LICENSE](LICENSE) for details. This software may not be used for commercial purposes.
