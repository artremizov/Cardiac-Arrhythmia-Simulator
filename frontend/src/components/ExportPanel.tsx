import type { SimResult } from '../types'
import { STATE_VARS } from '../lib/stateVars'

function slug(s: string) { return s.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '') }

function download(filename: string, csv: string) {
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
}

function toCSV(headers: string[], rows: (number | string)[][]): string {
  const esc = (h: string) => (/[",]/.test(h) ? `"${h.replace(/"/g, '""')}"` : h)
  return [headers.map(esc).join(','),
    ...rows.map(r => r.map(v => (typeof v === 'number' ? v.toFixed(6) : v)).join(','))].join('\n')
}

const STATE_HEADERS = STATE_VARS.map(v => `${v.id} ${v.name} (${v.unit})`)

function waveformCSV(r: SimResult, plotWindow: number): string {
  const tEnd   = r.t[r.t.length - 1]
  const tStart = Math.max(0, tEnd - plotWindow)
  const idx = r.t.map((_, i) => i).filter(i => r.t[i] >= tStart)
  const headers = ['Time (s)', ...STATE_HEADERS, 'ECG, synthetic (a.u.)', 'LV pressure (mmHg)', 'LV outflow (mL/s)']
  const rows = idx.map(i => [r.t[i], ...r.X[i], r.ecg[i], r.metrics.lvp_full[i], r.metrics.lvof[i]])
  return toCSV(headers, rows)
}

function pvCSV(r: SimResult): string {
  return toCSV(['LV volume (mL)', 'LV pressure (mmHg)'], r.metrics.lv_vol.map((v, i) => [v, r.metrics.lvp[i]]))
}

function fullCSV(r: SimResult): string {
  return toCSV(['Time (s)', ...STATE_HEADERS], r.t.map((t, i) => [t, ...r.X[i]]))
}

interface Props { primary: SimResult; comparison: SimResult | null; plotWindow: number }

export function ExportPanel({ primary, comparison, plotWindow }: Props) {
  const runs = comparison ? [['A', primary], ['B', comparison]] as const : [['', primary]] as const
  const files = (r: SimResult) => {
    const s = slug(r.preset)
    return [
      { name: 'Waveforms', file: `cardiosim_${s}_waveforms.csv`,
        content: `Last ${plotWindow.toFixed(2)} s: time, X1–X12, ECG, LV pressure, LV outflow`,
        rows: r.t.filter(t => t >= r.t[r.t.length - 1] - plotWindow).length,
        make: () => waveformCSV(r, plotWindow) },
      { name: 'Pressure–volume loop', file: `cardiosim_${s}_pvloop.csv`,
        content: 'LV volume and pressure over the plotted beat',
        rows: r.metrics.lv_vol.length,
        make: () => pvCSV(r) },
      { name: 'Full run', file: `cardiosim_${s}_full.csv`,
        content: 'All time points: time, X1–X12',
        rows: r.t.length,
        make: () => fullCSV(r) },
    ]
  }

  return (
    <div className="export">
      <table className="data-table export-table">
        <thead>
          <tr>{comparison && <th>Run</th>}<th>Data</th><th>Columns</th><th className="num">Rows</th><th>File</th><th></th></tr>
        </thead>
        <tbody>
          {runs.map(([tag, r]) => files(r).map(f => (
            <tr key={tag + f.file}>
              {comparison && <td>{tag}: {r.preset}</td>}
              <td>{f.name}</td>
              <td className="muted">{f.content}</td>
              <td className="num">{f.rows.toLocaleString()}</td>
              <td className="mono-ish">{f.file}</td>
              <td><button type="button" className="btn" onClick={() => download(f.file, f.make())}>Download</button></td>
            </tr>
          )))}
        </tbody>
      </table>
      <p className="note">Comma-separated, one header row, units in the headers. Volumes in mL (1 mL = 1 cm³).</p>
    </div>
  )
}
