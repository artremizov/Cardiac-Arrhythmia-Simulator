import { useEffect, useState } from 'react'
import type { Presets } from '../types'

const GROUPS: [string, string][] = [
  ['normal', 'Normal'], ['arrhythmia', 'Arrhythmia'], ['structural', 'Structural'], ['critical', 'Critical'],
]

function PresetSelect({ id, presets, value, onChange, exclude }: {
  id: string; presets: Presets; value: string; onChange: (p: string) => void; exclude?: string
}) {
  return (
    <select id={id} value={value} onChange={e => onChange(e.target.value)}>
      {GROUPS.map(([cat, label]) => {
        const names = Object.keys(presets).filter(n => presets[n].category === cat && n !== exclude)
        return names.length ? (
          <optgroup key={cat} label={label}>
            {names.map(n => <option key={n} value={n}>{n}</option>)}
          </optgroup>
        ) : null
      })}
    </select>
  )
}

interface FieldProps {
  id: string; label: string; unit: string; value: number
  min: number; max: number; step: number; digits: number
  onChange: (v: number) => void; disabled?: boolean; note?: string
}

// Slider with an editable numeric field; typed values are committed on Enter or blur
function Field({ id, label, unit, value, min, max, step, digits, onChange, disabled, note }: FieldProps) {
  const [text, setText] = useState(value.toFixed(digits))
  useEffect(() => { setText(value.toFixed(digits)) }, [value, digits])

  const commit = () => {
    const v = parseFloat(text)
    if (Number.isFinite(v)) {
      const snapped = Math.round(Math.min(max, Math.max(min, v)) / step) * step
      onChange(+snapped.toFixed(4))
      setText(snapped.toFixed(digits))
    } else {
      setText(value.toFixed(digits))
    }
  }

  return (
    <div className={`field${disabled ? ' is-disabled' : ''}`}>
      <div className="field-row">
        <label htmlFor={id}>{label}</label>
        <span className="field-value">
          <input
            type="text" inputMode="decimal" aria-label={`${label} (${unit})`}
            value={text} disabled={disabled}
            onChange={e => setText(e.target.value)}
            onBlur={commit}
            onKeyDown={e => { if (e.key === 'Enter') commit() }}
          />
          <span className="field-unit">{unit}</span>
        </span>
      </div>
      <input
        id={id} type="range" min={min} max={max} step={step} value={value} disabled={disabled}
        onChange={e => onChange(Number(e.target.value))}
      />
      {note && <p className="field-note">{note}</p>}
    </div>
  )
}

interface Props {
  presets: Presets; preset: string; onPresetChange: (p: string) => void
  modified: boolean; onReset: () => void
  compareMode: boolean; onCompareModeChange: (v: boolean) => void
  comparePreset: string; onComparePresetChange: (p: string) => void
  hr: number; onHrChange: (v: number) => void
  contract: number; onContractChange: (v: number) => void
  resist: number; onResistChange: (v: number) => void
  compl: number; onComplChange: (v: number) => void
  duration: number; onDurationChange: (v: number) => void
  plotWindow: number; onPlotWindowChange: (v: number) => void
  onRun: () => void; loading: boolean; error: string | null
}

export function Sidebar(props: Props) {
  const {
    presets, preset, onPresetChange, modified, onReset,
    compareMode, onCompareModeChange, comparePreset, onComparePresetChange,
    hr, onHrChange, contract, onContractChange, resist, onResistChange, compl, onComplChange,
    duration, onDurationChange, plotWindow, onPlotWindowChange, onRun, loading, error,
  } = props
  const info = presets[preset]

  const hrNote =
    preset === 'Ventricular Fibrillation'
      ? 'Not used by this preset: R-R intervals are drawn uniformly from 0.12–0.25 s.'
      : preset === 'Atrial Fibrillation'
        ? 'Sets the mean of the random R-R intervals.'
        : undefined

  return (
    <aside className="sidebar">
      <header className="sidebar-head">
        <h1>CardioSim</h1>
        <p>Lumped-parameter cardiovascular model (Avanzolini et al., 1988)</p>
      </header>

      <div className="sidebar-body">
        <section className="group">
          <div className="group-head">
            <label className="group-label" htmlFor="preset">Preset</label>
            {modified && (
              <span className="modified">
                Modified <button type="button" className="link-btn" onClick={onReset}>Reset</button>
              </span>
            )}
          </div>
          <PresetSelect id="preset" presets={presets} value={preset} onChange={onPresetChange} />
          {info && <p className="desc">{info.desc}</p>}
        </section>

        <section className="group">
          <h2 className="group-label">Parameters</h2>
          <Field id="hr" label="Heart rate" unit="bpm" value={hr} min={30} max={400} step={1} digits={0}
                 onChange={onHrChange} disabled={preset === 'Ventricular Fibrillation'} note={hrNote} />
          <Field id="contract" label="Contractility" unit="%" value={contract} min={10} max={160} step={1} digits={0}
                 onChange={onContractChange} />
          <Field id="resist" label="Peripheral resistance" unit="mmHg·s/mL" value={resist} min={0.4} max={2.5} step={0.05} digits={2}
                 onChange={onResistChange} />
          <Field id="compl" label="Arterial compliance" unit="mL/mmHg" value={compl} min={0.6} max={2.2} step={0.02} digits={2}
                 onChange={onComplChange} />
        </section>

        <section className="group">
          <label className="check">
            <input type="checkbox" checked={compareMode} onChange={e => onCompareModeChange(e.target.checked)} />
            Compare with a second preset
          </label>
          {compareMode && (
            <div className="compare-body">
              <PresetSelect id="compare-preset" presets={presets} value={comparePreset}
                            onChange={onComparePresetChange} exclude={preset} />
              {presets[comparePreset] && <p className="desc">{presets[comparePreset].desc}</p>}
              <p className="field-note">Run B uses the preset's own parameters. It is drawn dashed.</p>
            </div>
          )}
        </section>

        <section className="group">
          <h2 className="group-label">Simulation</h2>
          <Field id="duration" label="Duration" unit="s" value={duration} min={2} max={20} step={0.5} digits={1}
                 onChange={onDurationChange} />
          <Field id="window" label="Plot window" unit="s" value={plotWindow} min={0.5} max={duration} step={0.25} digits={2}
                 onChange={v => onPlotWindowChange(Math.min(v, duration))} />
        </section>
      </div>

      <footer className="sidebar-foot">
        <button type="button" className="btn btn-primary" onClick={onRun} disabled={loading}>
          {loading ? 'Running…' : 'Run simulation'}
        </button>
        {error && <p className="error" role="alert">{error}</p>}
      </footer>
    </aside>
  )
}
