import type { Presets, PresetInfo } from '../types'

const CAT_COLOR: Record<string, string> = {
  normal:     '#059669',
  arrhythmia: '#d97706',
  structural: '#2563eb',
  critical:   '#dc2626',
}

interface SliderProps {
  label: string; value: number; min: number; max: number; step: number
  format?: (v: number) => string; onChange: (v: number) => void
}

function Slider({ label, value, min, max, step, format, onChange }: SliderProps) {
  const pct     = ((value - min) / (max - min)) * 100
  const display = format ? format(value) : String(value)
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 7 }}>
        <span style={{ fontSize: '0.78rem', color: '#374151', fontWeight: 500 }}>{label}</span>
        <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '0.75rem', color: '#6b7280' }}>{display}</span>
      </div>
      <input
        type="range" min={min} max={max} step={step} value={value}
        onChange={e => onChange(Number(e.target.value))}
        style={{ background: `linear-gradient(to right, #2563eb ${pct}%, #e5e7eb ${pct}%)` }}
      />
    </div>
  )
}

interface Props {
  presets: Presets; preset: string; onPresetChange: (p: string) => void
  compareMode: boolean; onCompareModeChange: (v: boolean) => void
  comparePreset: string; onComparePresetChange: (p: string) => void
  hr: number; onHrChange: (v: number) => void
  contract: number; onContractChange: (v: number) => void
  resist: number; onResistChange: (v: number) => void
  compl: number; onComplChange: (v: number) => void
  duration: number; onDurationChange: (v: number) => void
  plotWindow: number; onPlotWindowChange: (v: number) => void
  onRun: () => void; loading: boolean; error: string | null; presetName: string
}

export function Sidebar({
  presets, preset, onPresetChange,
  compareMode, onCompareModeChange, comparePreset, onComparePresetChange,
  hr, onHrChange, contract, onContractChange,
  resist, onResistChange, compl, onComplChange,
  duration, onDurationChange, plotWindow, onPlotWindowChange,
  onRun, loading, error,
}: Props) {
  const info: PresetInfo | undefined = presets[preset]
  const cat    = info?.category ?? 'normal'
  const catCol = CAT_COLOR[cat] ?? '#64748b'

  return (
    <aside className="sidebar">
      {/* Brand */}
      <div style={{ padding: '20px 20px 18px', borderBottom: '1px solid #f1f5f9' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 1 }}>
          <span style={{ fontSize: '1.15rem', fontWeight: 800, color: '#111827', letterSpacing: '-0.03em' }}>Cardio</span>
          <span style={{ fontSize: '1.15rem', fontWeight: 800, color: '#2563eb', letterSpacing: '-0.03em' }}>Sim</span>
        </div>
        <p style={{ fontSize: '0.67rem', color: '#94a3b8', marginTop: 3, fontWeight: 500, letterSpacing: '0.03em' }}>
          Avanzolini 1988 · McSharry ECG · v3.0
        </p>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', paddingBottom: 16 }}>
        {/* Clinical Preset */}
        <div className="section-label" style={{ marginTop: 20 }}>Clinical Preset</div>
        <div style={{ padding: '0 16px' }}>
          <select value={preset} onChange={e => onPresetChange(e.target.value)}>
            {Object.keys(presets).map(name => (
              <option key={name} value={name}>{name}</option>
            ))}
          </select>
          {info && (
            <div style={{ marginTop: 10 }}>
              <span
                className="preset-badge"
                style={{ background: catCol + '14', color: catCol }}
              >
                {cat}
              </span>
              <p style={{ fontSize: '0.75rem', color: '#6b7280', lineHeight: 1.55, marginTop: 8 }}>{info.desc}</p>
            </div>
          )}
        </div>

        <div className="sidebar-divider" />

        {/* Compare mode */}
        <div style={{ padding: '0 16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '0.78rem', fontWeight: 500, color: '#374151' }}>Compare Two Conditions</span>
            <label className="toggle">
              <input type="checkbox" checked={compareMode} onChange={e => onCompareModeChange(e.target.checked)} />
              <span className="toggle-slider" />
            </label>
          </div>
          {compareMode && (
            <div style={{ marginTop: 12 }}>
              <select value={comparePreset} onChange={e => onComparePresetChange(e.target.value)}>
                {Object.keys(presets).filter(n => n !== preset).map(name => (
                  <option key={name} value={name}>{name}</option>
                ))}
              </select>
              {presets[comparePreset] && (
                <p style={{ fontSize: '0.75rem', color: '#6b7280', lineHeight: 1.55, marginTop: 8 }}>
                  {presets[comparePreset].desc}
                </p>
              )}
              <p style={{ fontSize: '0.7rem', color: '#e11d48', marginTop: 8 }}>
                Comparison shown in red on all charts
              </p>
            </div>
          )}
        </div>

        <div className="sidebar-divider" />

        {/* Parameters */}
        <div className="section-label">Parameters</div>
        <div style={{ padding: '0 16px' }}>
          <Slider label="Heart Rate" value={hr} min={30} max={400} step={1}
            format={v => `${v} bpm`} onChange={onHrChange} />
          <Slider label="Contractility" value={contract} min={10} max={160} step={1}
            format={v => `${v}%`} onChange={onContractChange} />
          <Slider label="Peripheral Resistance" value={resist} min={0.4} max={2.5} step={0.05}
            format={v => v.toFixed(2)} onChange={onResistChange} />
          <Slider label="Arterial Compliance" value={compl} min={0.6} max={2.2} step={0.02}
            format={v => v.toFixed(2)} onChange={onComplChange} />
        </div>

        <div className="sidebar-divider" />

        {/* Simulation */}
        <div className="section-label">Simulation</div>
        <div style={{ padding: '0 16px' }}>
          <Slider label="Duration" value={duration} min={2} max={20} step={0.5}
            format={v => `${v.toFixed(1)} s`} onChange={onDurationChange} />
          <Slider label="Plot Window" value={plotWindow} min={0.5} max={duration} step={0.25}
            format={v => `${v.toFixed(2)} s`} onChange={v => onPlotWindowChange(Math.min(v, duration))} />

          <button className="run-btn" style={{ marginTop: 4 }} onClick={onRun} disabled={loading}>
            {loading ? <><span className="spinner" />Simulating…</> : 'Run Simulation'}
          </button>
          {error && (
            <p style={{ fontSize: '0.75rem', color: '#dc2626', marginTop: 8, lineHeight: 1.4 }}>{error}</p>
          )}
        </div>
      </div>

      {/* Footer */}
      <div style={{ padding: '12px 20px', borderTop: '1px solid #f1f5f9' }}>
        <p style={{ fontSize: '0.67rem', color: '#cbd5e1' }}>
          © 2025 Artemii Remizov · WSU ·{' '}
          <a href="https://creativecommons.org/licenses/by-nc/4.0/" target="_blank"
             style={{ color: '#9ca3af', textDecoration: 'underline' }}>CC BY-NC 4.0</a>
        </p>
      </div>
    </aside>
  )
}
