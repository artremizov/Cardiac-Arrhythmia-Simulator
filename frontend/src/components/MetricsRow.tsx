import type { Metrics, SimResult } from '../types'
import { classify, direction, RANGES, STATUS_COLOR } from '../lib/classify'

interface Part { key: string; get: (m: Metrics) => number; digits: number }

interface MetricDef { label: string; unit: string; parts: Part[] }

const p = (key: string, get: (m: Metrics) => number, digits = 0): Part => ({ key, get, digits })

const METRICS: MetricDef[] = [
  { label: 'Cardiac output',         unit: 'L/min', parts: [p('co',  m => m.co, 2)] },
  { label: 'Stroke volume',          unit: 'mL',    parts: [p('sv',  m => m.sv, 1)] },
  { label: 'Blood pressure',         unit: 'mmHg',  parts: [p('sys', m => m.sys), p('dia', m => m.dia)] },
  { label: 'Mean arterial pressure', unit: 'mmHg',  parts: [p('map', m => m.map_val)] },
  { label: 'Ejection fraction',      unit: '%',     parts: [p('ef',  m => m.ef)] },
  { label: 'Heart rate',             unit: 'bpm',   parts: [p('hr',  m => m.hr)] },
]

const fmtRange = (k: string, digits: number) =>
  RANGES[k].normal.map(v => v.toFixed(digits === 2 ? 1 : 0)).join('–')

const signed = (d: number) => (Math.round(d) > 0 ? '+' : Math.round(d) < 0 ? '−' : '') + Math.abs(d).toFixed(0)

export function MetricsRow({ primary, comparison }: { primary: SimResult; comparison: SimResult | null }) {
  return (
    <section className="strip" aria-label="Results">
      {METRICS.map(({ label, unit, parts }) => {
        const flags = parts
          .map(pt => ({ pt, dir: direction(pt.key, pt.get(primary.metrics)) }))
          .filter(f => f.dir)
        const ref = parts.map(pt => fmtRange(pt.key, pt.digits)).join(' / ')
        return (
          <div className="strip-cell" key={label}>
            <div className="strip-label">{label}</div>
            <div className="strip-value">
              <span className="strip-num">
                {parts.map((pt, i) => {
                  const v = pt.get(primary.metrics)
                  return (
                    <span key={pt.key}>
                      {i > 0 && <span className="strip-sep">/</span>}
                      <span style={{ color: STATUS_COLOR[classify(pt.key, v)] }}>{v.toFixed(pt.digits)}</span>
                    </span>
                  )
                })}
              </span>
              <span className="strip-unit">{unit}</span>
            </div>
            <div className="strip-meta">
              {flags.length > 0 && (
                <span className="flag">
                  {parts.map((pt, i) => {
                    const v = pt.get(primary.metrics), st = classify(pt.key, v)
                    return (
                      <span key={pt.key} style={{ color: st === 'normal' ? 'var(--muted)' : STATUS_COLOR[st] }}>
                        {i > 0 && ' / '}{direction(pt.key, v) ?? '–'}
                      </span>
                    )
                  })}
                </span>
              )}
              <span>Ref {ref}</span>
            </div>
            {comparison && <Compare parts={parts} a={primary.metrics} b={comparison.metrics} />}
          </div>
        )
      })}
    </section>
  )
}

function Compare({ parts, a, b }: { parts: Part[]; a: Metrics; b: Metrics }) {
  const vb = parts.map(pt => pt.get(b).toFixed(pt.digits)).join('/')
  const first = parts[0]
  const va = first.get(a), vbn = first.get(b)
  // A percentage change is shown for single-valued metrics only
  const delta = parts.length === 1 && va !== 0 ? (vbn - va) / Math.abs(va) * 100 : null
  return (
    <div className="strip-compare">
      B <span className="num">{vb}</span>
      {delta != null && <span className="num"> ({signed(delta)}%)</span>}
    </div>
  )
}
