Interactive Cardiovascular Simulator

This Streamlit application provides an interactive platform for simulating the human cardiovascular system based on the verified 1988 lumped-parameter model by Avanzolini et al. It allows users to explore the effects of various physiological and pathophysiological conditions on hemodynamics.

Features:
Verified Core Model: Implements the 12-state ODE model from Avanzolini et al. (1988).
Interactive Parameter Control: Adjust key parameters like Heart Rate, Ventricular Contractility, Systemic Peripheral Resistance, and Arterial Compliance via sliders.
Preset Clinical Scenarios: Quickly load parameters for 'Healthy Adult', 'Ventricular Fibrillation', 'Tachycardia', 'Heart Failure (Systolic)', and 'Hypertension'.
Real-time Visualization: View hemodynamic waveforms (Aortic Pressure, Venous Pressure, LV Volume, etc.) and diagnostic Left Ventricular Pressure-Volume (PV) loops.
Quantitative Metrics: Displays calculated Cardiac Output, Stroke Volume, Systolic, and Diastolic Blood Pressure based on the last stable cardiac cycle.
Detailed State Variable Plotting: Option to view the time course of all 12 model state variables.
Data Export: Download simulation results (waveforms, PV loop data, full state variables) as CSV files.
Simulation Settings: Control simulation duration and the time window for plots.

Setup:
Clone the Repository (or download files):
git clone <your-repo-url>
cd <your-repo-directory>
Create a Python Environment (Recommended):
Using conda:
conda create -n cardiac_sim python=3.9
conda activate cardiac_sim
Or using venv:
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
Install Dependencies:
pip install -r requirements.txt

Running the Simulator:
Ensure your Python environment is activated. Then, run the Streamlit app from your terminal:
streamlit run cardiac_sim.py
This will open the simulator interface in your web browser.

Using the Simulator:
Select a Preset: Choose a predefined condition from the sidebar radio buttons. This will automatically set the sliders to typical values for that state.

Customize Parameters: Fine-tune the simulation by adjusting the sliders in the sidebar. Tooltips provide information about each parameter.
Adjust Settings: Set the desired total simulation duration and how many seconds of the end of the simulation you want to display in the plots. Longer durations generally lead to more stable results.

Run Simulation: Click the "Run Simulation" button. A spinner will indicate that the ODEs are being solved.

Analyze Results:
View the Key Performance Indicators (KPIs).
Examine the plots in the "Graphical Analysis" tabs (Waveforms, PV Loop, All State Variables).
Use the download buttons within the tabs to save the data for offline analysis.

Model Reference
Avanzolini, G., Barbini, P., Cappello, A., & Cevenini, G. (1988). CADCS simulation of the closed-loop cardiovascular system. International Journal of Bio-Medical Computing, 22(1), 39-49.

## Citation
If you use this simulator or code in your research or educational work, please cite it. You can cite the associated arXiv paper:
* Remizov, A., & Lapin, S. (YYYY). Quantifying the Hemodynamic Effects of Ventricular Fibrillation using a Verified Computational Model. *arXiv preprint arXiv:XXXX.XXXXX*.
(Replace YYYY with the year and XXXX.XXXXX with the arXiv identifier once you have it).
Alternatively, you can cite the GitHub repository directly:
* Remizov, A. (YYYY). Cardiac-Arrhythmia-Simulator (Version X.Y.Z) [Software]. Available from https://github.com/artremizov/Cardiac-Arrhythmia-Simulator

License:
MIT
