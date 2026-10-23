import { RANGES } from '../lib/classify'

const RANGE_ROWS: [string, string, string, number][] = [
  ['Cardiac output', 'co', 'L/min', 1],
  ['Stroke volume', 'sv', 'mL', 0],
  ['Systolic pressure', 'sys', 'mmHg', 0],
  ['Diastolic pressure', 'dia', 'mmHg', 0],
  ['Mean arterial pressure', 'map', 'mmHg', 0],
  ['Ejection fraction', 'ef', '%', 0],
  ['Heart rate', 'hr', 'bpm', 0],
]

export function About() {
  return (
    <article className="about">
      <section>
        <h3>Model</h3>
        <p>
          CardioSim solves the 12-state closed-loop lumped-parameter model of Avanzolini et al. (1988).
          The systemic and pulmonary circulations are resistances, compliances and inertances; the four
          valves are ideal diodes; both ventricles are time-varying elastances driven by an activation
          function A(t). The equations are integrated with SciPy's RK45 solver (relative tolerance 10⁻⁵,
          absolute tolerance 10⁻⁸, maximum step 5 ms) and sampled at 600 points per second.
        </p>
        <p>
          Systolic duration is T<sub>s</sub> = min(0.16 + 0.3·T<sub>c</sub>, 0.9·T<sub>c</sub>) s, where
          T<sub>c</sub> is the R-R interval. The cap keeps systole inside the cycle above 225 bpm.
        </p>
      </section>

      <section>
        <h3>Parameters</h3>
        <dl className="defs">
          <dt>Contractility</dt>
          <dd>Scales ULO, URO, ELS and ERS (peak isovolumic pressures and systolic elastances of both ventricles) together; 100% is the published baseline.</dd>
          <dt>Peripheral resistance</dt>
          <dd>Systemic peripheral resistance R3, baseline 1.0 mmHg·s/mL.</dd>
          <dt>Arterial compliance</dt>
          <dd>Systemic arterial compliance C2, baseline 1.46 mL/mmHg.</dd>
          <dt>Heart rate</dt>
          <dd>
            Sets T<sub>c</sub> = 60 / HR for regular rhythms. Atrial fibrillation draws R-R intervals from a gamma
            distribution with mean 60 / HR s (shape 4, limited to 0.3–1.5 s). Ventricular fibrillation draws
            them uniformly from 0.12–0.25 s and ignores the heart rate setting.
          </dd>
        </dl>
      </section>

      <section>
        <h3>Results</h3>
        <p>
          Metrics come from the last full beat; for atrial and ventricular fibrillation they are means over the
          last 8 beats, and the heart rate shown is the effective rate over those beats. Blood pressure is aortic
          pressure (X1). Stroke volume is the integral of LV outflow over the beat; cardiac output is stroke volume
          times heart rate; mean arterial pressure is diastolic + (systolic − diastolic) / 3; ejection fraction is
          stroke volume divided by end-diastolic volume.
        </p>
        <p>
          A value outside the resting adult reference range is marked amber with a Low or High label, and red
          when further out. Reference ranges:
        </p>
        <table className="data-table ranges">
          <thead><tr><th>Metric</th><th className="num">Reference</th><th className="num">Red below / above</th><th>Unit</th></tr></thead>
          <tbody>
            {RANGE_ROWS.map(([label, k, unit, d]) => (
              <tr key={k}>
                <td>{label}</td>
                <td className="num">{RANGES[k].normal.map(v => v.toFixed(d)).join('–')}</td>
                <td className="num">{RANGES[k].limits.map(v => v.toFixed(d)).join(' / ')}</td>
                <td className="unit">{unit}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p>
          Values quoted in the preset descriptions were measured with this code from 30 s runs; for ventricular
          fibrillation they are the mean of 5 runs.
        </p>
        <p>
          The ECG is synthetic: a sum of Gaussian waves after McSharry et al. (2003), timed to the model's beats.
          It is not computed by the model and is shown for orientation only.
        </p>
      </section>

      <section>
        <h3>Paper</h3>
        <p>
          Remizov A, Lapin S. Quantifying the hemodynamic effects of a prescribed ventricular-fibrillation-like
          state using a lumped-parameter cardiovascular model. The <code>paper/</code> folder of the repository
          contains the scripts and data that reproduce its results.
        </p>
      </section>

      <section>
        <h3>References</h3>
        <ol className="refs">
          <li>
            Avanzolini G, Barbini P, Cappello A, Cevese A. CADCS simulation of the closed-loop cardiovascular system.
            Int J Biomed Comput. 1988;22(1):39–49.
          </li>
          <li>
            McSharry PE, Clifford GD, Tarassenko L, Smith LA. A dynamical model for generating synthetic
            electrocardiogram signals. IEEE Trans Biomed Eng. 2003;50(3):289–294.
          </li>
        </ol>
      </section>

      <section>
        <h3>Use and license</h3>
        <p>
          For research and teaching; not for clinical decisions. © 2025 Artemii Remizov. Licensed under{' '}
          <a href="https://creativecommons.org/licenses/by-nc/4.0/" target="_blank" rel="noreferrer">CC BY-NC 4.0</a>.
          Source:{' '}
          <a href="https://github.com/artremizov/Cardiac-Arrhythmia-Simulator" target="_blank" rel="noreferrer">
            github.com/artremizov/Cardiac-Arrhythmia-Simulator
          </a>.
        </p>
      </section>
    </article>
  )
}
