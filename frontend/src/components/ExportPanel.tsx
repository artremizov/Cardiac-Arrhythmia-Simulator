import type { SimResult } from '../types'

const STATE_LABELS = [
  ['Aortic Pressure','mmHg'],['Aortic Flow','cm³/s'],
  ['Systemic Arterial Pressure','mmHg'],['Systemic Peripheral Flow','cm³/s'],
  ['Systemic Venous Pressure','mmHg'],['Right Ventricle Volume','cm³'],
  ['Pulmonary Artery Pressure','mmHg'],['Pulmonary Arterial Flow','cm³/s'],
  ['Pulmonary Arteriole Pressure','mmHg'],['Pulmonary Venous Flow','cm³/s'],
  ['Pulmonary Venous / LA Pressure','mmHg'],['Left Ventricle Volume','cm³'],
]

function slug(s: string) { return s.toLowerCase().replace(/[^a-z0-9]+/g, '_') }

function download(filename: string, csv: string) {
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
}

function toCSV(headers: string[], rows: (number | string)[][]): string {
  return [headers.join(','), ...rows.map(r => r.map(v => typeof v === 'number' ? v.toFixed(6) : v).join(','))].join('\n')
}

function waveformCSV(r: SimResult, plotWindow: number): string {
  const tEnd = r.t[r.t.length - 1]
  const tStart = Math.max(0, tEnd - plotWindow)
  const idx = r.t.map((_, i) => i).filter(i => r.t[i] >= tStart)
  const headers = ['Time (s)', ...STATE_LABELS.map(([n, u]) => `${n} (${u})`), 'ECG (mV)', 'LV Pressure (mmHg)', 'LV Outflow (cm³/s)']
  const rows = idx.map(i => [r.t[i], ...r.X[i], r.ecg[i], r.metrics.lvp_full[i], r.metrics.lvof[i]])
  return toCSV(headers, rows)
}

function pvCSV(r: SimResult): string {
  const headers = ['LV Volume (cm³)', 'LV Pressure (mmHg)']
  const rows = r.metrics.lv_vol.map((v, i) => [v, r.metrics.lvp[i]])
  return toCSV(headers, rows)
}

function fullCSV(r: SimResult): string {
  const headers = ['Time (s)', ...STATE_LABELS.map(([n, u]) => `${n} (${u})`)]
  const rows = r.t.map((t, i) => [t, ...r.X[i]])
  return toCSV(headers, rows)
}

interface SectionProps { result: SimResult; plotWindow: number; label: string }

function ExportSection({ result, plotWindow, label }: SectionProps) {
  const s = slug(result.preset)
  return (
    <div className="card p-5 mb-4">
      <p className="text-xs font-semibold text-muted uppercase tracking-widest mb-4">{label}</p>
      <div className="grid grid-cols-3 gap-3">
        {[
          { icon: '≋', title: 'Waveform Data', sub: 'Plot window · all signals', fn: () => download(`cardiosim_${s}_waveforms.csv`, waveformCSV(result, plotWindow)) },
          { icon: '◯', title: 'PV Loop Data',  sub: 'LV volume × pressure',     fn: () => download(`cardiosim_${s}_pvloop.csv`,    pvCSV(result)) },
          { icon: '⊞', title: 'Full Simulation',sub: 'All time points · 12 ODEs', fn: () => download(`cardiosim_${s}_full.csv`,      fullCSV(result)) },
        ].map(({ icon, title, sub, fn }) => (
          <button key={title} onClick={fn} className="export-btn flex-col gap-1.5 py-4">
            <span className="text-lg">{icon}</span>
            <span className="font-medium">{title}</span>
            <span className="text-[10px] text-[#334155]">{sub}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

interface Props { primary: SimResult; comparison: SimResult | null; plotWindow: number }

export function ExportPanel({ primary, comparison, plotWindow }: Props) {
  return (
    <div>
      <ExportSection result={primary} plotWindow={plotWindow} label={`Primary: ${primary.preset}`} />
      {comparison
        ? <ExportSection result={comparison} plotWindow={plotWindow} label={`Comparison: ${comparison.preset}`} />
        : (
          <div className="card p-5 text-center">
            <p className="text-muted text-sm">Enable Compare Mode to export a second condition.</p>
          </div>
        )}
      <p className="text-xs text-[#1e293b] mt-4 text-center">
        Waveform data covers the current plot window · Full simulation exports all time points
      </p>
    </div>
  )
}
